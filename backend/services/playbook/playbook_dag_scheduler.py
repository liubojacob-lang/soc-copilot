"""DAG Playbook Scheduler - async concurrent execution engine."""

import asyncio
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from playbook_engine.v7_dag.registry import get_node_registry

logger = get_logger(__name__)

# 运行中的 scheduler 注册表，供 cancel API 调用
_running_schedulers: dict[str, "DAGScheduler"] = {}


def get_running_scheduler(run_id: str) -> Optional["DAGScheduler"]:
    """供 cancel API 使用：获取正在执行的 scheduler 以调用 cancel()。"""
    return _running_schedulers.get(run_id)


class DAGScheduler:
    """Async DAG scheduler with concurrent execution, retry, and cancellation support."""

    def __init__(
        self,
        session: AsyncSession,
        run_id: str,
        compiled_dag: dict[str, Any],
        input_context: dict[str, Any],
        mode: str = "apply",
        failure_strategy: str = "fail_fast",
        created_by_user_id: str | None = None,
    ):
        self.session = session
        self.run_id = run_id
        self.compiled_dag = compiled_dag
        self.input_context = input_context
        self.mode = mode
        self.failure_strategy = failure_strategy
        self.created_by_user_id = created_by_user_id

        # Runtime state
        self.cancelled = False
        self._secrets_cache: dict[str, str] | None = None
        self.node_outputs: dict[str, dict[str, Any]] = {}
        self.completed_nodes: set[str] = set()
        self.failed_nodes: set[str] = set()

        # Get node registry
        self.registry = get_node_registry()
        if not self.registry:
            logger.warning(
                f"[{run_id}] Node registry not initialized, auto-loading plugins..."
            )
            from pathlib import Path

            from playbook_engine.v7_dag.registry import NodeRegistry

            registry = NodeRegistry()
            plugin_dir = (
                Path(__file__).parent.parent / "playbook_engine" / "v7_dag" / "plugins"
            )
            registry.auto_load_plugins(plugin_dir)
            from playbook_engine.v7_dag.registry import set_node_registry

            set_node_registry(registry)
            self.registry = registry

    async def execute(self) -> dict[str, Any]:
        """Execute the DAG playbook."""
        global _running_schedulers
        logger.info(f"Starting DAG execution for run {self.run_id}")
        _running_schedulers[self.run_id] = self
        try:
            # Execute from root nodes
            await self._execute_from_roots()

            # Wait for all nodes to complete
            await self._wait_for_completion()

            # Compile final output
            output = await self._compile_output()

            logger.info(f"DAG execution completed for run {self.run_id}")
            return output

        except asyncio.CancelledError:
            logger.warning(f"DAG execution cancelled for run {self.run_id}")
            raise
        except Exception as e:
            logger.error(f"DAG execution failed for run {self.run_id}: {e}")
            raise
        finally:
            _running_schedulers.pop(self.run_id, None)

    async def _load_secrets(self) -> dict[str, str]:
        """加载密钥供节点使用（如 {{secret.xxx}}）。密钥未配置或解密失败时返回空 dict。

        使用独立的临时 session：并发节点会同时调用本方法，而 AsyncSession
        不允许并发使用（scheduler 的共享 session 留给 run 状态更新）。
        """
        if self._secrets_cache is not None:
            return self._secrets_cache
        out: dict[str, str] = {}
        try:
            from db.session import AsyncSessionLocal
            from repositories.secret_repository import SecretRepository
            from services.security.secret_service import get_secret_service

            svc = get_secret_service()
            async with AsyncSessionLocal() as session:
                repo = SecretRepository(session)
                items = await repo.list_all(limit=500, offset=0)
                for s in items:
                    try:
                        out[s.name] = svc.decrypt(s.encrypted_value)
                    except Exception as e:
                        logger.warning(
                            f"[{self.run_id}] Failed to decrypt secret {s.name}: {e}"
                        )
        except ValueError as e:
            logger.debug(f"[{self.run_id}] Secrets not available: {e}")
        except Exception as e:
            logger.warning(f"[{self.run_id}] Load secrets failed: {e}")
        self._secrets_cache = out
        return out

    async def _execute_from_roots(self) -> None:
        """Start execution from root nodes."""
        root_nodes = self.compiled_dag.get("root_nodes", [])

        for node_id in root_nodes:
            asyncio.create_task(self._execute_node(node_id))

        logger.info(f"Started execution from {len(root_nodes)} root nodes")

    async def _execute_node(self, node_id: str) -> None:
        """Execute a single node with retry logic."""
        if self.cancelled:
            return

        if node_id in self.completed_nodes or node_id in self.failed_nodes:
            return

        # Check dependencies
        incoming = self.compiled_dag.get("incoming", {}).get(node_id, [])
        for edge in incoming:
            source_id = edge["source"]
            if source_id not in self.completed_nodes:
                logger.info(f"Node {node_id}: dependency {source_id} not complete")
                return

        try:
            node_def = self.compiled_dag["nodes"][node_id]
            node_type = node_def.get("type")
            node_name = node_def.get("name", node_id)

            # Execute node via plugin
            output = await self._execute_node_plugin(
                node_id=node_id,
                node_type=node_type,
                node_name=node_name,
                node_def=node_def,
            )

            self.node_outputs[node_id] = output

            # Check if node succeeded
            if output.get("status") in ("success", "skipped"):
                self.completed_nodes.add(node_id)
                logger.info(
                    f"Node {node_id} ({node_name}) completed with status: {output.get('status')}"
                )
            else:
                self.failed_nodes.add(node_id)
                logger.error(
                    f"Node {node_id} ({node_name}) failed: {output.get('error', 'Unknown error')}"
                )

                if self.failure_strategy == "fail_fast":
                    await self.cancel(f"Node {node_id} failed")
                    return

            # Start dependent nodes
            await self._start_dependent_nodes(node_id)

        except Exception as e:
            error = str(e)
            logger.error(f"Node {node_id} failed with exception: {error}")
            self.failed_nodes.add(node_id)
            self.node_outputs[node_id] = {"status": "error", "error": error}

            if self.failure_strategy == "fail_fast":
                await self.cancel(f"Node {node_id} failed: {error}")

    async def _execute_node_plugin(
        self, node_id: str, node_type: str, node_name: str, node_def: dict
    ) -> dict[str, Any]:
        """Execute a node using the plugin registry."""
        from playbook_engine.v7_dag.base_node import NodeExecutionContext

        # Map node type to plugin ID
        plugin_id = self._get_plugin_id(node_type)

        if not plugin_id:
            # For unknown types, return mock output for now
            logger.warning(
                f"No plugin found for node type: {node_type}, using mock execution"
            )
            return {
                "status": "success",
                "message": f"Mock execution for {node_type}",
                "node_id": node_id,
            }

        try:
            # Get plugin instance
            plugin = self.registry.get_plugin(plugin_id)

            # Build execution context
            # Collect outputs from parent nodes as input
            parent_outputs = {}
            incoming = self.compiled_dag.get("incoming", {}).get(node_id, [])
            for edge in incoming:
                source_id = edge["source"]
                if source_id in self.node_outputs:
                    parent_outputs[source_id] = self.node_outputs[source_id]

            # Build input from node config + original context + parent outputs
            # Priority: node config < run input < parent outputs
            node_config = (
                node_def.get("config", {}) if isinstance(node_def, dict) else {}
            )
            input_json = dict(node_config)
            input_json.update(self.input_context)
            input_json.update(parent_outputs)

            # Validate input if plugin supports it
            try:
                plugin.validate_input(input_json)
            except ValueError as ve:
                logger.error(f"Input validation failed for {node_id}: {ve}")
                return {"status": "error", "error": f"Input validation failed: {ve}"}

            secrets = await self._load_secrets()
            context = NodeExecutionContext(
                run_id=self.run_id,
                node_id=node_id,
                node_name=node_name,
                input_json=input_json,
                mode=self.mode,
                secrets=secrets,
                context={
                    "node_outputs": self.node_outputs,
                    "created_by_user_id": self.created_by_user_id,
                },
            )

            # Execute plugin
            logger.info(f"Executing plugin {plugin_id} for node {node_id}")
            result = await plugin.execute(context)
            return result

        except Exception as e:
            logger.error(f"Plugin execution failed for {node_id}: {e}")
            return {"status": "error", "error": str(e), "node_id": node_id}

    def _get_plugin_id(self, node_type: str) -> str | None:
        """Map node type to plugin ID."""
        # Direct mappings
        type_to_plugin = {
            "ti_lookup_otx": "builtin_otx_lookup",
            "extract_iocs": "builtin_extract_iocs",
            "normalize": "builtin_normalize",
            "generate_report": "builtin_generate_report",
            "slack_notify": "builtin_slack_notify",
            "http_request": "builtin_http_request",
            "decision": "builtin_decision",
            "sleep": "builtin_sleep",
            "parse_json": "builtin_parse_json",
            "asset_enrich": "builtin_asset_enrich",
            "risk_score": "builtin_risk_score",
            "action_plan": "builtin_action_plan",
            "timeline_build": "builtin_timeline_build",
            "human_approval": "builtin_human_approval",
        }

        if node_type in type_to_plugin:
            return type_to_plugin[node_type]

        # Check if plugin exists with this name
        available = self.registry.list_plugins()
        if node_type in available:
            return node_type

        # Try with builtin_ prefix
        builtin_name = f"builtin_{node_type}"
        if builtin_name in available:
            return builtin_name

        return None

    async def _start_dependent_nodes(self, completed_node_id: str) -> None:
        """Start execution of dependent nodes."""
        outgoing = self.compiled_dag.get("outgoing", {}).get(completed_node_id, [])

        for edge in outgoing:
            target_id = edge["target"]
            condition = edge.get("condition")

            # Skip if condition evaluates to false
            if condition and not await self._evaluate_condition(
                condition, completed_node_id
            ):
                continue

            # Start dependent node
            asyncio.create_task(self._execute_node(target_id))

    async def _evaluate_condition(self, condition: str, source_node_id: str) -> bool:
        """Evaluate a condition expression."""
        # Simple implementation - evaluate basic conditions
        # Format examples: "result == true", "status == success", "threat_score > 3"

        if not condition:
            return True

        # Get source node output
        source_output = self.node_outputs.get(source_node_id, {})

        try:
            # Handle simple boolean condition
            if condition == "true":
                return True
            if condition == "false":
                return False

            # Handle result == true/false
            if "result == true" in condition or "result == True" in condition:
                return source_output.get("result", False) == True
            if "result == false" in condition or "result == False" in condition:
                return source_output.get("result", False) == False

            # Handle status checks
            if "status == success" in condition:
                return source_output.get("status") == "success"

            # Handle numeric comparisons (e.g., threat_score >= 3)
            import re

            match = re.match(r"(\w+)\s*([>=<]+)\s*(\d+)", condition)
            if match:
                field, op, value = match.groups()
                field_val = source_output.get(field, 0)
                num_val = int(value)

                if op == ">=":
                    return field_val >= num_val
                elif op == ">":
                    return field_val > num_val
                elif op == "<=":
                    return field_val <= num_val
                elif op == "<":
                    return field_val < num_val
                elif op == "==":
                    return field_val == num_val

            # Default to true for unknown conditions
            return True

        except Exception as e:
            logger.warning(f"Condition evaluation failed for '{condition}': {e}")
            return True

    async def _wait_for_completion(self) -> None:
        """Wait for all nodes to complete or fail."""
        max_wait_seconds = 3600
        start_time = asyncio.get_event_loop().time()

        while not self.cancelled:
            total = len(self.compiled_dag.get("nodes", {}))
            completed = len(self.completed_nodes) + len(self.failed_nodes)

            if completed >= total and total > 0:
                break

            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait_seconds:
                await self.cancel("Execution timeout")
                break

            await asyncio.sleep(1)

    async def _compile_output(self) -> dict[str, Any]:
        """Compile final output from node outputs."""
        # Find final outputs (from leaf nodes or report generation)
        final_outputs = {}

        for node_id, output in self.node_outputs.items():
            node_def = self.compiled_dag["nodes"].get(node_id, {})
            node_type = node_def.get("type", "")

            # Include important outputs
            if node_type in ("generate_report", "ti_lookup_otx", "extract_iocs"):
                final_outputs[node_id] = output

        return {
            "nodes": self.node_outputs,
            "final_outputs": final_outputs,
            "summary": {
                "total_nodes": len(self.compiled_dag.get("nodes", {})),
                "completed_nodes": len(self.completed_nodes),
                "failed_nodes": len(self.failed_nodes),
            },
        }

    async def cancel(self, reason: str = "Cancelled by user") -> None:
        """Cancel the DAG execution."""
        logger.info(f"Cancelling run {self.run_id}: {reason}")
        self.cancelled = True
