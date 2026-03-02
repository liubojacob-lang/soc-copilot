"""Cron scheduler lifecycle service.

Manages the cron scheduler for scheduled playbook triggers.
"""

from __future__ import annotations

from typing import Optional

from core.lifecycle import LifecycleService, ServicePriority
from core.logger import get_logger
from db.session import AsyncSessionLocal
from services.cron_scheduler_service import CronSchedulerService, set_cron_scheduler

logger = get_logger(__name__)


class CronSchedulerServiceWrapper(LifecycleService):
    """Cron scheduler lifecycle service.
    
    This service handles:
    - Scheduler initialization
    - Starting scheduled jobs
    - Graceful shutdown
    
    Priority: ESSENTIAL (starts after database)
    Dependencies: database
    """
    
    def __init__(self):
        self._scheduler: Optional[CronSchedulerService] = None
    
    @property
    def name(self) -> str:
        return "cron_scheduler"
    
    @property
    def priority(self) -> ServicePriority:
        return ServicePriority.ESSENTIAL
    
    @property
    def dependencies(self) -> list[str]:
        return ["database"]
    
    async def start(self) -> None:
        """Initialize and start the cron scheduler.
        
        Creates scheduler instance and starts processing scheduled triggers.
        """
        logger.info("Initializing cron scheduler...")
        
        self._scheduler = CronSchedulerService(AsyncSessionLocal)
        set_cron_scheduler(self._scheduler)
        
        await self._scheduler.start()
        
        logger.info("Cron scheduler started")
    
    async def stop(self) -> None:
        """Stop the cron scheduler.
        
        Stops all scheduled jobs gracefully.
        """
        if self._scheduler:
            logger.info("Stopping cron scheduler...")
            await self._scheduler.stop()
            logger.info("Cron scheduler stopped")
    
    async def health_check(self) -> bool:
        """Check if scheduler is running.
        
        Returns:
            True if scheduler is active, False otherwise
        """
        if self._scheduler is None:
            return False
        
        try:
            return self._scheduler._running
        except Exception:
            return False
