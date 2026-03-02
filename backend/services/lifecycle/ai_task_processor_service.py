"""AI task processor lifecycle service.

Manages the AI background task processor.
"""

from __future__ import annotations

from core.lifecycle import LifecycleService, ServicePriority
from core.logger import get_logger

logger = get_logger(__name__)


class AITaskProcessorService(LifecycleService):
    """AI task processor lifecycle service.
    
    This service handles:
    - Starting the AI task background processor
    - Graceful shutdown of pending tasks
    
    Priority: NORMAL
    Dependencies: database
    """
    
    @property
    def name(self) -> str:
        return "ai_task_processor"
    
    @property
    def priority(self) -> ServicePriority:
        return ServicePriority.NORMAL
    
    @property
    def dependencies(self) -> list[str]:
        return ["database"]
    
    async def start(self) -> None:
        """Start the AI task processor.
        
        Initializes the background processor for AI tasks.
        """
        logger.info("Starting AI task processor...")
        
        from services.ai_task_service import start_ai_task_processor
        await start_ai_task_processor()
        
        logger.info("AI task processor started")
    
    async def stop(self) -> None:
        """Stop the AI task processor.
        
        Gracefully shuts down the processor, waiting for current tasks.
        """
        logger.info("Stopping AI task processor...")
        
        from services.ai_task_service import stop_ai_task_processor
        await stop_ai_task_processor()
        
        logger.info("AI task processor stopped")
