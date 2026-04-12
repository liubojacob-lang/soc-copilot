"""AI Task Queue Manager for asynchronous AI operations.

Moves AI calls from synchronous to background tasks to prevent blocking.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from models.ai_task import AITaskModel, AITaskStatus

logger = get_logger(__name__)


class AIQueueManager:
    """Manager for AI task queue and execution."""

    def __init__(self, max_concurrent: int = 3):
        """Initialize the AI queue manager.

        Args:
            max_concurrent: Maximum number of concurrent AI tasks
        """
        self.max_concurrent = max_concurrent
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._queue: list[dict[str, Any]] = []
        self._task_history: dict[str, dict[str, Any]] = {}

    async def create_task(
        self,
        task_type: str,
        input_data: dict[str, Any],
        session: AsyncSession,
        priority: int = 0,
        user_id: str | None = None,
        model_id: str | None = None,
        provider: str | None = None,
    ) -> str:
        """Create a new AI task and queue it for execution.

        Args:
            task_type: Type of AI task (e.g., "analyze_alert", "chat")
            input_data: Input data for the task
            session: Database session
            priority: Task priority (0=low, 1=normal, 2=high)
            user_id: Optional user ID
            model_id: Optional AI model ID
            provider: Optional AI provider

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())

        # Map task type to existing enum
        task_type_mapping = {
            "analyze_alert": "alert_analysis",
            "chat": "chat_completion",
            "recommend_playbook": "alert_analysis",
        }
        db_task_type = task_type_mapping.get(task_type, task_type)

        # Create task record with matching field names
        task = AITaskModel(
            id=task_id,
            task_type=db_task_type,
            status=AITaskStatus.PENDING.value,
            input_data=input_data,
            priority=priority,
            user_id=user_id,
            model_id=model_id,
            provider=provider,
        )

        session.add(task)
        await session.commit()

        logger.info(f"Created AI task {task_id} of type {task_type}")

        # Queue for execution
        await self._queue_task(task_id, task_type, input_data, priority)

        return task_id

    async def _queue_task(
        self, task_id: str, task_type: str, input_data: dict[str, Any], priority: int
    ):
        """Queue task for execution."""
        task_data = {
            "task_id": task_id,
            "task_type": task_type,
            "input_data": input_data,
            "priority": priority,
        }

        # Insert based on priority (higher priority first)
        inserted = False
        for i, queued in enumerate(self._queue):
            if queued["priority"] < priority:
                self._queue.insert(i, task_data)
                inserted = True
                break

        if not inserted:
            self._queue.append(task_data)

        logger.info(f"Queued AI task {task_id} with priority {priority}")

        # Try to execute immediately if capacity available
        asyncio.create_task(self._process_queue())

    async def get_task_status(
        self, task_id: str, session: AsyncSession
    ) -> dict[str, Any] | None:
        """Get current status of a task.

        Args:
            task_id: Task ID
            session: Database session

        Returns:
            Task status dict or None
        """
        from sqlalchemy import select

        stmt = select(AITaskModel).where(AITaskModel.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            return None

        # Include running tasks info
        is_running = task_id in self._running_tasks

        return {
            "task_id": task_id,
            "status": task.status,
            "task_type": task.task_type,
            "input_data": task.input_data,
            "result": task.result,
            "error_message": task.error_message,
            "priority": task.priority,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": (
                task.completed_at.isoformat() if task.completed_at else None
            ),
            "is_running": is_running,
            "user_id": task.user_id,
            "retry_count": task.retry_count,
        }

    async def cancel_task(self, task_id: str, session: AsyncSession) -> bool:
        """Cancel a pending or queued task.

        Args:
            task_id: Task ID
            session: Database session

        Returns:
            True if cancelled, False otherwise
        """
        from sqlalchemy import select

        stmt = select(AITaskModel).where(
            AITaskModel.id == task_id,
            AITaskModel.status.in_(
                [AITaskStatus.PENDING.value, AITaskStatus.PROCESSING.value]
            ),
        )
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if task:
            task.status = AITaskStatus.FAILED.value
            task.error_message = "Task cancelled by user"
            task.completed_at = datetime.now()
            session.add(task)
            await session.commit()

            # Remove from queue
            self._queue = [t for t in self._queue if t["task_id"] != task_id]

            logger.info(f"Cancelled AI task {task_id}")
            return True

        return False

    async def get_queue_stats(self) -> dict[str, int]:
        """Get current queue statistics.

        Returns:
            Dictionary with queue stats
        """
        return {
            "running": len(self._running_tasks),
            "queued": len(self._queue),
            "max_concurrent": self.max_concurrent,
            "available": self.max_concurrent - len(self._running_tasks),
        }

    async def _process_queue(self):
        """Process queued tasks."""
        while self._queue:
            # Wait for capacity
            if len(self._running_tasks) >= self.max_concurrent:
                logger.info(
                    f"Queue full: {len(self._running_tasks)}/{self.max_concurrent}"
                )
                await asyncio.sleep(1)
                continue

            # Get next task (highest priority first)
            task_data = self._queue.pop(0)

            # Execute in background
            asyncio.create_task(self._execute_task(task_data))

    async def _execute_task(self, task_data: dict[str, Any]):
        """Execute a single AI task.

        Args:
            task_data: Task data dict
        """
        task_id = task_data["task_id"]
        task_type = task_data["task_type"]
        input_data = task_data["input_data"]

        logger.info(f"Executing AI task {task_id} of type {task_type}")

        # Track running task
        self._running_tasks[task_id] = asyncio.current_task()

        # Mark as running
        async with get_session() as session:
            from sqlalchemy import select

            stmt = select(AITaskModel).where(AITaskModel.id == task_id)
            result = await session.execute(stmt)
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"Task {task_id} not found")
                return

            task.status = AITaskStatus.PROCESSING.value
            task.started_at = datetime.now()
            session.add(task)
            await session.commit()

        # Execute based on task type
        try:
            if task_type == "analyze_alert":
                result = await self._execute_analyze_alert(input_data)
            elif task_type == "chat":
                result = await self._execute_chat(input_data)
            elif task_type == "recommend_playbook":
                result = await self._execute_recommend_playbook(input_data)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            # Save result
            async with get_session() as session:
                from sqlalchemy import select

                stmt = select(AITaskModel).where(AITaskModel.id == task_id)
                result = await session.execute(stmt)
                task = result.scalar_one_or_none()

                if task:
                    task.status = AITaskStatus.COMPLETED.value
                    task.result = result
                    task.completed_at = datetime.now()
                    session.add(task)
                    await session.commit()

                    logger.info(f"AI task {task_id} completed successfully")

        except Exception as e:
            logger.error(f"AI task {task_id} failed: {e}", exc_info=True)

            # Save error
            async with get_session() as session:
                from sqlalchemy import select

                stmt = select(AITaskModel).where(AITaskModel.id == task_id)
                result = await session.execute(stmt)
                task = result.scalar_one_or_none()

                if task:
                    task.status = AITaskStatus.FAILED.value
                    task.error_message = str(e)
                    task.completed_at = datetime.now()
                    session.add(task)
                    await session.commit()

        finally:
            # Remove from running tasks
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]

    async def _execute_analyze_alert(
        self, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute alert analysis AI task."""
        from services.ai_service_enhanced import get_enhanced_ai_service

        ai_service = get_enhanced_ai_service()

        result = await ai_service.analyze_alert_with_rag(
            title=input_data.get("title", ""),
            description=input_data.get("description", ""),
            severity=input_data.get("severity", "medium"),
            source=input_data.get("source", "unknown"),
            alert_type=input_data.get("alert_type", "security"),
            use_rag=input_data.get("use_rag", True),
        )

        return result.dict()

    async def _execute_chat(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Execute AI chat task."""
        from services.ai_service_enhanced import get_enhanced_ai_service

        ai_service = get_enhanced_ai_service()

        message = input_data.get("message", "")
        conversation_history = input_data.get("conversation_history", [])

        result = await ai_service.chat_with_history(
            message=message, conversation_history=conversation_history
        )

        return {"response": result}

    async def _execute_recommend_playbook(
        self, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute playbook recommendation AI task."""
        from services.ai_service_enhanced import get_enhanced_ai_service

        ai_service = get_enhanced_ai_service()

        result = await ai_service.recommend_playbooks(
            alert_id=input_data.get("alert_id"),
            title=input_data.get("title", ""),
            description=input_data.get("description", ""),
            severity=input_data.get("severity", "medium"),
            alert_type=input_data.get("alert_type", "security"),
        )

        return {"recommendations": [r.dict() for r in result]}


# Global queue manager instance
_ai_queue_manager: AIQueueManager | None = None


def get_ai_queue_manager() -> AIQueueManager:
    """Get or create global AI queue manager."""
    global _ai_queue_manager

    if _ai_queue_manager is None:
        _ai_queue_manager = AIQueueManager(max_concurrent=3)

    return _ai_queue_manager
