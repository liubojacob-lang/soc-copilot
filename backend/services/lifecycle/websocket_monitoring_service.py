"""WebSocket monitoring lifecycle service.

Manages WebSocket monitoring and related services.
"""

from __future__ import annotations

from core.lifecycle import LifecycleService, ServicePriority
from core.logger import get_logger

logger = get_logger(__name__)


class WebSocketMonitoringService(LifecycleService):
    """WebSocket monitoring lifecycle service.

    This service handles:
    - WebSocket monitoring service startup
    - Message compression service
    - Message batch service
    - Connection pool service

    Priority: NORMAL
    """

    def __init__(self):
        self._monitoring = None

    @property
    def name(self) -> str:
        return "websocket_monitoring"

    @property
    def priority(self) -> ServicePriority:
        return ServicePriority.NORMAL

    async def start(self) -> None:
        """Start WebSocket monitoring and related services."""
        logger.info("Starting WebSocket monitoring services...")

        # Start monitoring service
        from services.observability.websocket_monitoring import (
            start_websocket_monitoring,
        )

        await start_websocket_monitoring()

        # Start compression service
        from services.websocket_compression import start_compression_service

        await start_compression_service()

        # Start batch service
        from services.message_batch_service import start_batch_service

        await start_batch_service()

        # Start connection pool
        from services.websocket_connection_pool import start_connection_pool

        await start_connection_pool()

        logger.info("WebSocket monitoring services started")

    async def stop(self) -> None:
        """Stop WebSocket monitoring services."""
        logger.info("Stopping WebSocket monitoring services...")

        try:
            from services.observability.websocket_monitoring import (
                get_websocket_monitoring,
            )

            monitoring = get_websocket_monitoring()
            if monitoring:
                await monitoring.stop()
        except Exception as e:
            logger.error(f"Error stopping WebSocket monitoring: {e}")

        logger.info("WebSocket monitoring services stopped")


class AlertEvaluatorService(LifecycleService):
    """Alert evaluator lifecycle service.

    This service handles the alert evaluation engine.

    Priority: NORMAL
    """

    @property
    def name(self) -> str:
        return "alert_evaluator"

    @property
    def priority(self) -> ServicePriority:
        return ServicePriority.NORMAL

    async def start(self) -> None:
        """Start the alert evaluator."""
        logger.info("Starting alert evaluator...")

        from services.alerting.alert_evaluator import start_alert_evaluator

        await start_alert_evaluator()

        logger.info("Alert evaluator started")

    async def stop(self) -> None:
        """Stop the alert evaluator."""
        logger.info("Stopping alert evaluator...")
        # Alert evaluator doesn't have explicit stop
        logger.info("Alert evaluator stopped")


class AuditArchiveService(LifecycleService):
    """Audit log archival lifecycle service.

    This service handles scheduled archival of old audit logs.

    Priority: OPTIONAL
    """

    def __init__(self):
        self._task = None

    @property
    def name(self) -> str:
        return "audit_archive"

    @property
    def priority(self) -> ServicePriority:
        return ServicePriority.OPTIONAL

    async def start(self) -> None:
        """Start the audit archive service."""
        from core.config import settings

        if not settings.audit_log_cleanup_enabled:
            logger.info("Audit log cleanup is disabled")
            return

        logger.info("Starting audit archive service...")

        import asyncio

        from db.session import AsyncSessionLocal
        from services.audit_archive_service import run_scheduled_archival

        self._task = asyncio.create_task(run_scheduled_archival(AsyncSessionLocal))

        logger.info("Audit archive service started")

    async def stop(self) -> None:
        """Stop the audit archive service."""
        if self._task:
            logger.info("Stopping audit archive service...")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Audit archive service stopped")


import asyncio
