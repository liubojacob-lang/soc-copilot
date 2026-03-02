"""Queue manager lifecycle service.

Manages the playbook run queue manager startup and shutdown.
"""

from __future__ import annotations

from typing import Optional

from core.lifecycle import LifecycleService, ServicePriority
from core.config import settings
from core.logger import get_logger
from db.session import AsyncSessionLocal
from services.run_queue_manager import RunQueueManager, set_run_queue_manager

logger = get_logger(__name__)


class QueueManagerService(LifecycleService):
    """Run queue manager lifecycle service.
    
    This service handles:
    - Queue manager initialization and recovery
    - Background processor startup
    - Graceful shutdown of running queues
    
    Priority: ESSENTIAL (starts after database)
    Dependencies: database
    """
    
    def __init__(self):
        self._manager: Optional[RunQueueManager] = None
    
    @property
    def name(self) -> str:
        return "queue_manager"
    
    @property
    def priority(self) -> ServicePriority:
        return ServicePriority.ESSENTIAL
    
    @property
    def dependencies(self) -> list[str]:
        return ["database"]
    
    async def start(self) -> None:
        """Initialize and start the queue manager.
        
        - Creates queue manager instance
        - Recovers any incomplete runs from previous session
        - Starts the background processor
        """
        logger.info("Initializing run queue manager...")
        
        self._manager = RunQueueManager(AsyncSessionLocal)
        set_run_queue_manager(self._manager)
        
        # Recover incomplete runs from previous session
        await self._manager.recover_runs()
        logger.info(f"Recovered incomplete runs")
        
        # Start background processor
        await self._manager.start_background_processor()
        
        logger.info(
            f"Queue manager started "
            f"(max_concurrent={settings.run_queue_max}, "
            f"policy={settings.run_queue_policy})"
        )
    
    async def stop(self) -> None:
        """Stop the queue manager.
        
        Stops the background processor gracefully.
        """
        if self._manager:
            logger.info("Stopping queue manager...")
            await self._manager.stop_background_processor()
            logger.info("Queue manager stopped")
    
    async def health_check(self) -> bool:
        """Check if queue manager is operational.
        
        Returns:
            True if manager is running, False otherwise
        """
        if self._manager is None:
            return False
        
        try:
            # Check if processor is running
            return self._manager._running
        except Exception:
            return False
