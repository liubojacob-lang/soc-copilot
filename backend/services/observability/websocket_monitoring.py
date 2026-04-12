"""
WebSocket Monitoring Service

This service provides real-time monitoring and metrics collection for
WebSocket connections, messages, errors, and performance.

Features:
- Automatic metrics collection from WebSocket events
- Time-series storage in Redis
- Aggregated statistics calculation
- Health score computation
- Metrics query API
"""

import asyncio
import time
from datetime import datetime
from typing import Any

from core.logger import get_logger
from models.websocket_metrics import (
    AggregatedMetrics,
    ConnectionMetrics,
    ErrorMetrics,
    ErrorType,
    MessageMetrics,
    MetricsQuery,
    MetricsReport,
    MetricsSnapshot,
    PerformanceMetrics,
)

logger = get_logger(__name__)


class WebSocketMetricsCollector:
    """
    Collector for WebSocket metrics.

    Tracks metrics in memory and periodically persists to Redis.
    """

    def __init__(self):
        # Current metrics
        self.connection_metrics = ConnectionMetrics()
        self.message_metrics = MessageMetrics()
        self.error_metrics = ErrorMetrics()
        self.performance_metrics = PerformanceMetrics()

        # Active connections tracking: {connection_id: {"user_id": str, "connected_at": float}}
        self.active_connections: dict[str, dict[str, Any]] = {}

        # Connection start times for duration tracking
        self.connection_start_times: dict[str, float] = {}

        # Message rate tracking (last second)
        self._messages_sent_last_second: list[float] = []
        self._messages_received_last_second: list[float] = []

        # Background tasks
        self._collection_task: asyncio.Task | None = None
        self._persistence_task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """Start background collection tasks."""
        if self._running:
            return

        self._running = True

        # Start metrics collection task (every second)
        self._collection_task = asyncio.create_task(self._collect_metrics_loop())

        # Start persistence task (every minute)
        self._persistence_task = asyncio.create_task(self._persist_metrics_loop())

        logger.info("WebSocket metrics collector started")

    async def stop(self):
        """Stop background collection tasks."""
        if not self._running:
            return

        self._running = False

        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

        if self._persistence_task:
            self._persistence_task.cancel()
            try:
                await self._persistence_task
            except asyncio.CancelledError:
                pass

        logger.info("WebSocket metrics collector stopped")

    async def _collect_metrics_loop(self):
        """Periodic metrics collection (every second)."""
        while self._running:
            try:
                await self._calculate_rates()
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                await asyncio.sleep(1)

    async def _persist_metrics_loop(self):
        """Periodic metrics persistence (every minute)."""
        while self._running:
            try:
                await self._persist_snapshot()

                # Evaluate alert rules
                await self._evaluate_alerts()

                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics persistence loop: {e}")
                await asyncio.sleep(60)

    async def _calculate_rates(self):
        """Calculate current rates (per second)."""
        now = time.time()

        # Clean old message timestamps (older than 1 second)
        cutoff = now - 1.0
        self._messages_sent_last_second = [
            ts for ts in self._messages_sent_last_second if ts > cutoff
        ]
        self._messages_received_last_second = [
            ts for ts in self._messages_received_last_second if ts > cutoff
        ]

        # Update rates
        self.message_metrics.current_send_rate = len(self._messages_sent_last_second)
        self.message_metrics.current_receive_rate = len(
            self._messages_received_last_second
        )

    def record_connection_established(
        self, connection_id: str, user_id: str, user_role: str
    ) -> None:
        """Record a new connection."""
        now = time.time()

        # Track active connection
        self.active_connections[connection_id] = {
            "user_id": user_id,
            "user_role": user_role,
            "connected_at": now,
        }

        # Track start time for duration calculation
        self.connection_start_times[connection_id] = now

        # Update metrics
        self.connection_metrics.active_connections = len(self.active_connections)
        self.connection_metrics.increment_connection(user_id)

        logger.debug(f"Connection established: {connection_id} for user {user_id}")

    def record_connection_closed(
        self, connection_id: str, reason: str | None = None
    ) -> None:
        """Record a closed connection."""
        # Calculate connection duration
        start_time = self.connection_start_times.get(connection_id)
        if start_time:
            duration_seconds = time.time() - start_time
            self.connection_metrics.increment_disconnection(duration_seconds)
            del self.connection_start_times[connection_id]

        # Remove from active connections
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]

        # Update metrics
        self.connection_metrics.active_connections = len(self.active_connections)

        logger.debug(f"Connection closed: {connection_id} (reason: {reason})")

    def record_connection_failed(self, reason: str) -> None:
        """Record a failed connection attempt."""
        self.connection_metrics.increment_connection_failure()
        logger.debug(f"Connection failed: {reason}")

    def record_message_sent(
        self,
        connection_id: str,
        message_type: str,
        size_bytes: int,
        recipients: int = 1,
    ) -> None:
        """Record a sent message."""
        self.message_metrics.record_message_sent(message_type, size_bytes, recipients)
        self._messages_sent_last_second.append(time.time())

    def record_message_received(self, connection_id: str, message_type: str) -> None:
        """Record a received message."""
        self.message_metrics.record_message_received(message_type)
        self._messages_received_last_second.append(time.time())

    def record_message_filtered(self, user_id: str) -> None:
        """Record a filtered message."""
        self.message_metrics.record_message_filtered()

    def record_error(
        self,
        error_type: ErrorType,
        message: str,
        is_critical: bool = False,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record an error."""
        self.error_metrics.record_error(error_type, message, is_critical, context)

    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self.performance_metrics.record_latency(latency_ms)

    def get_aggregated_metrics(self) -> AggregatedMetrics:
        """Get current aggregated metrics."""
        aggregated = AggregatedMetrics(
            connection=self.connection_metrics,
            message=self.message_metrics,
            error=self.error_metrics,
            performance=self.performance_metrics,
        )

        # Calculate health score
        aggregated.calculate_health_score()

        return aggregated

    async def _persist_snapshot(self):
        """Persist metrics snapshot to Redis."""
        try:
            from core.redis_client import get_redis_client

            redis_client = get_redis_client()

            # Create snapshot
            snapshot = MetricsSnapshot(
                connection=self.connection_metrics,
                message=self.message_metrics,
                error=self.error_metrics,
                performance=self.performance_metrics,
            )

            # Store in Redis (time series)
            snapshot_key = f"ws:metrics:snapshot:{int(time.time())}"
            snapshot_data = snapshot.model_dump_json()

            # Store with TTL (7 days)
            await redis_client.set(snapshot_key, snapshot_data, ex=7 * 24 * 3600)

            # Add to time series index
            await redis_client.zadd("ws:metrics:timeline", {snapshot_key: time.time()})

            # Trim old snapshots (keep last 10000)
            await redis_client.zremrangebyrank("ws:metrics:timeline", 0, -10000)

            logger.debug("Metrics snapshot persisted to Redis")

        except Exception as e:
            logger.error(f"Failed to persist metrics snapshot: {e}")

    async def _evaluate_alerts(self):
        """Evaluate alert rules against current metrics."""
        try:
            from services.alerting.alert_evaluator import get_alert_evaluator

            evaluator = get_alert_evaluator()

            # Get current metrics
            metrics = self.get_aggregated_metrics()

            # Evaluate rules (evaluates all rules, filters by user internally)
            notifications = await evaluator.evaluate_metrics(metrics)

            if notifications:
                logger.info(
                    f"Evaluated alerts: {len(notifications)} notifications sent"
                )

        except Exception as e:
            logger.error(f"Failed to evaluate alert rules: {e}")


class WebSocketMonitoringService:
    """
    High-level service for WebSocket monitoring.

    Provides API for recording events and querying metrics.
    """

    def __init__(self):
        self.collector = WebSocketMetricsCollector()
        self._started = False

    async def start(self):
        """Start the monitoring service."""
        if not self._started:
            await self.collector.start()
            self._started = True
            logger.info("WebSocket monitoring service started")

    async def stop(self):
        """Stop the monitoring service."""
        if self._started:
            await self.collector.stop()
            self._started = False
            logger.info("WebSocket monitoring service stopped")

    # Connection tracking
    async def record_connection_established(
        self, connection_id: str, user_id: str, user_role: str
    ) -> None:
        """Record a new connection."""
        self.collector.record_connection_established(connection_id, user_id, user_role)

    async def record_connection_closed(
        self, connection_id: str, reason: str | None = None
    ) -> None:
        """Record a closed connection."""
        self.collector.record_connection_closed(connection_id, reason)

    async def record_connection_failed(self, reason: str) -> None:
        """Record a failed connection attempt."""
        self.collector.record_connection_failed(reason)

    # Message tracking
    async def record_message_sent(
        self,
        connection_id: str,
        message_type: str,
        size_bytes: int,
        recipients: int = 1,
    ) -> None:
        """Record a sent message."""
        self.collector.record_message_sent(
            connection_id, message_type, size_bytes, recipients
        )

    async def record_message_received(
        self, connection_id: str, message_type: str
    ) -> None:
        """Record a received message."""
        self.collector.record_message_received(connection_id, message_type)

    async def record_message_filtered(self, user_id: str) -> None:
        """Record a filtered message."""
        self.collector.record_message_filtered(user_id)

    # Error tracking
    async def record_error(
        self,
        error_type: ErrorType,
        message: str,
        is_critical: bool = False,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record an error."""
        self.collector.record_error(error_type, message, is_critical, context)

    # Performance tracking
    async def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self.collector.record_latency(latency_ms)

    # Metrics queries
    async def get_current_metrics(self) -> AggregatedMetrics:
        """Get current aggregated metrics."""
        return self.collector.get_aggregated_metrics()

    async def get_metrics_summary(self) -> dict[str, Any]:
        """Get metrics summary."""
        aggregated = await self.get_current_metrics()
        return aggregated.get_summary()

    async def get_health_score(self) -> float:
        """Get current health score."""
        aggregated = await self.get_current_metrics()
        return aggregated.health_score

    async def get_historical_metrics(
        self, query: MetricsQuery
    ) -> list[MetricsSnapshot]:
        """
        Get historical metrics snapshots.

        Args:
            query: Query parameters for filtering

        Returns:
            List of metrics snapshots
        """
        try:
            from core.redis_client import get_redis_client

            redis_client = get_redis_client()

            # Get snapshot keys from time series
            now = time.time()

            # Calculate time range
            if query.end_time:
                end_timestamp = datetime.fromisoformat(query.end_time).timestamp()
            else:
                end_timestamp = now

            if query.start_time:
                start_timestamp = datetime.fromisoformat(query.start_time).timestamp()
            else:
                start_timestamp = end_timestamp - 3600  # Default: last hour

            # Get snapshots from time series
            snapshots = await redis_client.zrangebyscore(
                "ws:metrics:timeline",
                start_timestamp,
                end_timestamp,
                start=query.offset,
                num=query.limit,
            )

            # Deserialize snapshots
            result = []
            for snapshot_key in snapshots:
                snapshot_data = await redis_client.get(snapshot_key)
                if snapshot_data:
                    snapshot = MetricsSnapshot.model_validate_json(snapshot_data)
                    result.append(snapshot)

            return result

        except Exception as e:
            logger.error(f"Failed to get historical metrics: {e}")
            return []

    async def generate_report(
        self, start_time: str | None = None, end_time: str | None = None
    ) -> MetricsReport:
        """
        Generate a metrics report.

        Args:
            start_time: Report start time (ISO format)
            end_time: Report end time (ISO format)

        Returns:
            Metrics report with summary and recommendations
        """
        import uuid

        # Get historical metrics
        query = MetricsQuery(start_time=start_time, end_time=end_time, limit=1000)

        snapshots = await self.get_historical_metrics(query)

        # Get current metrics
        current_metrics = await self.get_current_metrics()

        # Calculate summary
        summary = {
            "snapshot_count": len(snapshots),
            "time_range": {"start": start_time or "N/A", "end": end_time or "N/A"},
            "total_connections": current_metrics.connection.total_connections,
            "total_messages": current_metrics.message.total_messages_sent,
            "total_errors": current_metrics.error.total_errors,
            "avg_health_score": (
                sum(s.health_score for s in snapshots) / len(snapshots)
                if snapshots
                else current_metrics.health_score
            ),
        }

        # Generate recommendations
        recommendations = []

        if current_metrics.health_score < 70:
            recommendations.append(
                "Health score is below 70% - investigate errors and performance"
            )

        if current_metrics.error.total_errors > 100:
            recommendations.append(
                f"High error count ({current_metrics.error.total_errors}) - review error logs"
            )

        if current_metrics.performance.p95_latency_ms > 500:
            recommendations.append(
                f"High P95 latency ({current_metrics.performance.p95_latency_ms:.2f}ms) - investigate bottlenecks"
            )

        if current_metrics.connection.total_connection_failures > 10:
            recommendations.append(
                "Multiple connection failures - check network and authentication"
            )

        # Generate report
        report = MetricsReport(
            report_id=str(uuid.uuid4()),
            time_range=summary["time_range"],
            summary=summary,
            recommendations=recommendations,
            metrics=current_metrics,
        )

        return report


# Global instance
_monitoring_service: WebSocketMonitoringService | None = None


def get_websocket_monitoring() -> WebSocketMonitoringService:
    """Get or create the global WebSocket monitoring service instance."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = WebSocketMonitoringService()
    return _monitoring_service


async def start_websocket_monitoring():
    """Initialize and start the WebSocket monitoring service."""
    service = get_websocket_monitoring()
    await service.start()
    return service
