"""
DAG Playbook Execution Service

Handles the core execution orchestration for DAG playbooks, including:
- Permission validation
- DAG compilation and validation
- Queue management
- Dry-run execution
- Apply-mode execution via DAGScheduler

Extracted from routers/playbook_definitions.py (v0.9.0 refactor).
"""

import traceback
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from repositories.playbook_definition_repository import PlaybookDefinitionRepository
from repositories.playbook_run_repository import PlaybookRunRepository
from schemas.playbook_run import (
    DAGPlaybookRunCreate,
    DAGPlaybookRunResponse,
    PlaybookRunErrorResponse,
)
from services.playbook.playbook_dag_compiler import DAGCompiler, DAGValidationError
from services.playbook.playbook_dag_scheduler import DAGScheduler, get_running_scheduler
from services.run_queue_manager import get_run_queue_manager

logger = get_logger(__name__)


class DAGExecutionService:
    """Service for orchestrating DAG playbook execution.

    Delegates to DAGCompiler (validation), DAGScheduler (execution),
    and RunQueueManager (concurrency control).
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.defn_repo = PlaybookDefinitionRepository(session)
        self.run_repo = PlaybookRunRepository(session)

    # ── Main Execution Entry Point ─────────────────────────────────

    async def execute(
        self,
        definition_id: str,
        data: DAGPlaybookRunCreate,
        current_user_id: str,
        current_username: str,
        current_user_role: str,
    ) -> DAGPlaybookRunResponse | PlaybookRunErrorResponse:
        """Execute a DAG playbook (dry_run or apply mode).

        dry_run guarantees:
        - No database writes (except run record for tracking)
        - No audit_logs entries
        - No external network calls
        - DAG validation + mock execution only

        Args:
            definition_id: Playbook definition ID
            data: Run creation parameters (mode, input_context, failure_strategy)
            current_user_id: Authenticated user ID
            current_username: Authenticated username
            current_user_role: Authenticated user role (admin/analyst)

        Returns:
            DAGPlaybookRunResponse on success, or PlaybookRunErrorResponse on error
        """
        trace_id = str(uuid.uuid4())
        is_dry_run = data.mode == "dry_run"

        logger.info(
            f"[{trace_id}] Starting playbook run: definition={definition_id}, "
            f"mode={data.mode}, user={current_username}"
        )

        # ── Permission check ──
        if data.mode == "apply" and current_user_role != "admin":
            return PlaybookRunErrorResponse(
                success=False,
                error_code="PERMISSION_DENIED",
                message="Only admins can execute in apply mode",
                details={"user_role": current_user_role, "required_role": "admin"},
                trace_id=trace_id,
            )

        # ── Get definition ──
        definition = await self.defn_repo.get_by_id(definition_id)
        if not definition:
            return PlaybookRunErrorResponse(
                success=False,
                error_code="DEFINITION_NOT_FOUND",
                message=f"Playbook definition not found: {definition_id}",
                details={"definition_id": definition_id},
                trace_id=trace_id,
            )
        if not definition.is_active:
            return PlaybookRunErrorResponse(
                success=False,
                error_code="DEFINITION_INACTIVE",
                message="Definition is not active",
                details={"definition_id": definition_id, "name": definition.name},
                trace_id=trace_id,
            )

        # ── Validate and compile DAG ──
        dag_json = definition.dag_json
        try:
            compiled = await DAGCompiler.validate_and_compile(dag_json, self.session)
            logger.info(
                f"[{trace_id}] DAG validated: {compiled.get('node_count', 0)} nodes, "
                f"{compiled.get('edge_count', 0)} edges"
            )
        except DAGValidationError as e:
            return PlaybookRunErrorResponse(
                success=False,
                error_code="DAG_VALIDATION_FAILED",
                message=str(e),
                details={"definition_id": definition_id, "dag_error": str(e)},
                trace_id=trace_id,
            )

        # ── Dry-run: mock execution without side effects ──
        if is_dry_run:
            return await self._execute_dry_run(
                definition=definition,
                compiled_dag=compiled,
                input_context=data.input_context,
                failure_strategy=data.failure_strategy,
                current_user_id=current_user_id,
                trace_id=trace_id,
            )

        # ── Apply mode: check queue capacity ──
        queue_manager = get_run_queue_manager()
        can_start = True if not queue_manager else await queue_manager.can_start_run()

        # ── Create run record ──
        run = await self.run_repo.create(
            playbook_name=definition.name,
            playbook_version=definition.version,
            mode=data.mode,
            input_json=data.input_context,
            created_by_user_id=current_user_id,
            engine_version="v0.7",
            execution_mode="dag",
            definition_id=definition_id,
            failure_strategy=data.failure_strategy,
        )

        # ── Queue if at capacity ──
        if not can_start:
            run.status = "queued"
            run.queued_at = datetime.now(UTC)
            await self.session.commit()
            logger.info(f"[{trace_id}] Run {run.id} queued (capacity reached)")

            return self._build_response(run, compiled, trace_id)

        # ── Execute DAG synchronously ──
        try:
            logger.info(f"[{trace_id}] Starting DAG execution for run {run.id}")
            scheduler = DAGScheduler(
                session=self.session,
                run_id=run.id,
                compiled_dag=compiled,
                input_context=data.input_context,
                mode=data.mode,
                failure_strategy=data.failure_strategy,
                created_by_user_id=str(run.created_by_user_id) if run.created_by_user_id else None,
            )
            output = await scheduler.execute()

            final_status = "cancelled" if scheduler.cancelled else "success"
            updates: dict[str, Any] = {
                "status": final_status,
                "output_json": output if not scheduler.cancelled else run.output_json,
            }
            if scheduler.cancelled:
                updates["error_message"] = "Cancelled by user"
            await self.run_repo.update(run.id, updates)
            run.status = final_status
            logger.info(f"[{trace_id}] Run {run.id} completed with status {final_status}")

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[{trace_id}] DAG execution failed: {e}\n{error_trace}")
            await self.run_repo.update(
                run.id, {"status": "failed", "error_message": "DAG execution failed"}
            )

        return self._build_response(run, compiled, trace_id)

    # ── Dry-Run Execution ──────────────────────────────────────────

    async def _execute_dry_run(
        self,
        definition: Any,
        compiled_dag: dict[str, Any],
        input_context: dict[str, Any],
        failure_strategy: str,
        current_user_id: str,
        trace_id: str,
    ) -> DAGPlaybookRunResponse:
        """Execute playbook in dry_run mode with mock execution.

        dry_run guarantees:
        - No database writes (no audit_logs, no node runs)
        - No external network calls
        - DAG validation + mock execution only
        """
        from playbook_engine.v7_dag.registry import get_node_registry

        logger.info(f"[{trace_id}] Executing dry_run mode (no side effects)")

        nodes = compiled_dag.get("nodes", {})
        node_count = len(nodes)
        start_time = datetime.now(UTC)

        # Mock node execution results
        mock_outputs: dict[str, Any] = {}
        completed_nodes: list[str] = []

        for node_id, node_def in nodes.items():
            node_type = node_def.get("type", "unknown")
            node_name = node_def.get("name", node_id)

            try:
                # Check if node type is registered
                registry = get_node_registry()
                if registry and node_type in registry.list_plugins():
                    # Plugin exists - mock success
                    mock_outputs[node_id] = {
                        "status": "success",
                        "node_id": node_id,
                        "node_type": node_type,
                        "message": f"[DRY_RUN] Mock execution for {node_type}",
                        "dry_run": True,
                        "skipped_reason": "dry_run_mode",
                    }
                else:
                    # Unknown node type - still mock success for dry_run
                    mock_outputs[node_id] = {
                        "status": "success",
                        "node_id": node_id,
                        "node_type": node_type,
                        "message": f"[DRY_RUN] Mock execution for unregistered type: {node_type}",
                        "dry_run": True,
                        "skipped_reason": "dry_run_mode",
                    }
                completed_nodes.append(node_id)
                logger.info(
                    f"[{trace_id}] [DRY_RUN] Mock executed node {node_id} ({node_type})"
                )

            except Exception as e:
                logger.warning(f"[{trace_id}] [DRY_RUN] Node {node_id} mock failed: {e}")
                mock_outputs[node_id] = {
                    "status": "success",  # Always success in dry_run
                    "node_id": node_id,
                    "error": str(e),
                    "dry_run": True,
                }
                completed_nodes.append(node_id)

        end_time = datetime.now(UTC)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        return DAGPlaybookRunResponse(
            id=f"dry_run_{trace_id}",  # Virtual ID for dry_run
            playbook_name=definition.name,
            playbook_version=definition.version,
            engine_version="v0.7",
            mode="dry_run",
            status="success",
            failure_strategy=failure_strategy,
            created_by_user_id=current_user_id,
            input_json=input_context,
            output_json={
                "nodes": mock_outputs,
                "dry_run": True,
                "message": "Dry run completed - no actual actions taken",
                "node_count": node_count,
                "duration_ms": duration_ms,
            },
            started_at=start_time,
            finished_at=end_time,
            error_message=None,
            definition_id=definition.id,
            execution_mode="dag",
            total_nodes=node_count,
            completed_nodes=node_count,
            failed_nodes=0,
            running_nodes=0,
            pending_nodes=0,
            cancel_requested_at=None,
            can_resume=False,
        )

    # ── Run Cancellation ────────────────────────────────────────────

    async def cancel_run(self, run_id: str, reason: str) -> dict[str, Any]:
        """Cancel a running DAG playbook.

        Args:
            run_id: Run ID to cancel
            reason: Cancellation reason

        Returns:
            {run_id, status, message}
        """
        run = await self.run_repo.get_by_id(run_id)
        if not run:
            return {"run_id": run_id, "status": "not_found", "message": "Run not found"}

        if run.status not in ("pending", "running"):
            return {
                "run_id": run_id,
                "status": "invalid_state",
                "message": f"Cannot cancel run in status: {run.status}",
            }

        scheduler = get_running_scheduler(run_id)
        if scheduler:
            await scheduler.cancel(reason or "Cancelled by user")

        await self.run_repo.update(
            run_id,
            {"status": "cancelled", "error_message": reason or "Cancelled by user"},
        )

        return {
            "run_id": run_id,
            "status": "cancelled",
            "message": "Run cancelled successfully",
        }

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _build_response(
        run: Any,
        compiled: dict[str, Any],
        trace_id: str,
    ) -> DAGPlaybookRunResponse:
        """Build a DAGPlaybookRunResponse from run record and compiled DAG."""
        return DAGPlaybookRunResponse(
            id=run.id,
            playbook_name=run.playbook_name,
            playbook_version=run.playbook_version,
            engine_version=run.engine_version,
            mode=run.mode,
            status=run.status,
            failure_strategy=run.failure_strategy,
            created_by_user_id=run.created_by_user_id,
            input_json=run.input_json,
            output_json=run.output_json,
            started_at=run.started_at,
            finished_at=run.finished_at,
            error_message=run.error_message,
            definition_id=run.definition_id,
            execution_mode=run.execution_mode,
            total_nodes=compiled.get("node_count", 0),
            completed_nodes=0,
            failed_nodes=0 if run.status == "success" else 1,
            running_nodes=0,
            pending_nodes=0,
            cancel_requested_at=None,
            can_resume=False,
        )
