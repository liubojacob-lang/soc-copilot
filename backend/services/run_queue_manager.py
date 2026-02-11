"""Run Queue Manager for execution concurrency control (v0.7.4).

This service manages the execution queue for playbook runs, providing:
- Concurrency control (max concurrent runs)
- FIFO queue policy for pending runs
- Orphaned run recovery after server restart
- Queue status monitoring
"""

import asyncio
from typing import Optional
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.playbook_run import PlaybookRunModel
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


# Global queue manager instance
_queue_manager: Optional["RunQueueManager"] = None


class RunQueueManager:
    """Manager for playbook run execution queue.

    This service controls the number of concurrently running playbooks
    and queues excess requests for FIFO processing.
    """

    def __init__(self, session_factory):
        """Initialize the queue manager.

        Args:
            session_factory: AsyncSessionLocal factory for DB access
        """
        self.session_factory = session_factory
        self.max_concurrent = settings.run_queue_max
        self.policy = settings.run_queue_policy
        self._processing_task: Optional[asyncio.Task] = None

    async def recover_runs(self) -> int:
        """Recover orphaned runs from previous server session.

        Marks runs as failed if they were in 'running' state for more
        than 1 hour (likely interrupted by server restart).

        Returns:
            Number of orphaned runs recovered
        """
        async with self.session_factory() as session:
            # Find orphaned running runs (started > 1 hour ago with no finish time)
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            stmt = select(PlaybookRunModel).where(
                and_(
                    PlaybookRunModel.status == "running",
                    PlaybookRunModel.started_at < cutoff,
                    PlaybookRunModel.finished_at.is_(None)
                )
            )
            result = await session.execute(stmt)
            orphaned = result.scalars().all()

            for run in orphaned:
                run.status = "failed"
                run.error_message = "Run interrupted by server restart"
                run.finished_at = datetime.now(timezone.utc)

            await session.commit()

            if orphaned:
                logger.warning(f"Recovered {len(orphaned)} orphaned runs from previous session")

            return len(orphaned)

    async def can_start_run(self) -> bool:
        """Check if a new run can be started immediately.

        Returns:
            True if concurrent limit not reached, False otherwise
        """
        async with self.session_factory() as session:
            stmt = select(func.count(PlaybookRunModel.id)).where(
                PlaybookRunModel.status == "running"
            )
            result = await session.execute(stmt)
            running_count = result.scalar() or 0

            has_capacity = running_count < self.max_concurrent

            if not has_capacity:
                logger.info(
                    f"Queue at capacity: {running_count}/{self.max_concurrent} running"
                )

            return has_capacity

    async def get_queue_stats(self) -> dict:
        """Get current queue statistics.

        Returns:
            Dictionary with running and queued counts
        """
        async with self.session_factory() as session:
            # Count running runs
            running_stmt = select(func.count(PlaybookRunModel.id)).where(
                PlaybookRunModel.status == "running"
            )
            running_result = await session.execute(running_stmt)
            running_count = running_result.scalar() or 0

            # Count queued runs
            queued_stmt = select(func.count(PlaybookRunModel.id)).where(
                PlaybookRunModel.status == "queued"
            )
            queued_result = await session.execute(queued_stmt)
            queued_count = queued_result.scalar() or 0

            return {
                "running": running_count,
                "queued": queued_count,
                "max_concurrent": self.max_concurrent,
                "has_capacity": running_count < self.max_concurrent,
            }

    async def process_queue(self) -> Optional[str]:
        """Process the queue and start the next pending run if capacity available.

        Returns:
            Run ID of started run, or None if queue is empty or at capacity
        """
        if not await self.can_start_run():
            return None

        async with self.session_factory() as session:
            # Get oldest queued run (FIFO)
            stmt = select(PlaybookRunModel).where(
                PlaybookRunModel.status == "queued"
            ).order_by(
                PlaybookRunModel.queued_at
            ).limit(1)

            result = await session.execute(stmt)
            queued_run = result.scalar_one_or_none()

            if not queued_run:
                return None

            # Update status to running
            queued_run.status = "running"
            queued_run.started_at = datetime.now(timezone.utc)

            await session.commit()

            logger.info(
                f"Started queued run {queued_run.id} "
                f"(playbook: {queued_run.playbook_name})"
            )

            # Trigger execution of the run
            # This will be handled by the caller
            return queued_run.id

    async def queue_run(self, run_id: str) -> None:
        """Add a run to the queue.

        Args:
            run_id: ID of the run to queue
        """
        async with self.session_factory() as session:
            stmt = select(PlaybookRunModel).where(
                PlaybookRunModel.id == run_id
            )
            result = await session.execute(stmt)
            run = result.scalar_one_or_none()

            if run:
                run.status = "queued"
                run.queued_at = datetime.now(timezone.utc)
                await session.commit()

                logger.info(f"Queued run {run_id} (playbook: {run.playbook_name})")

    async def start_background_processor(self) -> None:
        """Start background task to process queue continuously."""
        if self._processing_task is not None:
            return  # Already running

        async def process_loop():
            while True:
                try:
                    await self.process_queue()
                except Exception as e:
                    logger.error(f"Error processing queue: {e}")

                await asyncio.sleep(5)  # Check every 5 seconds

        self._processing_task = asyncio.create_task(process_loop())
        logger.info("Started queue processor background task")

    async def stop_background_processor(self) -> None:
        """Stop background queue processor."""
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            logger.info("Stopped queue processor background task")


# Global singleton functions
def set_run_queue_manager(manager: RunQueueManager) -> None:
    """Set the global queue manager instance."""
    global _queue_manager
    _queue_manager = manager


def get_run_queue_manager() -> Optional[RunQueueManager]:
    """Get the global queue manager instance."""
    return _queue_manager
