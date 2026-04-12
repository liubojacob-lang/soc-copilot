"""AI Task Queue Service for background processing.

This service provides:
- Async task creation and submission
- Background task processing with timeout handling
- Status polling for long-running AI operations
- Automatic retry on transient failures
"""

import asyncio
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from core.logger import get_logger
from models.ai_task import AITaskModel, AITaskStatus, AITaskType
from services.llm_retry import get_llm_retry_service

logger = get_logger(__name__)

# Global task queue
_task_queue: asyncio.Queue = asyncio.Queue()
_background_processor: asyncio.Task | None = None


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
        await _task_queue.put((task_id, priority))
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
            # Process based on task type
            llm_service = get_llm_retry_service()

            if task.task_type in [
                AITaskType.ALERT_ANALYSIS.value,
                AITaskType.TIMELINE_ANALYSIS.value,
                AITaskType.IOC_ANALYSIS.value,
            ]:
                result = await asyncio.wait_for(
                    llm_service.generate_structured(
                        prompt=task.prompt,
                        response_class=dict,  # Will be handled by llm_retry
                    ),
                    timeout=task.timeout_seconds,
                )
            else:
                # Generic chat completion
                result = await asyncio.wait_for(
                    llm_service.ai_service.generate(task.prompt),
                    timeout=task.timeout_seconds,
                )

            # Update with result
            async with self.session_factory() as session:
                stmt = select(AITaskModel).where(AITaskModel.id == task_id)
                result_db = await session.execute(stmt)
                task = result_db.scalar_one_or_none()

                if task:
                    task.status = AITaskStatus.COMPLETED.value
                    task.result = (
                        result if isinstance(result, dict) else {"content": result}
                    )
                    task.completed_at = datetime.now(UTC)
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
                await _task_queue.put((task_id, task.priority))
                logger.info(
                    f"Retrying AI task {task_id} (attempt {task.retry_count}/{task.max_retries})"
                )

    async def start_background_processor(self) -> None:
        """Start the background task processor."""
        if self._processor_task and not self._processor_task.done():
            return

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
                # Get next task from queue
                task_id, priority = await _task_queue.get()

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
