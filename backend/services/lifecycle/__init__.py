"""Lifecycle services package.

This package contains service implementations that follow the LifecycleService
pattern for structured startup and shutdown management.

Available services:
- DatabaseService: Database initialization and connection management
- QueueManagerService: Playbook run queue manager
- CronSchedulerServiceWrapper: Scheduled trigger management
- AITaskProcessorService: Background AI task processing
- RateLimiterService: API rate limiting
- WebSocketMonitoringService: WebSocket monitoring and related services
- AlertEvaluatorService: Alert evaluation engine
- AuditArchiveService: Audit log archival

Usage:
    from services.lifecycle import (
        get_lifecycle_manager,
        DatabaseService,
        QueueManagerService,
    )

    manager = get_lifecycle_manager()
    manager.register(DatabaseService())
    manager.register(QueueManagerService())
    await manager.start_all()
"""

from core.lifecycle import (
    LifecycleManager,
    LifecycleService,
    ServicePriority,
    ServiceState,
    get_lifecycle_manager,
    reset_lifecycle_manager,
)

from .ai_task_processor_service import AITaskProcessorService
from .alert_pipeline_service import AlertPipelineService
from .cron_scheduler_service import CronSchedulerServiceWrapper
from .data_retention_service import DataRetentionService
from .database_service import DatabaseService
from .queue_manager_service import QueueManagerService
from .rate_limiter_service import RateLimiterService
from .websocket_monitoring_service import (
    AlertEvaluatorService,
    AuditArchiveService,
    WebSocketMonitoringService,
)

__all__ = [
    # Core lifecycle components
    "LifecycleService",
    "LifecycleManager",
    "ServicePriority",
    "ServiceState",
    "get_lifecycle_manager",
    "reset_lifecycle_manager",
    # Service implementations
    "DatabaseService",
    "QueueManagerService",
    "CronSchedulerServiceWrapper",
    "AITaskProcessorService",
    "AlertPipelineService",
    "DataRetentionService",
    "RateLimiterService",
    "WebSocketMonitoringService",
    "AlertEvaluatorService",
    "AuditArchiveService",
]
