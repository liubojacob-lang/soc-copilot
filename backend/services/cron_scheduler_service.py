"""Cron scheduler service for automated playbook execution."""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger

logger = get_logger(__name__)


class CronSchedulerService:
    """Background service for scheduling and executing cron triggers."""

    def __init__(self, session_factory) -> None:
        """Initialize the cron scheduler.

        Args:
            session_factory: Factory function to create new database sessions
        """
        self.session_factory = session_factory
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._pending_triggers: Set[str] = set()  # Prevent duplicate executions
        self._check_interval = 30  # seconds

    async def start(self) -> None:
        """Start the cron scheduler background task."""
        if self._running:
            logger.warning("Cron scheduler is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Cron scheduler started")

    async def stop(self) -> None:
        """Stop the cron scheduler background task."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Cron scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop that checks for due cron triggers."""
        logger.info("Cron scheduler loop started")

        while self._running:
            try:
                await self._check_and_execute_triggers()
            except Exception as e:
                logger.error(f"Error in cron scheduler loop: {e}")

            # Wait before next check
            await asyncio.sleep(self._check_interval)

        logger.info("Cron scheduler loop ended")

    async def _check_and_execute_triggers(self) -> None:
        """Check all cron triggers and execute those that are due."""
        from repositories.trigger_repository import TriggerRepository
        from services.trigger_service import TriggerService
        from croniter import croniter

        async with self.session_factory() as session:
            trigger_repo = TriggerRepository(session)
            trigger_service = TriggerService(session)

            # Get all active cron triggers
            triggers = await trigger_repo.get_active_cron_triggers()

            now = datetime.now(timezone.utc)
            executed_count = 0
            skipped_count = 0

            for trigger in triggers:
                if not trigger.cron_expr:
                    continue

                # Skip if already in pending set (prevents duplicate execution)
                if trigger.id in self._pending_triggers:
                    skipped_count += 1
                    continue

                try:
                    # Check if trigger is due
                    should_run = False
                    if trigger.last_triggered_at:
                        # Has run before - check if next execution time has passed
                        cron = croniter(trigger.cron_expr, trigger.last_triggered_at)
                        next_run = cron.get_next(datetime)
                        should_run = next_run <= now
                    else:
                        # Never run before - check if schedule matches current time
                        cron = croniter(trigger.cron_expr, now)
                        prev_run = cron.get_prev(datetime)
                        # If previous scheduled execution was within the last check interval, run it
                        should_run = (now - prev_run).total_seconds() < self._check_interval * 2

                    if should_run:
                        # Add to pending set to prevent duplicate execution
                        self._pending_triggers.add(trigger.id)

                        # Execute the trigger (fire and forget within transaction)
                        run_id = await trigger_service.execute_cron_trigger(trigger.id)

                        if run_id:
                            executed_count += 1
                            logger.info(
                                f"Executed cron trigger {trigger.id} "
                                f"({trigger.name}) -> run {run_id}"
                            )
                        else:
                            logger.warning(f"Cron trigger {trigger.id} execution returned None")

                        # Remove from pending set after a short delay
                        asyncio.create_task(self._remove_from_pending(trigger.id))

                except Exception as e:
                    logger.error(f"Error executing cron trigger {trigger.id}: {e}")
                    # Remove from pending set on error
                    self._pending_triggers.discard(trigger.id)

            if executed_count > 0 or skipped_count > 0:
                logger.debug(
                    f"Cron scheduler check: executed={executed_count}, "
                    f"skipped={skipped_count}, total={len(triggers)}"
                )

    async def _remove_from_pending(self, trigger_id: str) -> None:
        """Remove trigger from pending set after a delay."""
        await asyncio.sleep(60)  # Wait 60 seconds before allowing re-execution
        self._pending_triggers.discard(trigger_id)

    async def check_now(self) -> dict[str, int]:
        """Manually trigger a check for due cron triggers.

        Returns dict with executed and skipped counts.
        """
        from repositories.trigger_repository import TriggerRepository
        from services.trigger_service import TriggerService

        async with self.session_factory() as session:
            trigger_repo = TriggerRepository(session)
            trigger_service = TriggerService(session)

            triggers = await trigger_repo.get_active_cron_triggers()

            executed = 0
            for trigger in triggers:
                if trigger.id in self._pending_triggers:
                    continue

                self._pending_triggers.add(trigger.id)
                run_id = await trigger_service.execute_cron_trigger(trigger.id)

                if run_id:
                    executed += 1

                asyncio.create_task(self._remove_from_pending(trigger.id))

            return {"executed": executed, "total": len(triggers)}

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._running

    @property
    def pending_count(self) -> int:
        """Get the number of pending triggers."""
        return len(self._pending_triggers)


# Global instance singleton
_cron_scheduler: Optional[CronSchedulerService] = None


def get_cron_scheduler() -> Optional[CronSchedulerService]:
    """Get the global cron scheduler instance."""
    return _cron_scheduler


def set_cron_scheduler(scheduler: CronSchedulerService) -> None:
    """Set the global cron scheduler instance."""
    global _cron_scheduler
    _cron_scheduler = scheduler
