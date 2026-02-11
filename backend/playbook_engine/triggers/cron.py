"""Cron scheduler for time-based playbook triggers."""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Set
from croniter import croniter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.logger import get_logger
from models.playbook_definition import PlaybookTriggerModel, PlaybookDefinitionModel

logger = get_logger(__name__)


class CronScheduler:
    """Scheduler for cron-based playbook triggers."""

    def __init__(
        self,
        session_factory,
        check_interval: int = 30,
    ):
        """Initialize the cron scheduler.

        Args:
            session_factory: Async session factory for database access
            check_interval: Seconds between trigger checks (default: 30)
        """
        self.session_factory = session_factory
        self.check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._pending_triggers: Set[str] = set()

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
        """Main scheduler loop that checks for due triggers."""
        while self._running:
            try:
                await self._check_triggers()
            except Exception as e:
                logger.error(f"Error in cron scheduler loop: {e}")

            await asyncio.sleep(self.check_interval)

    async def _check_triggers(self) -> None:
        """Check for and execute due cron triggers."""
        async with self.session_factory() as session:
            # Get all active cron triggers
            stmt = select(PlaybookTriggerModel).where(
                PlaybookTriggerModel.type == "cron",
                PlaybookTriggerModel.is_active == True,
            )
            result = await session.execute(stmt)
            triggers = result.scalars().all()

            now = datetime.now(timezone.utc)

            for trigger in triggers:
                try:
                    cron_expr = trigger.config_json.get("cron_expression")
                    if not cron_expr:
                        logger.warning(f"Cron trigger {trigger.id} missing cron_expression")
                        continue

                    # Check if trigger is due
                    cron = croniter(cron_expr, now)
                    prev_run = cron.get_prev(datetime)

                    # Get last execution time
                    last_run = trigger.config_json.get("last_run")

                    # If this is a new run, execute it
                    if not last_run or prev_run > datetime.fromisoformat(last_run):
                        await self._execute_cron_trigger(session, trigger, now)

                except Exception as e:
                    logger.error(f"Error processing cron trigger {trigger.id}: {e}")

            await session.commit()

    async def _execute_cron_trigger(
        self,
        session: AsyncSession,
        trigger: PlaybookTriggerModel,
        now: datetime,
    ) -> None:
        """Execute a cron-triggered playbook.

        Args:
            session: Database session
            trigger: Trigger model
            now: Current time
        """
        trigger_id = trigger.id

        # Prevent duplicate executions
        if trigger_id in self._pending_triggers:
            logger.debug(f"Cron trigger {trigger_id} already pending, skipping")
            return

        self._pending_triggers.add(trigger_id)

        try:
            # Get playbook definition
            stmt = select(PlaybookDefinitionModel).where(
                PlaybookDefinitionModel.id == trigger.definition_id,
            )
            result = await session.execute(stmt)
            definition = result.scalar_one_or_none()

            if not definition:
                logger.error(f"Playbook definition not found: {trigger.definition_id}")
                return

            logger.info(f"Executing cron trigger {trigger_id} for playbook {definition.name}")

            # Execute the playbook
            from .dag import DAGBuilder, DAGExecutionEngine

            dag_definition = DAGBuilder.from_json(definition.definition_json)
            engine = DAGExecutionEngine(session)

            # Create run record
            from models.playbook_run import PlaybookRunModel
            from repositories.playbook_run_repository import PlaybookRunRepository
            import uuid

            run_repo = PlaybookRunRepository(session)
            run_id = str(uuid.uuid4())

            input_json = trigger.config_json.get("input_json", {})

            await run_repo.create(
                playbook_name=f"cron:{definition.name}",
                playbook_version=definition.version,
                mode="dry_run",
                status="running",
                created_by_user_id=None,
                input_json=input_json,
                output_json={},
                execution_mode="dag",
                definition_id=definition.id,
                trigger_source="cron",
            )

            await session.flush()

            # Execute the DAG
            result = await engine.execute_dag(
                definition=dag_definition,
                run_id=run_id,
                input_json=input_json,
                mode="dry_run",
            )

            logger.info(f"Cron trigger {trigger_id} completed with status: {result['status']}")

            # Update last run time
            trigger.config_json["last_run"] = now.isoformat()
            trigger.updated_at = now

        except Exception as e:
            logger.error(f"Error executing cron trigger {trigger_id}: {e}")
        finally:
            self._pending_triggers.discard(trigger_id)

    async def get_next_run_time(
        self,
        trigger_id: str,
    ) -> Optional[datetime]:
        """Get the next scheduled run time for a trigger.

        Args:
            trigger_id: Trigger ID

        Returns:
            Next run datetime or None if not found
        """
        async with self.session_factory() as session:
            stmt = select(PlaybookTriggerModel).where(
                PlaybookTriggerModel.id == trigger_id,
                PlaybookTriggerModel.type == "cron",
            )
            result = await session.execute(stmt)
            trigger = result.scalar_one_or_none()

            if not trigger:
                return None

            cron_expr = trigger.config_json.get("cron_expression")
            if not cron_expr:
                return None

            cron = croniter(cron_expr, datetime.now(timezone.utc))
            return cron.get_next(datetime)


# Global scheduler instance
_scheduler: Optional[CronScheduler] = None


def get_scheduler() -> Optional[CronScheduler]:
    """Get the global cron scheduler instance.

    Returns:
        Global CronScheduler instance or None
    """
    return _scheduler


def set_scheduler(scheduler: CronScheduler) -> None:
    """Set the global cron scheduler instance.

    Args:
        scheduler: Scheduler instance to set as global
    """
    global _scheduler
    _scheduler = scheduler
