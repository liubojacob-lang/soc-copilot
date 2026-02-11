"""Playbook execution engine for running linear step-based playbooks."""

import uuid
import asyncio
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from .registry import get_registry
from .models import StepResult
from db.session import AsyncSessionLocal

logger = get_logger(__name__)


class PlaybookExecutionEngine:
    """Engine for executing linear playbook workflows."""

    def __init__(self, session: AsyncSession):
        """Initialize the execution engine."""
        self.session = session
        self.registry = get_registry()

    async def run_playbook(
        self,
        playbook_name: str,
        input_json: dict[str, Any],
        mode: str = "dry_run",
        created_by_user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute a playbook from start to finish.

        Args:
            playbook_name: Name of the playbook to run
            input_json: Input data for the playbook
            mode: Execution mode (dry_run or apply)
            created_by_user_id: User ID who initiated the run

        Returns:
            Dictionary with run_id and final status
        """
        from schemas.playbook_run import AVAILABLE_PLAYBOOKS

        if playbook_name not in AVAILABLE_PLAYBOOKS:
            raise ValueError(f"Unknown playbook: {playbook_name}")

        playbook_config = AVAILABLE_PLAYBOOKS[playbook_name]
        step_ids = playbook_config["steps"]

        # Import the run model here to avoid circular dependency
        from models.playbook_run import PlaybookRunModel
        from repositories.playbook_run_repository import PlaybookRunRepository

        run_repo = PlaybookRunRepository(self.session)

        # Create playbook run record
        run = await run_repo.create(
            playbook_name=playbook_name,
            playbook_version=playbook_config["version"],
            mode=mode,
            status="running",
            created_by_user_id=created_by_user_id,
            input_json=input_json,
            output_json={"steps": []},
        )

        # Commit immediately to ensure run is persisted
        await self.session.flush()

        logger.info(f"[{run.id}] Starting playbook '{playbook_name}' in {mode} mode")

        # Execute steps directly (synchronously within the request)
        await self._execute_steps_in_session(
            self.session, run.id, playbook_name, step_ids, input_json, mode
        )

        # Commit all changes to ensure persistence
        await self.session.flush()

        # Get final status
        final_run = await run_repo.get_by_id(run.id)

        return {
            "run_id": run.id,
            "status": final_run.status if final_run else "unknown",
            "playbook_name": playbook_name,
            "playbook_version": playbook_config["version"],
            "mode": mode,
        }

    async def resume_playbook_run(
        self,
        run_id: str,
        from_step_index: int = 0,
        run_mode: Optional[str] = None,
    ) -> dict[str, Any]:
        """Resume a playbook run from a specific step.

        Args:
            run_id: ID of the run to resume
            from_step_index: Step index to resume from (0-based)
            run_mode: Optional override for run mode

        Returns:
            Dictionary with updated status
        """
        from models.playbook_run import PlaybookRunModel
        from repositories.playbook_run_repository import PlaybookRunRepository

        run_repo = PlaybookRunRepository(self.session)
        run = await run_repo.get_by_id(run_id)

        if not run:
            raise ValueError(f"Run not found: {run_id}")

        if run.status not in ["failed", "partial", "running"]:
            raise ValueError(f"Cannot resume run with status: {run.status}")

        # Get playbook configuration
        from schemas.playbook_run import AVAILABLE_PLAYBOOKS
        playbook_config = AVAILABLE_PLAYBOOKS[run.playbook_name]
        step_ids = playbook_config["steps"]

        # Update mode if specified
        if run_mode and run_mode != run.mode:
            await run_repo.update(run_id, {"mode": run_mode})

        # Resume execution
        asyncio.create_task(self._execute_steps(
            run_id, run.playbook_name, step_ids[from_step_index:],
            run.input_json, run.mode, from_step_index
        ))

        return {
            "run_id": run_id,
            "status": "running",
            "from_step": from_step_index,
        }

    async def _execute_steps_in_session(
        self,
        session: AsyncSession,
        run_id: str,
        playbook_name: str,
        step_ids: list[str],
        input_json: dict[str, Any],
        mode: str,
        start_index: int = 0,
    ) -> None:
        """Execute playbook steps sequentially using existing session.

        Args:
            session: Existing database session
            run_id: Playbook run ID
            playbook_name: Name of the playbook
            step_ids: List of step IDs to execute
            input_json: Input data for all steps
            mode: Execution mode (dry_run or apply)
            start_index: Starting step index
        """
        from models.playbook_run import PlaybookRunModel
        from repositories.playbook_run_repository import PlaybookRunRepository

        run_repo = PlaybookRunRepository(session)

        steps_output = []
        failed_steps = []
        skipped_steps = []

        try:
            for idx, step_id in enumerate(step_ids):
                if idx < start_index:
                    # Skip steps before the resume point
                    continue

                await self._execute_single_step(
                    session, run_id, idx, step_id, input_json, mode, steps_output
                )

            # All steps completed successfully
            await run_repo.update(run_id, {
                "status": "success",
                "finished_at": datetime.now(),
                "output_json": {"steps": steps_output},
            })
            logger.info(f"[{run_id}] Playbook completed successfully")

        except Exception as e:
            logger.error(f"[{run_id}] Playbook execution error: {e}")
            await run_repo.update(run_id, {
                "status": "failed",
                "finished_at": datetime.now(),
                "error_message": str(e),
                "output_json": {"steps": steps_output},
            })
            raise  # Re-raise so caller can handle

    async def _execute_steps(
        self,
        run_id: str,
        playbook_name: str,
        step_ids: list[str],
        input_json: dict[str, Any],
        mode: str,
        start_index: int = 0,
    ) -> None:
        """Execute playbook steps sequentially.

        Args:
            run_id: Playbook run ID
            playbook_name: Name of the playbook
            step_ids: List of step IDs to execute
            input_json: Input data for all steps
            mode: Execution mode (dry_run or apply)
            start_index: Starting step index
        """
        # Create a new session for the background task
        async with AsyncSessionLocal() as session:
            from models.playbook_run import PlaybookRunModel
            from repositories.playbook_run_repository import PlaybookRunRepository

            run_repo = PlaybookRunRepository(session)

            steps_output = []
            failed_steps = []
            skipped_steps = []

            try:
                for idx, step_id in enumerate(step_ids):
                    if idx < start_index:
                        # Skip steps before the resume point
                        continue

                    await self._execute_single_step(
                        session, run_id, idx, step_id, input_json, mode, steps_output
                    )

                # All steps completed successfully
                await run_repo.update(run_id, {
                    "status": "success",
                    "finished_at": datetime.now(),
                    "output_json": {"steps": steps_output},
                })
                logger.info(f"[{run_id}] Playbook completed successfully")

            except Exception as e:
                logger.error(f"[{run_id}] Playbook execution error: {e}")
                await run_repo.update(run_id, {
                    "status": "failed",
                    "finished_at": datetime.now(),
                    "error_message": str(e),
                    "output_json": {"steps": steps_output},
                })
            finally:
                await session.commit()

    async def _execute_single_step(
        self,
        session: AsyncSession,
        run_id: str,
        step_index: int,
        step_id: str,
        input_json: dict[str, Any],
        mode: str,
        steps_output: list,
    ) -> StepResult:
        """Execute a single playbook step.

        Args:
            session: Database session to use
            run_id: Playbook run ID
            step_index: Index of the step
            step_id: Step identifier
            input_json: Input data
            mode: Execution mode
            steps_output: Accumulated step outputs

        Returns:
            StepResult object with execution results
        """
        from models.playbook_run import PlaybookRunStepModel
        from repositories.playbook_run_repository import PlaybookRunRepository

        step_repo = PlaybookRunRepository(session)

        # Create step record
        step = await step_repo.create_step(
            run_id=run_id,
            step_index=step_index,
            step_id=step_id,
            step_name=self.registry.get_step_name(step_id),
            step_type=self.registry.get_step_type(step_id),
            status="running",
            input_json=input_json,
            output_json={},
        )

        step_result = StepResult(
            step_id=step_id,
            success=False,
            output={},
            error=None,
            skipped=False,
            skipped_reason=None,
        )

        start_time = datetime.now()

        try:
            logger.info(f"[{run_id}] Executing step {step_index}: {step_id}")

            # Get step implementation from registry
            step_impl = self.registry.get_step_implementation(step_id)

            # Check if mode applies (some steps may not support apply mode)
            if mode == "apply" and not step_impl.supports_apply:
                step_result.skipped = True
                step_result.skipped_reason = f"Step does not support apply mode"
                await self._mark_step_skipped(session, step.id, step_result.skipped_reason)
                return step_result

            # Build enriched input: original input + outputs from previous steps
            enriched_input = {**input_json}
            for prev_output in steps_output:
                if "output" in prev_output and isinstance(prev_output["output"], dict):
                    enriched_input.update(prev_output["output"])

            # Execute the step with enriched input
            if asyncio.iscoroutinefunction(step_impl.execute):
                result = await step_impl.execute(enriched_input, mode)
            else:
                result = step_impl.execute(enriched_input, mode)

            step_result.success = True
            step_result.output = result

            # Update step as success
            await step_repo.update_by_id(step.id, {
                "status": "success",
                "finished_at": datetime.now(),
                "output_json": {"result": result},
            })

            logger.info(f"[{run_id}] Step {step_index} ({step_id}) completed successfully")

        except Exception as e:
            logger.error(f"[{run_id}] Step {step_index} ({step_id}) failed: {e}")
            step_result.error = str(e)
            step_result.success = False

            # Update step as failed
            await step_repo.update_by_id(step.id, {
                "status": "failed",
                "finished_at": datetime.now(),
                "error_text": str(e),
            })

            raise  # Re-raise to stop playbook execution

        finally:
            # Calculate duration
            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Update step with duration
            await step_repo.update_by_id(step.id, {"duration_ms": duration_ms})

            # Add to accumulated output
            steps_output.append({
                "step_index": step_index,
                "step_id": step_id,
                "step_name": self.registry.get_step_name(step_id),
                "status": "success" if step_result.success else ("skipped" if step_result.skipped else "failed"),
                "output": step_result.output,
                "error": step_result.error,
                "skipped_reason": step_result.skipped_reason,
                "duration_ms": duration_ms,
            })

        return step_result

    async def _mark_step_skipped(self, session: AsyncSession, step_id: str, reason: str) -> None:
        """Mark a step as skipped.

        Args:
            session: Database session to use
            step_id: Step ID
            reason: Reason for skipping
        """
        from repositories.playbook_run_repository import PlaybookRunRepository

        step_repo = PlaybookRunRepository(session)
        await step_repo.update_by_id(step_id, {
            "status": "skipped",
            "finished_at": datetime.now(),
            "skipped_reason": reason,
        })
