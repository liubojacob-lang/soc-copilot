"""AI Task Queue Service for background processing.

This service provides:
- Async task creation and submission
- Priority-ordered background processing (higher priority first, FIFO
  within the same priority)
- Crash recovery: on startup, pending tasks left in the DB by a previous
  process are re-enqueued and stale "processing" rows are marked failed
- Background task processing with timeout handling
- Status polling for long-running AI operations
- Automatic retry on transient failures
"""

import asyncio
import itertools
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from core.logger import get_logger
from models.ai_task import AITaskModel, AITaskStatus, AITaskType
from services.llm_retry import get_llm_retry_service

logger = get_logger(__name__)

# Priority queue: items are (-priority, seq, task_id) so higher priority
# pops first and the unique seq keeps ordering FIFO within a priority
# (and stops heapq from ever comparing task_id strings).
_task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
_task_seq = itertools.count()
_background_processor: asyncio.Task | None = None


def _queue_item(task_id: str, priority: int) -> tuple[int, int, str]:
    return (-priority, next(_task_seq), task_id)


class AITaskQueueService:
    """Service for managing AI background tasks."""

    def __init__(self, session_factory):
        """Initialize the task queue service.

        Args:
            session_factory: AsyncSessionLocal factory for DB access
        """
        self.session_factory = session_factory
        self._processor_task: asyncio.Task | None = None
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._max_concurrent = 5  # Max concurrent AI tasks

    async def submit_task(
        self,
        task_type: AITaskType,
        prompt: str,
        input_data: dict[str, Any] | None = None,
        model_id: str | None = None,
        provider: str | None = None,
        user_id: str | None = None,
        timeout_seconds: int = 300,
        priority: int = 0,
    ) -> str:
        """Submit a new AI task for background processing.

        Args:
            task_type: Type of AI task
            prompt: The prompt to send to the AI
            input_data: Additional input data
            model_id: Specific model to use
            provider: AI provider to use
            user_id: User who submitted the task
            timeout_seconds: Task timeout in seconds
            priority: Task priority (higher = more urgent)

        Returns:
            Task ID for status polling
        """
        task_id = str(uuid.uuid4())

        async with self.session_factory() as session:
            task = AITaskModel(
                id=task_id,
                task_type=task_type.value,
                status=AITaskStatus.PENDING.value,
                prompt=prompt,
                input_data=input_data or {},
                model_id=model_id,
                provider=provider,
                user_id=user_id,
                timeout_seconds=timeout_seconds,
                priority=priority,
            )
            session.add(task)
            await session.commit()

        # Add to processing queue
        await _task_queue.put(_queue_item(task_id, priority))
        logger.info(f"Submitted AI task {task_id} type={task_type.value}")

        return task_id

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """Get the current status of an AI task.

        Args:
            task_id: Task ID to check

        Returns:
            Task status dictionary or None if not found
        """
        async with self.session_factory() as session:
            stmt = select(AITaskModel).where(AITaskModel.id == task_id)
            result = await session.execute(stmt)
            task = result.scalar_one_or_none()

            if not task:
                return None

            # Check for timeout
            if task.is_timeout:
                task.status = AITaskStatus.TIMEOUT.value
                task.error_message = (
                    f"Task timed out after {task.timeout_seconds} seconds"
                )
                task.completed_at = datetime.now(UTC)
                await session.commit()

            return task.to_dict()

    async def get_task_result(self, task_id: str) -> dict[str, Any] | None:
        """Get the result of a completed AI task.

        Args:
            task_id: Task ID to get result for

        Returns:
            Task result or None if not completed
        """
        status = await self.get_task_status(task_id)
        if not status:
            return None

        if status["status"] != AITaskStatus.COMPLETED.value:
            return None

        return status.get("result")

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or processing task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if cancelled, False if not possible
        """
        async with self.session_factory() as session:
            stmt = select(AITaskModel).where(AITaskModel.id == task_id)
            result = await session.execute(stmt)
            task = result.scalar_one_or_none()

            if not task or task.is_terminal:
                return False

            task.status = AITaskStatus.FAILED.value
            task.error_message = "Task cancelled by user"
            task.completed_at = datetime.now(UTC)
            await session.commit()

            # Cancel running asyncio task if exists
            if task_id in self._running_tasks:
                self._running_tasks[task_id].cancel()
                del self._running_tasks[task_id]

            logger.info(f"Cancelled AI task {task_id}")
            return True

    async def _process_task(self, task_id: str) -> None:
        """Process a single AI task.

        Args:
            task_id: Task ID to process
        """
        async with self.session_factory() as session:
            # Get task
            stmt = select(AITaskModel).where(AITaskModel.id == task_id)
            result = await session.execute(stmt)
            task = result.scalar_one_or_none()

            if not task:
                logger.warning(f"Task {task_id} not found")
                return

            # Update status
            task.status = AITaskStatus.PROCESSING.value
            task.started_at = datetime.now(UTC)
            await session.commit()

        try:
            # Process the task via the retry-aware LLM service. All task
            # types currently produce free-form text (no fixed schema), so
            # response_class=None routes through the free-form path that
            # skips pydantic coercion. When a concrete schema is introduced
            # for a task type, pass it here instead of None.
            llm_service = get_llm_retry_service()

            result, model_used, degraded = await asyncio.wait_for(
                llm_service.generate_structured(
                    prompt=task.prompt,
                    response_class=None,
                ),
                timeout=task.timeout_seconds,
            )

            # Update with result
            async with self.session_factory() as session:
                stmt = select(AITaskModel).where(AITaskModel.id == task_id)
                result_db = await session.execute(stmt)
                task = result_db.scalar_one_or_none()

                if task:
                    task.status = AITaskStatus.COMPLETED.value
                    task.result = {
                        "content": result,
                        "model_used": model_used,
                        "degraded": degraded,
                    }
                    task.completed_at = datetime.now(UTC)

                    # T2.5: Backfill AI triage result into alert.raw_data
                    if (
                        task.task_type
                        in (AITaskType.ALERT_ANALYSIS.value, "alert_analysis")
                        and task.input_data
                        and task.input_data.get("alert_id")
                    ):
                        await self._backfill_alert_triage(
                            session, task, result, model_used, degraded
                        )

                    await session.commit()
                    logger.info(f"Completed AI task {task_id}")

        except TimeoutError:
            await self._handle_task_error(
                task_id,
                f"Task timed out after {task.timeout_seconds} seconds",
                is_timeout=True,
            )
        except asyncio.CancelledError:
            await self._handle_task_error(task_id, "Task was cancelled")
        except Exception as e:
            await self._handle_task_error(task_id, str(e))
            # Retry if possible
            await self._maybe_retry_task(task_id)

    async def _backfill_alert_triage(
        self,
        session,
        task: AITaskModel,
        result: Any,
        model_used: str,
        degraded: bool,
    ) -> None:
        """T2.5: Write AI triage result back to the associated SecurityAlert."""
        try:
            import re

            from sqlalchemy.orm.attributes import flag_modified

            from models.security_alert import SecurityAlert

            raw_alert_id = task.input_data.get("alert_id")
            try:
                alert_id = int(raw_alert_id)
            except (ValueError, TypeError):
                alert_id = raw_alert_id

            stmt = select(SecurityAlert).where(SecurityAlert.id == alert_id)
            res = await session.execute(stmt)
            alert = res.scalar_one_or_none()
            if not alert:
                logger.warning(
                    f"T2.5: Alert {alert_id} not found for AI task {task.id}"
                )
                return

            raw = dict(alert.raw_data or {})
            pipeline = dict(raw.get("pipeline") or {})

            summary_text = ""
            if isinstance(result, dict):
                summary_text = (
                    result.get("summary")
                    or result.get("content")
                    or ""
                )
            elif isinstance(result, str):
                summary_text = result[:1000]

            pipeline["ai_triage"] = {
                "summary": summary_text,
                "completed_at": datetime.now(UTC).isoformat(),
                "task_id": task.id,
                "model_used": model_used,
                "degraded": degraded,
            }

            # Attempt to extract suggested severity
            if isinstance(result, dict) and result.get("severity"):
                pipeline["ai_suggested_severity"] = str(result["severity"]).lower()
            elif isinstance(result, str):
                m = re.search(
                    r"\b(?:severity|建议严重度|严重度|级别)\s*[:=：]\s*(critical|high|medium|low)\b",
                    result,
                    re.IGNORECASE,
                )
                if m:
                    pipeline["ai_suggested_severity"] = m.group(1).lower()

            raw["pipeline"] = pipeline
            alert.raw_data = raw
            flag_modified(alert, "raw_data")
            logger.info(f"T2.5: Backfilled AI triage result to alert {alert_id}")
        except Exception as e:
            logger.error(f"T2.5: Failed to backfill alert triage: {e}", exc_info=True)


    async def _handle_task_error(
        self, task_id: str, error_message: str, is_timeout: bool = False
    ) -> None:
        """Handle task error and update status."""
        async with self.session_factory() as session:
            stmt = select(AITaskModel).where(AITaskModel.id == task_id)
            result = await session.execute(stmt)
            task = result.scalar_one_or_none()

            if task:
                task.status = (
                    AITaskStatus.TIMEOUT.value
                    if is_timeout
                    else AITaskStatus.FAILED.value
                )
                task.error_message = error_message
                task.completed_at = datetime.now(UTC)
                await session.commit()
                logger.error(f"AI task {task_id} failed: {error_message}")

    async def _maybe_retry_task(self, task_id: str) -> None:
        """Retry task if retries remaining."""
        async with self.session_factory() as session:
            stmt = select(AITaskModel).where(AITaskModel.id == task_id)
            result = await session.execute(stmt)
            task = result.scalar_one_or_none()

            if task and task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = AITaskStatus.PENDING.value
                task.error_message = None
                task.completed_at = None
                task.started_at = None
                await session.commit()

                # Re-queue
                await _task_queue.put(_queue_item(task_id, task.priority))
                logger.info(
                    f"Retrying AI task {task_id} (attempt {task.retry_count}/{task.max_retries})"
                )

    async def recover_orphaned_tasks(self) -> tuple[int, int]:
        """Recover tasks orphaned by a previous process crash/restart.

        The in-memory queue dies with the process, so at startup any DB row
        still pending/processing belongs to a previous lifetime:

        - ``pending``    → re-enqueued with its original priority
        - ``processing`` → the worker died mid-run; mark failed so the row
          does not sit as a zombie forever (callers can resubmit)

        Returns:
            (requeued, failed) counts.
        """
        requeued = failed = 0
        async with self.session_factory() as session:
            stmt = select(AITaskModel).where(
                AITaskModel.status.in_(
                    [AITaskStatus.PENDING.value, AITaskStatus.PROCESSING.value]
                )
            )
            result = await session.execute(stmt)
            orphans = list(result.scalars().all())

            for task in orphans:
                if task.status == AITaskStatus.PENDING.value:
                    await _task_queue.put(_queue_item(task.id, task.priority))
                    requeued += 1
                else:
                    task.status = AITaskStatus.FAILED.value
                    task.error_message = (
                        "orphaned by restart: worker exited before completion; "
                        "resubmit if still needed"
                    )
                    task.completed_at = datetime.now(UTC)
                    failed += 1
                    logger.warning(
                        f"AI task {task.id} orphaned in 'processing' by a restart; "
                        "marked failed"
                    )
            await session.commit()

        if requeued or failed:
            logger.info(
                f"AI task crash recovery: requeued={requeued}, marked failed={failed}"
            )
        return requeued, failed

    async def start_background_processor(self) -> None:
        """Start the background task processor (with crash recovery)."""
        if self._processor_task and not self._processor_task.done():
            return

        await self.recover_orphaned_tasks()
        self._processor_task = asyncio.create_task(self._processor_loop())
        logger.info("AI task background processor started")

    async def stop_background_processor(self) -> None:
        """Stop the background task processor."""
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
            self._processor_task = None
            logger.info("AI task background processor stopped")

    async def _processor_loop(self) -> None:
        """Main processor loop."""
        while True:
            try:
                # Get next task from the priority queue (highest priority
                # first; FIFO within one priority level via the sequence).
                _, _, task_id = await _task_queue.get()

                # Wait if at max concurrent
                while len(self._running_tasks) >= self._max_concurrent:
                    await asyncio.sleep(0.5)

                # Start processing
                task = asyncio.create_task(self._process_task(task_id))
                self._running_tasks[task_id] = task

                # Clean up when done
                def cleanup(t_id, t_task):
                    def done_callback(fut):
                        if t_id in self._running_tasks:
                            del self._running_tasks[t_id]

                    t_task.add_done_callback(done_callback)

                cleanup(task_id, task)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in processor loop: {e}")
                await asyncio.sleep(1)


# Global instance
_ai_task_service: AITaskQueueService | None = None


def get_ai_task_service() -> AITaskQueueService:
    """Get or create AI task service singleton."""
    global _ai_task_service
    if _ai_task_service is None:
        from db.session import AsyncSessionLocal

        _ai_task_service = AITaskQueueService(AsyncSessionLocal)
    return _ai_task_service


async def start_ai_task_processor() -> None:
    """Start the AI task processor on app startup."""
    service = get_ai_task_service()
    await service.start_background_processor()


async def stop_ai_task_processor() -> None:
    """Stop the AI task processor on app shutdown."""
    if _ai_task_service:
        await _ai_task_service.stop_background_processor()
