"""DAG-based playbook execution engine with topological sort and concurrent execution."""

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from core.metrics import observe_playbook_error, observe_playbook_run

from ..v6_linear.registry import get_registry
from .exceptions import (
    DAGCycleError,
    DAGExecutionError,
    DAGTimeoutError,
    ErrorContext,
    NodeExecutionError,
    NodeTimeoutError,
)
from .retry_policy import RetryExecutor, RetryPolicy
from .state_machine import NodeState, NodeStateMachine

logger = get_logger(__name__)

# v0.8.1: Global timeout for DAG execution (in seconds)
DAG_GLOBAL_TIMEOUT_SECONDS = settings.api_timeout_dag_run_ms // 1000


@dataclass
class DAGNode:
    """Representation of a node in the DAG definition."""

    id: str
    step_id: str
    name: str
    config: dict[str, Any] = None
    inputs: dict[str, Any] = None
    inputs_template: dict[str, Any] = None  # v0.7.3: Template with variable references
    outputs_mapping: dict[str, str] = None  # v0.7.3: JSONPath to context key mapping
    retry_policy: RetryPolicy | None = None
    timeout_seconds: int = 300

    def __post_init__(self):
        if self.config is None:
            self.config = {}
        if self.inputs is None:
            self.inputs = {}
        if self.inputs_template is None:
            self.inputs_template = {}
        if self.outputs_mapping is None:
            self.outputs_mapping = {}


@dataclass
class DAGEdge:
    """Representation of an edge in the DAG definition."""

    source: str
    target: str
    condition: str | None = None


@dataclass
class DAGDefinition:
    """Parsed DAG definition from JSON."""

    nodes: dict[str, DAGNode]
    edges: list[DAGEdge]

    def get_dependencies(self, node_id: str) -> list[str]:
        """Get all nodes that this node depends on.

        Args:
            node_id: Node to get dependencies for

        Returns:
            List of node IDs that are dependencies
        """
        deps = []
        for edge in self.edges:
            if edge.target == node_id:
                deps.append(edge.source)
        return deps

    def get_dependents(self, node_id: str) -> list[str]:
        """Get all nodes that depend on this node.

        Args:
            node_id: Node to get dependents for

        Returns:
            List of node IDs that depend on this node
        """
        dependents = []
        for edge in self.edges:
            if edge.source == node_id:
                dependents.append(edge.target)
        return dependents


class DAGBuilder:
    """Builds DAG definition from JSON configuration."""

    @staticmethod
    def from_json(definition_json: dict) -> DAGDefinition:
        """Parse DAG definition from JSON.

        Args:
            definition_json: JSON dict with nodes and edges

        Returns:
            Parsed DAGDefinition object

        Raises:
            ValueError: If definition is invalid
        """
        if "nodes" not in definition_json or "edges" not in definition_json:
            raise ValueError("Definition must contain 'nodes' and 'edges'")

        nodes = {}
        for node_data in definition_json["nodes"]:
            node_id = node_data["id"]
            retry_policy = None
            if "retry_policy" in node_data:
                rp = node_data["retry_policy"]
                retry_policy = RetryPolicy(
                    max_attempts=rp.get("max_attempts", 3),
                    backoff_base=rp.get("backoff_base", 1.0),
                    backoff_max=rp.get("backoff_max", 60.0),
                    timeout=rp.get("timeout", 300),
                )

            # v0.7.3: Auto-migrate old schema
            node_config = node_data.get("config", {})
            node_inputs = node_data.get("inputs", {})
            node_inputs_template = node_data.get("inputs_template", node_inputs)
            node_outputs_mapping = node_data.get("outputs_mapping", {})

            nodes[node_id] = DAGNode(
                id=node_id,
                step_id=node_data.get("step_id", node_data.get("type", "")),
                name=node_data.get("name", node_id),
                config=node_config,
                inputs=node_inputs,
                inputs_template=node_inputs_template,
                outputs_mapping=node_outputs_mapping,
                retry_policy=retry_policy,
                timeout_seconds=node_data.get("timeout_seconds", 300),
            )

        edges = []
        for edge_data in definition_json["edges"]:
            edges.append(
                DAGEdge(
                    source=edge_data["source"],
                    target=edge_data["target"],
                    condition=edge_data.get("condition"),
                )
            )

        return DAGDefinition(nodes=nodes, edges=edges)


class DAGExecutionEngine:
    """Engine for executing DAG-based playbook workflows."""

    def __init__(
        self,
        session: AsyncSession,
        concurrency_limit: int = None,
    ):
        """Initialize the DAG execution engine.

        Args:
            session: Database session for persistence
            concurrency_limit: Maximum concurrent node executions (defaults to config)
        """
        self.session = session
        self.registry = get_registry()
        # v0.8.3: Use config default, respect max limit
        self.concurrency_limit = min(
            concurrency_limit or settings.dag_concurrency_default,
            settings.dag_concurrency_max,
        )
        self.semaphore = asyncio.Semaphore(self.concurrency_limit)
        self._node_states: dict[str, NodeStateMachine] = {}
        self._node_outputs: dict[str, Any] = {}

    async def execute_dag(
        self,
        definition: DAGDefinition,
        run_id: str,
        input_json: dict[str, Any],
        mode: str = "dry_run",
        created_by_user_id: str | None = None,
        input_context_json: dict[str, Any] = None,  # v0.7.3
    ) -> dict[str, Any]:
        """Execute a DAG definition.

        Args:
            definition: Parsed DAG definition
            run_id: Playbook run ID
            input_json: Input data for the DAG
            mode: Execution mode (dry_run or apply)
            created_by_user_id: User ID who initiated the run
            input_context_json: Initial context for v0.7.3 variable system

        Returns:
            Dictionary with execution results
        """
        logger.info(
            f"[{run_id}] Starting DAG execution with {len(definition.nodes)} nodes"
        )
        start_time = datetime.now(UTC)
        playbook_name = input_json.get("playbook_name", "unknown")
        tenant_id = str(input_json.get("tenant_id", "default"))

        # Initialize state machines for all nodes
        self._node_states = {
            node_id: NodeStateMachine() for node_id in definition.nodes
        }
        self._node_outputs = {}

        # v0.7.3: Initialize context variable system
        if input_context_json is None:
            input_context_json = {}

        from services.playbook_context_service import context_service

        # Initialize run context
        run_context = context_service.initialize_run_context(
            run_id=run_id,
            input_data=input_context_json or input_json,
            definition_id=None,  # Could be passed if needed
        )

        # Get topological order
        execution_order = self._topological_sort(definition)
        logger.info(f"[{run_id}] Execution order: {execution_order}")

        # Create node run records
        await self._create_node_runs(run_id, definition)

        # Execute by topological levels (concurrent execution)
        failed_nodes = []
        skipped_nodes = []

        # Group nodes by level for concurrent execution
        levels = self._group_by_level(definition, execution_order)

        try:
            for level, nodes_at_level in enumerate(levels):
                # v0.8.1: Check global timeout before each level
                elapsed = (datetime.now(UTC) - start_time).total_seconds()
                if elapsed > DAG_GLOBAL_TIMEOUT_SECONDS:
                    logger.error(
                        f"[{run_id}] DAG execution timed out after {elapsed:.1f}s"
                    )
                    await self._update_run_status(
                        run_id, "timeout", self._node_outputs, run_context
                    )
                    observe_playbook_error(playbook_name, "timeout", tenant_id)
                    observe_playbook_run(
                        playbook_name, "timeout", mode, tenant_id, elapsed
                    )
                    return {
                        "run_id": run_id,
                        "status": "timeout",
                        "failed_nodes": failed_nodes,
                        "skipped_nodes": skipped_nodes
                        + nodes_at_level,  # Remaining nodes are skipped
                        "outputs": self._node_outputs,
                        "error": f"Global timeout exceeded ({DAG_GLOBAL_TIMEOUT_SECONDS}s)",
                    }

                logger.info(
                    f"[{run_id}] Executing level {level} with {len(nodes_at_level)} nodes"
                )

                # Execute all nodes at this level concurrently with timeout
                tasks = [
                    self._execute_node_with_timeout(
                        node_id=node_id,
                        definition=definition,
                        run_id=run_id,
                        input_json=input_json,
                        mode=mode,
                        run_context=run_context,
                        start_time=start_time,  # Pass start time for timeout checking
                    )
                    for node_id in nodes_at_level
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for node_id, result in zip(nodes_at_level, results, strict=False):
                    if isinstance(result, Exception):
                        logger.error(f"[{run_id}] Node {node_id} failed: {result}")
                        failed_nodes.append(node_id)
                    elif result.status == "failed":
                        failed_nodes.append(node_id)
                    elif result.status == "skipped":
                        skipped_nodes.append(node_id)

                # Check if we should continue (fail-fast behavior)
                if failed_nodes:
                    # Determine which nodes can still run (dependents of successful nodes only)
                    remaining_nodes = self._get_executable_nodes(
                        definition, failed_nodes, skipped_nodes
                    )
                    if not remaining_nodes:
                        logger.warning(
                            f"[{run_id}] Cannot continue after failures in {failed_nodes}"
                        )
                        break

        except TimeoutError:
            logger.error(f"[{run_id}] DAG execution timed out")
            await self._update_run_status(
                run_id, "timeout", self._node_outputs, run_context
            )
            observe_playbook_error(playbook_name, "timeout", tenant_id)
            observe_playbook_run(
                playbook_name,
                "timeout",
                mode,
                tenant_id,
                (datetime.now(UTC) - start_time).total_seconds(),
            )
            # Create structured error for timeout
            timeout_error = DAGTimeoutError(
                run_id=run_id,
                timeout_seconds=DAG_GLOBAL_TIMEOUT_SECONDS,
                completed_nodes=list(self._node_outputs.keys()),
                pending_nodes=[
                    n for n in definition.nodes if n not in self._node_outputs
                ],
            )
            return {
                "run_id": run_id,
                "status": "timeout",
                "failed_nodes": failed_nodes,
                "skipped_nodes": skipped_nodes,
                "outputs": self._node_outputs,
                "error": timeout_error.to_dict(),
            }
        except DAGExecutionError as e:
            logger.error(f"[{run_id}] DAG execution error: {e.message}")
            await self._update_run_status(
                run_id, "failed", self._node_outputs, run_context
            )
            observe_playbook_error(playbook_name, type(e).__name__, tenant_id)
            observe_playbook_run(
                playbook_name,
                "failed",
                mode,
                tenant_id,
                (datetime.now(UTC) - start_time).total_seconds(),
            )
            return {
                "run_id": run_id,
                "status": "failed",
                "failed_nodes": failed_nodes,
                "skipped_nodes": skipped_nodes,
                "outputs": self._node_outputs,
                "error": e.to_dict(),
            }

        # Update run status
        final_status = "success"
        if failed_nodes:
            final_status = "failed"
        elif skipped_nodes:
            final_status = "partial"

        await self._update_run_status(
            run_id, final_status, self._node_outputs, run_context
        )
        total_duration = (datetime.now(UTC) - start_time).total_seconds()
        observe_playbook_run(
            playbook_name, final_status, mode, tenant_id, total_duration
        )

        logger.info(f"[{run_id}] DAG execution completed with status: {final_status}")

        # Send failure notification if enabled
        if final_status in ["failed", "cancelled", "timeout"]:
            await self._send_failure_notification(
                run_id=run_id,
                status=final_status,
                failed_nodes=failed_nodes,
            )

        return {
            "run_id": run_id,
            "status": final_status,
            "failed_nodes": failed_nodes,
            "skipped_nodes": skipped_nodes,
            "outputs": self._node_outputs,
        }

    def _topological_sort(self, definition: DAGDefinition) -> list[str]:
        """Perform topological sort using Kahn's algorithm.

        Args:
            definition: DAG definition

        Returns:
            List of node IDs in topological order

        Raises:
            ValueError: If the graph contains a cycle
        """
        # Calculate in-degrees
        in_degree = defaultdict(int)
        for node_id in definition.nodes:
            in_degree[node_id] = 0

        for edge in definition.edges:
            in_degree[edge.target] += 1

        # Initialize queue with nodes that have no dependencies
        queue = deque([node_id for node_id, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            node_id = queue.popleft()
            result.append(node_id)

            # Reduce in-degree for dependents
            for dependent in definition.get_dependents(node_id):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # Check for cycles
        if len(result) != len(definition.nodes):
            # Find the cycle nodes
            remaining = set(definition.nodes.keys()) - set(result)
            raise DAGCycleError(
                message="DAG contains a cycle, cannot determine execution order",
                cycle_nodes=list(remaining),
            )

        return result

    def _group_by_level(
        self,
        definition: DAGDefinition,
        execution_order: list[str],
    ) -> list[list[str]]:
        """Group nodes by execution level for concurrent execution.

        Args:
            definition: DAG definition
            execution_order: Topologically sorted node IDs

        Returns:
            List of lists, where each inner list contains nodes at the same level
        """
        levels = []
        current_level = []
        current_level_nodes = set()

        for node_id in execution_order:
            deps = definition.get_dependencies(node_id)

            # Check if all dependencies are in current or previous levels
            can_execute_at_current_level = all(
                dep in current_level_nodes for dep in deps
            )

            if can_execute_at_current_level and not current_level:
                # First node, start new level
                current_level.append(node_id)
                current_level_nodes.add(node_id)
            elif can_execute_at_current_level:
                # Can execute concurrently with current level
                current_level.append(node_id)
                current_level_nodes.add(node_id)
            else:
                # Need to start a new level
                if current_level:
                    levels.append(current_level)
                current_level = [node_id]
                current_level_nodes = {node_id}

        if current_level:
            levels.append(current_level)

        return levels

    async def _execute_node_with_timeout(
        self,
        node_id: str,
        definition: DAGDefinition,
        run_id: str,
        input_json: dict[str, Any],
        mode: str,
        run_context: dict[str, Any] = None,
        start_time: datetime = None,
    ) -> "NodeExecutionResult":
        """Execute a single DAG node with global timeout checking.

        Args:
            node_id: Node identifier
            definition: DAG definition
            run_id: Run ID
            input_json: Input data
            mode: Execution mode
            run_context: Current execution context
            start_time: DAG execution start time for timeout checking

        Returns:
            NodeExecutionResult with execution outcome
        """
        # Check global timeout before executing
        if start_time:
            elapsed = (datetime.now(UTC) - start_time).total_seconds()
            if elapsed > DAG_GLOBAL_TIMEOUT_SECONDS:
                logger.warning(
                    f"[{run_id}] Node {node_id} skipped due to global timeout"
                )
                return NodeExecutionResult(
                    node_id=node_id,
                    status="skipped",
                    error=f"Global timeout exceeded ({DAG_GLOBAL_TIMEOUT_SECONDS}s)",
                )

        return await self._execute_node(
            node_id=node_id,
            definition=definition,
            run_id=run_id,
            input_json=input_json,
            mode=mode,
            run_context=run_context,
        )

    async def _execute_node(
        self,
        node_id: str,
        definition: DAGDefinition,
        run_id: str,
        input_json: dict[str, Any],
        mode: str,
        run_context: dict[str, Any] = None,  # v0.7.3
    ) -> "NodeExecutionResult":
        """Execute a single DAG node with retry policy.

        Args:
            node_id: Node identifier
            definition: DAG definition
            run_id: Run ID
            input_json: Input data
            mode: Execution mode
            run_context: Current execution context (v0.7.3)

        Returns:
            NodeExecutionResult with execution outcome
        """
        node = definition.nodes[node_id]
        state_machine = self._node_states[node_id]

        async with self.semaphore:  # Limit concurrency
            # Update state to running
            state_machine.transition_to(NodeState.RUNNING)
            await self._update_node_status(run_id, node_id, "running")

            start_time = datetime.now(UTC)
            error = None
            output = None

            try:
                # Get step implementation
                step_impl = self.registry.get_step_implementation(node.step_id)

                # v0.7.3: Build enriched input with context system
                from services.playbook_context_service import context_service

                # Initialize context if not provided
                if run_context is None:
                    run_context = {"context": {}, "input": input_json, "nodes": {}}

                # Prepare node inputs
                if node.inputs_template:
                    # Render inputs_template with context variables
                    enriched_input = context_service.render_node_inputs(
                        node.inputs_template, run_context
                    )
                else:
                    # Legacy behavior: use node.inputs or build from dependencies
                    enriched_input = {**input_json}
                    if node.inputs:
                        enriched_input.update(node.inputs)
                    for dep in definition.get_dependencies(node_id):
                        if dep in self._node_outputs:
                            enriched_input.update(self._node_outputs[dep])

                # Update node run with rendered inputs
                await self._update_node_inputs(run_id, node_id, enriched_input)

                # Check retry policy
                if node.retry_policy:
                    executor = RetryExecutor(node.retry_policy)

                    async def execute_step():
                        if asyncio.iscoroutinefunction(step_impl.execute):
                            return await step_impl.execute(enriched_input, mode)
                        return step_impl.execute(enriched_input, mode)

                    retry_result = await executor.execute_with_retry(execute_step)

                    if retry_result.success:
                        output = retry_result
                        state_machine.transition_to(NodeState.SUCCESS)
                        await self._update_node_status(
                            run_id, node_id, "success", output
                        )
                    else:
                        error = retry_result.error
                        state_machine.transition_to(NodeState.FAILED)
                        await self._update_node_status(
                            run_id, node_id, "failed", error=error
                        )
                else:
                    # Execute without retry
                    if asyncio.iscoroutinefunction(step_impl.execute):
                        output = await step_impl.execute(enriched_input, mode)
                    else:
                        output = step_impl.execute(enriched_input, mode)

                    state_machine.transition_to(NodeState.SUCCESS)
                    await self._update_node_status(run_id, node_id, "success", output)

                self._node_outputs[node_id] = output

                # v0.7.3: Merge node output into context using outputs_mapping
                if output is not None and node.outputs_mapping:
                    updated_context = context_service.merge_node_output(
                        run_context, node_id, output, node.outputs_mapping
                    )
                    # Update run context for subsequent nodes
                    run_context.clear()
                    run_context.update(updated_context)

                    # Persist context to database
                    await self._persist_run_context(run_id, run_context)

            except DAGExecutionError as e:
                # Already a structured error
                logger.error(f"[{run_id}] Node {node_id} execution failed: {e.message}")
                error = e.to_dict()
                state_machine.transition_to(NodeState.FAILED)
                await self._update_node_status(
                    run_id, node_id, "failed", error=e.message
                )
            except TimeoutError:
                # Handle timeout specifically
                logger.error(f"[{run_id}] Node {node_id} timed out")
                timeout_error = NodeTimeoutError(
                    node_id=node_id,
                    step_id=node.step_id,
                    timeout_seconds=node.timeout_seconds,
                    context=ErrorContext(
                        run_id=run_id,
                        node_id=node_id,
                        step_id=node.step_id,
                    ),
                )
                error = timeout_error.to_dict()
                state_machine.transition_to(NodeState.FAILED)
                await self._update_node_status(
                    run_id, node_id, "failed", error=timeout_error.message
                )
            except Exception as e:
                # Convert to structured error
                logger.error(
                    f"[{run_id}] Node {node_id} execution failed: {e}", exc_info=True
                )
                node_error = NodeExecutionError(
                    message=str(e),
                    node_id=node_id,
                    step_id=node.step_id,
                    context=ErrorContext(
                        run_id=run_id,
                        node_id=node_id,
                        step_id=node.step_id,
                        input_data=(
                            enriched_input if "enriched_input" in dir() else None
                        ),
                    ),
                    recoverable=True,
                    cause=e,
                )
                error = node_error.to_dict()
                state_machine.transition_to(NodeState.FAILED)
                await self._update_node_status(
                    run_id, node_id, "failed", error=node_error.message
                )

            # Calculate duration
            duration_ms = int(
                (datetime.now(UTC) - start_time).total_seconds() * 1000
            )

            return NodeExecutionResult(
                node_id=node_id,
                status=state_machine.state.value,
                output=output,
                error=error,
                duration_ms=duration_ms,
            )

    async def _create_node_runs(
        self,
        run_id: str,
        definition: DAGDefinition,
    ) -> None:
        """Create node run records in the database.

        Args:
            run_id: Playbook run ID
            definition: DAG definition
        """
        from models.playbook_definition import PlaybookNodeRunModel

        for node_id, node in definition.nodes.items():
            node_run = PlaybookNodeRunModel(
                run_id=run_id,
                node_id=node_id,
                step_id=node.step_id,
                status="pending",
                input_json={},
                output_json={},
            )
            self.session.add(node_run)

        await self.session.flush()

    async def _update_node_status(
        self,
        run_id: str,
        node_id: str,
        status: str,
        output: Any = None,
        error: str | None = None,
    ) -> None:
        """Update node run status in database.

        Args:
            run_id: Run ID
            node_id: Node ID
            status: New status
            output: Optional output data
            error: Optional error message
        """
        from models.playbook_definition import PlaybookNodeRunModel

        now = datetime.now(UTC)

        # Get the node run
        stmt = select(PlaybookNodeRunModel).where(
            PlaybookNodeRunModel.run_id == run_id,
            PlaybookNodeRunModel.node_id == node_id,
        )
        result = await self.session.execute(stmt)
        node_run = result.scalar_one_or_none()

        if node_run:
            node_run.status = status

            if status == "running" and not node_run.started_at:
                node_run.started_at = now

            if status in ["success", "failed", "skipped"]:
                node_run.finished_at = now
                if node_run.started_at:
                    duration_ms = int(
                        (now - node_run.started_at).total_seconds() * 1000
                    )
                    node_run.duration_ms = duration_ms

            if output:
                node_run.output_json = {"result": output}

            if error:
                node_run.error_message = error

            await self.session.flush()

    async def _update_node_inputs(
        self,
        run_id: str,
        node_id: str,
        inputs: dict[str, Any],
    ) -> None:
        """Update node run inputs in database.

        Args:
            run_id: Run ID
            node_id: Node ID
            inputs: Rendered input data
        """
        from models.playbook_definition import PlaybookNodeRunModel

        stmt = select(PlaybookNodeRunModel).where(
            PlaybookNodeRunModel.run_id == run_id,
            PlaybookNodeRunModel.node_id == node_id,
        )
        result = await self.session.execute(stmt)
        node_run = result.scalar_one_or_none()

        if node_run:
            node_run.input_json = inputs
            await self.session.flush()

    async def _persist_run_context(
        self,
        run_id: str,
        context: dict[str, Any],
    ) -> None:
        """Persist run context to database.

        Args:
            run_id: Run ID
            context: Current execution context
        """
        from sqlalchemy import update

        from models.playbook_run import PlaybookRunModel

        stmt = (
            update(PlaybookRunModel)
            .where(PlaybookRunModel.id == run_id)
            .values(context_json=context)
        )

        await self.session.execute(stmt)
        await self.session.flush()

    async def _update_run_status(
        self,
        run_id: str,
        status: str,
        outputs: dict[str, Any],
        run_context: dict[str, Any] = None,  # v0.7.3
    ) -> None:
        """Update the overall run status.

        Args:
            run_id: Run ID
            status: Final status
            outputs: Node outputs
            run_context: Final execution context (v0.7.3)
        """
        from repositories.playbook_run_repository import PlaybookRunRepository

        run_repo = PlaybookRunRepository(self.session)

        update_data = {
            "status": status,
            "finished_at": datetime.now(UTC),
            "output_json": {"nodes": outputs},
        }

        # v0.7.3: Persist final context
        if run_context is not None:
            update_data["context_json"] = run_context

        await run_repo.update(run_id, update_data)

    def _get_executable_nodes(
        self,
        definition: DAGDefinition,
        failed_nodes: list[str],
        skipped_nodes: list[str],
    ) -> set[str]:
        """Get nodes that can still execute after failures.

        Args:
            definition: DAG definition
            failed_nodes: List of failed node IDs
            skipped_nodes: List of skipped node IDs

        Returns:
            Set of node IDs that can still execute
        """
        blocked = set(failed_nodes + skipped_nodes)
        executable = set()

        for node_id in definition.nodes:
            if node_id in blocked:
                continue

            deps = definition.get_dependencies(node_id)
            if not any(dep in blocked for dep in deps):
                executable.add(node_id)

        return executable

    async def _send_failure_notification(
        self,
        run_id: str,
        status: str,
        failed_nodes: list[str],
    ) -> None:
        """Send failure notification to Slack if enabled.

        Args:
            run_id: Playbook run ID
            status: Failure status (failed, cancelled, timeout)
            failed_nodes: List of failed node IDs
        """
        try:
            from sqlalchemy import select

            from models.playbook_run import PlaybookRunModel
            from playbook_engine.notifications.slack import SlackNotificationService

            # Get run details
            stmt = select(PlaybookRunModel).where(PlaybookRunModel.id == run_id)
            result = await self.session.execute(stmt)
            run = result.scalar_one_or_none()

            if not run:
                logger.warning(
                    f"[{run_id}] Cannot send failure notification - run not found"
                )
                return

            # Get playbook name
            playbook_name = run.playbook_name or "Unknown Playbook"

            # Get error message from first failed node
            error_message = None
            if failed_nodes:
                from models.playbook_node_run import PlaybookNodeRunModel

                stmt = select(PlaybookNodeRunModel).where(
                    PlaybookNodeRunModel.run_id == run_id,
                    PlaybookNodeRunModel.node_id == failed_nodes[0],
                )
                result = await self.session.execute(stmt)
                node_run = result.scalar_one_or_none()
                if node_run and node_run.error_message:
                    error_message = node_run.error_message

            # Send notification
            slack_service = SlackNotificationService()
            await slack_service.notify_run_failed(
                run_id=run_id,
                playbook_name=playbook_name,
                status=status,
                error_message=error_message,
                failed_nodes=failed_nodes,
            )

        except Exception as e:
            # Don't fail the run if notification fails
            logger.error(f"[{run_id}] Failed to send failure notification: {e}")


@dataclass
@dataclass
class NodeExecutionResult:
    """Result of executing a single DAG node."""

    node_id: str
    status: str
    output: Any = None
    error: str | None = None
    duration_ms: int = 0
