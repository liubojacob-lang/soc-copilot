"""
Wazuh Alert Streaming Service

Handles real-time broadcasting of Wazuh alerts via WebSocket.
Supports filtering, aggregation, and intelligent alert routing.
"""

import asyncio
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from routers.websocket import get_manager, push_alert
from schemas.alert_stream import (
    AlertAggregation,
    AlertStreamFilter,
    AlertStreamStats,
    SeverityLevel,
    WazuhAlertStream,
    WazuhStreamMessage,
)

logger = logging.getLogger(__name__)


@dataclass
class AlertBufferEntry:
    """Entry in the alert buffer for aggregation."""

    alert: WazuhAlertStream
    count: int = 1
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)


class WazuhStreamService:
    """
    Service for streaming Wazuh alerts in real-time.

    Features:
    - Real-time alert broadcasting via WebSocket
    - Alert deduplication and aggregation
    - Per-client filtering
    - Stream statistics
    """

    def __init__(
        self,
        aggregation_window_seconds: int = 10,  # Reduced from 60 for faster testing
        max_buffer_size: int = 10000,
        max_history_size: int = 1000,
    ):
        """
        Initialize the stream service.

        Args:
            aggregation_window_seconds: Time window for alert aggregation
            max_buffer_size: Maximum alerts in aggregation buffer
            max_history_size: Maximum alerts in history cache
        """
        self.aggregation_window = timedelta(seconds=aggregation_window_seconds)
        self.max_buffer_size = max_buffer_size
        self.max_history_size = max_history_size

        # Alert aggregation buffer: {aggregation_key: AlertBufferEntry}
        self._aggregation_buffer: dict[str, AlertBufferEntry] = {}
        self._buffer_lock = asyncio.Lock()

        # Alert history (recent alerts for new subscribers)
        self._alert_history: deque = deque(maxlen=max_history_size)

        # Stream statistics
        self._stats = {
            "total_alerts": 0,
            "alerts_by_severity": defaultdict(int),
            "alerts_by_event_type": defaultdict(int),
            "alerts_by_agent": defaultdict(int),
            "alerts_by_source_ip": defaultdict(int),
            "stream_start_time": datetime.now(UTC),
            "last_alert_time": None,
        }
        self._stats_lock = asyncio.Lock()

        # Client subscriptions: {client_id: AlertStreamFilter}
        self._subscriptions: dict[str, AlertStreamFilter] = {}

        # Service state
        self._running = False
        self._aggregation_task: asyncio.Task | None = None
        self._cleanup_task: asyncio.Task | None = None

    async def start(self):
        """Start the stream service background tasks."""
        if self._running:
            return

        self._running = True
        logger.info("Starting Wazuh alert stream service")

        # Start aggregation processing task
        self._aggregation_task = asyncio.create_task(self._process_aggregations())

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_old_data())

    async def stop(self):
        """Stop the stream service."""
        self._running = False

        if self._aggregation_task:
            self._aggregation_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()

        logger.info("Stopped Wazuh alert stream service")

    async def stream_alert(self, alert: WazuhAlertStream) -> bool:
        """
        Stream an alert to all subscribed clients.

        Args:
            alert: The alert to stream

        Returns:
            True if alert was successfully queued for streaming
        """
        try:
            # Update statistics
            await self._update_stats(alert)

            # Add to history
            self._alert_history.append(alert)

            # Check aggregation
            aggregated = await self._try_aggregate(alert)

            if not aggregated:
                # Stream immediately if not aggregated
                await self._broadcast_alert(alert)

            logger.debug(f"Streamed alert: {alert.id} - {alert.title}")
            return True

        except Exception as e:
            logger.error(f"Error streaming alert {alert.id}: {e}")
            return False

    def _matches_filter(self, alert: WazuhAlertStream, filters: AlertStreamFilter) -> bool:
        if filters.min_severity:
            if self._severity_order(alert.severity) > self._severity_order(filters.min_severity):
                return False
        if filters.agent_ids and alert.agent.id not in filters.agent_ids:
            return False
        if filters.event_types and alert.event_type not in filters.event_types:
            return False
        if filters.source_ips and alert.source_ip not in filters.source_ips:
            return False
        if filters.has_mitre and not alert.mitre:
            return False
        return True

    async def _broadcast_alert(self, alert: WazuhAlertStream):
        alert_data = alert.model_dump(mode="json")

        message = WazuhStreamMessage(
            type="alert",
            data=alert_data,
            timestamp=datetime.now(UTC),
            channel="wazuh",
        )

        if not self._subscriptions:
            await push_alert(alert_data)
        else:
            for client_id, filters in list(self._subscriptions.items()):
                if self._matches_filter(alert, filters):
                    try:
                        manager = get_manager()
                        ws = next(
                            (
                                ws
                                for ws, info in manager.active_connections.items()
                                if info.get("user_id") == client_id
                            ),
                            None,
                        )
                        if ws:
                            await ws.send_json(message.model_dump(mode="json"))
                    except Exception as e:
                        logger.warning(f"Failed to send filtered alert to {client_id}: {e}")

    async def _try_aggregate(self, alert: WazuhAlertStream) -> bool:
        """
        Try to aggregate the alert with existing alerts.

        Returns:
            True if alert was aggregated (don't stream immediately)
        """
        # Generate aggregation key
        key = self._generate_aggregation_key(alert)

        async with self._buffer_lock:
            now = datetime.now(UTC)

            if key in self._aggregation_buffer:
                # Add to existing aggregation
                entry = self._aggregation_buffer[key]
                entry.count += 1
                entry.last_seen = now

                # Update severity if higher
                if self._severity_order(alert.severity) < self._severity_order(
                    entry.alert.severity
                ):
                    entry.alert.severity = alert.severity

                logger.debug(f"Aggregated alert {alert.id} into {key}")
                return True
            else:
                # Create new aggregation entry
                entry = AlertBufferEntry(alert=alert, count=1, first_seen=now, last_seen=now)
                self._aggregation_buffer[key] = entry

                # Prune buffer if too large
                if len(self._aggregation_buffer) > self.max_buffer_size:
                    self._prune_buffer()

                return False

    def _generate_aggregation_key(self, alert: WazuhAlertStream) -> str:
        """
        Generate aggregation key for an alert.

        Alerts are aggregated if they have the same:
        - Agent ID
        - Event type
        - Source IP (if present)
        - Rule ID (if present)
        """
        parts = [
            alert.agent.id,
            alert.event_type,
            alert.source_ip or "no-src-ip",
            str(
                alert.rule.get("id", "no-rule")
                if isinstance(alert.rule, dict)
                else getattr(alert.rule, "id", "no-rule")
            )
            if alert.rule
            else "no-rule",
        ]
        return "|".join(parts)

    def _severity_order(self, severity: SeverityLevel) -> int:
        """Get numeric order for severity (lower = more severe)."""
        order = {
            SeverityLevel.CRITICAL: 0,
            SeverityLevel.HIGH: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.LOW: 3,
            SeverityLevel.INFO: 4,
        }
        return order.get(severity, 99)

    def _prune_buffer(self):
        """Prune oldest entries from aggregation buffer."""
        # Remove oldest entries based on last_seen time
        sorted_entries = sorted(self._aggregation_buffer.items(), key=lambda x: x[1].last_seen)

        # Remove 10% of buffer
        to_remove = int(len(sorted_entries) * 0.1)
        for key, _ in sorted_entries[:to_remove]:
            del self._aggregation_buffer[key]

        logger.info(f"Pruned {to_remove} entries from aggregation buffer")

    async def _process_aggregations(self):
        """Background task to process aggregated alerts."""
        while self._running:
            try:
                await asyncio.sleep(self.aggregation_window.seconds / 2)  # Check twice per window

                async with self._buffer_lock:
                    now = datetime.now(UTC)
                    to_stream = []

                    # Find aggregations ready to stream
                    for key, entry in list(self._aggregation_buffer.items()):
                        age = now - entry.last_seen
                        if age >= self.aggregation_window:
                            to_stream.append((key, entry))
                            del self._aggregation_buffer[key]

                    # Stream aggregated alerts
                    for key, entry in to_stream:
                        await self._stream_aggregated_alert(key, entry)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in aggregation processing: {e}")

    async def _stream_aggregated_alert(self, key: str, entry: AlertBufferEntry):
        aggregation = AlertAggregation(
            aggregation_key=key,
            alert_count=entry.count,
            first_seen=entry.first_seen,
            last_seen=entry.last_seen,
            severity=entry.alert.severity,
            sample_alert=entry.alert,
            iocs=entry.alert.iocs,
        )

        aggregation_data = aggregation.model_dump(mode="json")
        message = WebSocketMessage(
            type="aggregated_alert",
            data=aggregation_data,
            timestamp=datetime.now(UTC).isoformat(),
            channel="alerts",
        )

        manager = get_manager()

        if not self._subscriptions:
            await manager.broadcast_to_channel("alerts", message)
        else:
            for client_id, filters in list(self._subscriptions.items()):
                if self._matches_filter(entry.alert, filters):
                    try:
                        ws = next(
                            (
                                ws
                                for ws, info in manager.active_connections.items()
                                if info.get("user_id") == client_id
                            ),
                            None,
                        )
                        if ws:
                            await ws.send_json(message.model_dump(mode="json"))
                    except Exception as e:
                        logger.warning(f"Failed to send aggregated alert to {client_id}: {e}")

    async def _cleanup_old_data(self):
        """Background task to clean up old data."""
        while self._running:
            try:
                await asyncio.sleep(3600)  # Run every hour

                # Clean old statistics data (keep last 24 hours)
                cutoff = datetime.now(UTC) - timedelta(hours=24)

                async with self._stats_lock:
                    # Reset counters if needed
                    if (datetime.now(UTC) - self._stats["stream_start_time"]) > timedelta(hours=24):
                        self._stats["stream_start_time"] = datetime.now(UTC)
                        self._stats["total_alerts"] = 0
                        self._stats["alerts_by_severity"].clear()
                        self._stats["alerts_by_event_type"].clear()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")

    async def _update_stats(self, alert: WazuhAlertStream):
        """Update stream statistics."""
        async with self._stats_lock:
            self._stats["total_alerts"] += 1
            self._stats["alerts_by_severity"][alert.severity.value] += 1
            self._stats["alerts_by_event_type"][alert.event_type] += 1
            self._stats["alerts_by_agent"][alert.agent.name] += 1
            if alert.source_ip:
                self._stats["alerts_by_source_ip"][alert.source_ip] += 1
            self._stats["last_alert_time"] = datetime.now(UTC)

    def get_stats(self) -> AlertStreamStats:
        """Get current stream statistics."""
        # Convert stats to response format
        alerts_by_severity = dict(self._stats["alerts_by_severity"])
        alerts_by_event_type = dict(self._stats["alerts_by_event_type"])

        # Get top agents
        top_agents = [
            {"name": k, "count": v}
            for k, v in sorted(
                self._stats["alerts_by_agent"].items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

        # Get top source IPs
        top_source_ips = [
            {"ip": k, "count": v}
            for k, v in sorted(
                self._stats["alerts_by_source_ip"].items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]
        ]

        return AlertStreamStats(
            total_alerts=self._stats["total_alerts"],
            alerts_by_severity=alerts_by_severity,
            alerts_by_event_type=alerts_by_event_type,
            top_agents=top_agents,
            top_source_ips=top_source_ips,
            stream_start_time=self._stats["stream_start_time"],
            last_alert_time=self._stats["last_alert_time"],
        )

    def get_recent_alerts(self, limit: int = 50) -> list[WazuhAlertStream]:
        """Get recent alerts from history."""
        return list(self._alert_history)[-limit:]

    def subscribe(self, client_id: str, filters: AlertStreamFilter):
        """Subscribe a client with specific filters."""
        self._subscriptions[client_id] = filters
        logger.info(f"Client {client_id} subscribed with filters: {filters}")

    def unsubscribe(self, client_id: str):
        """Unsubscribe a client."""
        if client_id in self._subscriptions:
            del self._subscriptions[client_id]
            logger.info(f"Client {client_id} unsubscribed")

    def get_subscription(self, client_id: str) -> AlertStreamFilter | None:
        """Get client subscription filters."""
        return self._subscriptions.get(client_id)


# Global stream service instance
_stream_service: WazuhStreamService | None = None


def get_wazuh_stream_service() -> WazuhStreamService:
    """Get the global Wazuh stream service instance."""
    global _stream_service
    if _stream_service is None:
        _stream_service = WazuhStreamService()
    return _stream_service


async def init_wazuh_stream_service(
    aggregation_window_seconds: int = 10,  # Reduced from 60 for faster testing
    max_buffer_size: int = 10000,
    max_history_size: int = 1000,
) -> WazuhStreamService:
    """Initialize and start the global Wazuh stream service."""
    global _stream_service
    _stream_service = WazuhStreamService(
        aggregation_window_seconds=aggregation_window_seconds,
        max_buffer_size=max_buffer_size,
        max_history_size=max_history_size,
    )
    await _stream_service.start()
    return _stream_service
