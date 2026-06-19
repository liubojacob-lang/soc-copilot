"""
WebSocket Monitoring Metrics Data Models

This module defines data models for collecting and tracking WebSocket
connection, message, error, and performance metrics.

Models:
- ConnectionMetrics: Connection lifecycle metrics
- MessageMetrics: Message flow statistics
- ErrorMetrics: Error tracking by type
- PerformanceMetrics: Latency and throughput metrics
- AggregatedMetrics: Combined metrics snapshot
- MetricsSnapshot: Time-series data point
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MetricCategory(str, Enum):
    """Categories of metrics collected.

    Renamed from MetricType to avoid collision with the unrelated
    AlertMetricType in monitoring_alerts.py (which enumerates the specific
    metric names that can trigger alerts). This enum groups metrics by
    collection domain (connection / message / error / performance).
    """

    CONNECTION = "connection"
    MESSAGE = "message"
    ERROR = "error"
    PERFORMANCE = "performance"
    AGGREGATED = "aggregated"


class ErrorType(str, Enum):
    """Types of errors tracked."""

    CONNECTION_ERROR = "connection_error"
    AUTHENTICATION_ERROR = "authentication_error"
    MESSAGE_PARSE_ERROR = "message_parse_error"
    FILTER_ERROR = "filter_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    QUEUE_ERROR = "queue_error"
    UNKNOWN_ERROR = "unknown_error"


class ConnectionMetrics(BaseModel):
    """
    WebSocket connection lifecycle metrics.

    Tracks connection state changes and counts.
    """

    # Current connection counts
    active_connections: int = 0
    connecting_connections: int = 0  # Currently connecting
    disconnecting_connections: int = 0  # Currently disconnecting

    # Total connection counts (cumulative)
    total_connections: int = 0
    total_disconnections: int = 0
    total_connection_failures: int = 0

    # Connection duration statistics (seconds)
    avg_connection_duration_seconds: float = 0.0
    max_connection_duration_seconds: float = 0.0
    min_connection_duration_seconds: float = 0.0

    # Reconnection tracking
    total_reconnections: int = 0
    unique_users_connected: int = 0

    # Timestamp
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def increment_connection(self, user_id: str | None = None) -> None:
        """Increment total connections counter."""
        self.total_connections += 1
        if user_id:
            # Track unique users in a separate set (not persisted here)
            pass

    def increment_disconnection(self, duration_seconds: float) -> None:
        """Increment disconnection counter and update duration stats."""
        self.total_disconnections += 1

        # Update duration statistics
        if self.total_disconnections == 1:
            self.avg_connection_duration_seconds = duration_seconds
            self.max_connection_duration_seconds = duration_seconds
            self.min_connection_duration_seconds = duration_seconds
        else:
            # Update average
            n = self.total_disconnections
            self.avg_connection_duration_seconds = (
                self.avg_connection_duration_seconds * (n - 1) + duration_seconds
            ) / n
            # Update max/min
            self.max_connection_duration_seconds = max(
                self.max_connection_duration_seconds, duration_seconds
            )
            self.min_connection_duration_seconds = min(
                self.min_connection_duration_seconds, duration_seconds
            )

    def increment_connection_failure(self) -> None:
        """Increment connection failure counter."""
        self.total_connection_failures += 1


class MessageMetrics(BaseModel):
    """
    WebSocket message flow metrics.

    Tracks message statistics by type and direction.
    """

    # Message counts (cumulative)
    total_messages_sent: int = 0
    total_messages_received: int = 0
    total_messages_filtered: int = 0
    total_messages_queued: int = 0  # Offline message queue

    # Message counts by type
    messages_by_type: dict[str, int] = Field(default_factory=dict)

    # Message size statistics (bytes)
    avg_message_size_bytes: int = 0
    max_message_size_bytes: int = 0
    total_message_size_bytes: int = 0  # Cumulative size

    # Message rate (messages per second)
    current_send_rate: float = 0.0  # Messages sent in last second
    current_receive_rate: float = 0.0  # Messages received in last second

    # Broadcast statistics
    total_broadcasts: int = 0
    avg_broadcast_recipients: float = 0.0

    # Timestamp
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def record_message_sent(
        self, message_type: str, size_bytes: int, recipients: int = 1
    ) -> None:
        """Record a sent message."""
        self.total_messages_sent += size_bytes > 0  # Only count if size provided

        # Update type statistics
        if message_type not in self.messages_by_type:
            self.messages_by_type[message_type] = 0
        self.messages_by_type[message_type] += 1

        # Update size statistics
        if size_bytes > 0:
            self.total_message_size_bytes += size_bytes
            if self.total_messages_sent > 0:
                self.avg_message_size_bytes = (
                    self.total_message_size_bytes // self.total_messages_sent
                )
            self.max_message_size_bytes = max(self.max_message_size_bytes, size_bytes)

        # Update broadcast stats
        if recipients > 1:
            self.total_broadcasts += 1
            n = self.total_broadcasts
            self.avg_broadcast_recipients = (
                self.avg_broadcast_recipients * (n - 1) + recipients
            ) / n

    def record_message_received(self, message_type: str) -> None:
        """Record a received message."""
        self.total_messages_received += 1

        if message_type not in self.messages_by_type:
            self.messages_by_type[message_type] = 0
        self.messages_by_type[message_type] += 1

    def record_message_filtered(self) -> None:
        """Record a filtered message."""
        self.total_messages_filtered += 1

    def record_message_queued(self) -> None:
        """Record a queued offline message."""
        self.total_messages_queued += 1


class ErrorMetrics(BaseModel):
    """
    WebSocket error tracking metrics.

    Tracks errors by type and severity.
    """

    # Error counts (cumulative)
    total_errors: int = 0
    total_critical_errors: int = 0  # Errors that cause connection loss

    # Errors by type
    errors_by_type: dict[str, int] = Field(default_factory=dict)

    # Error details (last N errors)
    recent_errors: list[dict[str, Any]] = Field(default_factory=list)
    max_recent_errors: int = 100

    # Error rate tracking
    current_error_rate: float = 0.0  # Errors per second

    # Timestamp
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def record_error(
        self,
        error_type: ErrorType,
        message: str,
        is_critical: bool = False,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Record an error."""
        self.total_errors += 1

        if is_critical:
            self.total_critical_errors += 1

        # Update type statistics
        error_type_str = error_type.value
        if error_type_str not in self.errors_by_type:
            self.errors_by_type[error_type_str] = 0
        self.errors_by_type[error_type_str] += 1

        # Add to recent errors
        error_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "type": error_type_str,
            "message": message,
            "is_critical": is_critical,
            "context": context or {},
        }
        self.recent_errors.append(error_entry)

        # Trim recent errors if needed
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors = self.recent_errors[-self.max_recent_errors :]

    def get_error_summary(self) -> dict[str, Any]:
        """Get summary of errors by type."""
        return {
            "total_errors": self.total_errors,
            "critical_errors": self.total_critical_errors,
            "errors_by_type": dict(self.errors_by_type),
            "recent_error_count": len(self.recent_errors),
        }


class PerformanceMetrics(BaseModel):
    """
    WebSocket performance metrics.

    Tracks latency, throughput, and resource usage.
    """

    # Latency statistics (milliseconds)
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0  # Median
    p95_latency_ms: float = 0.0  # 95th percentile
    p99_latency_ms: float = 0.0  # 99th percentile
    max_latency_ms: float = 0.0

    # Latency samples for percentile calculation
    latency_samples: list[float] = Field(default_factory=list)
    max_latency_samples: int = 1000

    # Throughput metrics
    messages_per_second: float = 0.0
    bytes_per_second: float = 0.0

    # Memory usage (bytes)
    memory_usage_bytes: int = 0
    queue_memory_bytes: int = 0

    # CPU usage (percentage)
    cpu_usage_percent: float = 0.0

    # Timestamp
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        # Add to samples
        self.latency_samples.append(latency_ms)

        # Update max
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)

        # Trim samples if needed
        if len(self.latency_samples) > self.max_latency_samples:
            self.latency_samples.pop(0)

        # Update statistics
        self._recalculate_statistics()

    def _recalculate_statistics(self) -> None:
        """Recalculate latency statistics from samples."""
        if not self.latency_samples:
            return

        # Calculate average
        self.avg_latency_ms = sum(self.latency_samples) / len(self.latency_samples)

        # Calculate percentiles
        sorted_samples = sorted(self.latency_samples)
        n = len(sorted_samples)

        self.p50_latency_ms = sorted_samples[int(n * 0.5)]
        self.p95_latency_ms = sorted_samples[int(n * 0.95)]
        self.p99_latency_ms = sorted_samples[int(n * 0.99)]

    def get_latency_summary(self) -> dict[str, float]:
        """Get summary of latency metrics."""
        return {
            "avg_ms": self.avg_latency_ms,
            "p50_ms": self.p50_latency_ms,
            "p95_ms": self.p95_latency_ms,
            "p99_ms": self.p99_latency_ms,
            "max_ms": self.max_latency_ms,
            "sample_count": len(self.latency_samples),
        }


class AggregatedMetrics(BaseModel):
    """
    Aggregated metrics snapshot combining all metric types.

    Provides a unified view of WebSocket system health.
    """

    connection: ConnectionMetrics = Field(default_factory=ConnectionMetrics)
    message: MessageMetrics = Field(default_factory=MessageMetrics)
    error: ErrorMetrics = Field(default_factory=ErrorMetrics)
    performance: PerformanceMetrics = Field(default_factory=PerformanceMetrics)

    # Health score (0-100)
    health_score: float = 100.0

    # Timestamp
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    def calculate_health_score(self) -> float:
        """
        Calculate overall health score based on all metrics.

        Scoring:
        - 100-90: Healthy
        - 89-70: Degraded
        - 69-50: Warning
        - 49-0: Critical

        Factors:
        - Connection success rate (weight: 0.3)
        - Error rate (weight: 0.4)
        - Performance (weight: 0.3)
        """
        # Connection health
        total_conn_attempts = (
            self.connection.total_connections
            + self.connection.total_connection_failures
        )
        if total_conn_attempts > 0:
            connection_success_rate = (
                self.connection.total_connections / total_conn_attempts
            )
        else:
            connection_success_rate = 1.0

        connection_score = connection_success_rate * 100

        # Error health (inverse of error rate)
        if self.message.total_messages_sent > 0:
            error_rate = self.error.total_errors / self.message.total_messages_sent
        else:
            error_rate = 0.0

        error_score = max(0, 100 - (error_rate * 100))

        # Performance health (based on latency)
        # P95 < 100ms = 100, P95 > 1000ms = 0
        if self.performance.p95_latency_ms < 100:
            performance_score = 100.0
        elif self.performance.p95_latency_ms > 1000:
            performance_score = 0.0
        else:
            performance_score = 100 - ((self.performance.p95_latency_ms - 100) / 9)

        # Weighted average
        self.health_score = (
            connection_score * 0.3 + error_score * 0.4 + performance_score * 0.3
        )

        return self.health_score

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all metrics."""
        return {
            "health_score": self.health_score,
            "active_connections": self.connection.active_connections,
            "total_messages": self.message.total_messages_sent,
            "total_errors": self.error.total_errors,
            "avg_latency_ms": self.performance.avg_latency_ms,
            "p95_latency_ms": self.performance.p95_latency_ms,
            "timestamp": self.timestamp,
        }


class MetricsSnapshot(BaseModel):
    """
    Time-series metrics snapshot for historical tracking.

    Used for storing metrics over time for trend analysis.
    """

    id: str | None = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )

    # Metrics data (serialized)
    connection: ConnectionMetrics
    message: MessageMetrics
    error: ErrorMetrics
    performance: PerformanceMetrics

    # Snapshot metadata
    snapshot_type: str = "periodic"  # periodic, on_event, manual
    source: str = "websocket_monitor"  # Service that created snapshot

    # Aggregated health score
    health_score: float = 100.0


class MetricsQuery(BaseModel):
    """
    Query parameters for fetching historical metrics.
    """

    start_time: str | None = None  # ISO format timestamp
    end_time: str | None = None  # ISO format timestamp
    metric_types: list[MetricCategory] = Field(default_factory=list)
    limit: int = 100
    offset: int = 0
    aggregate_by: str | None = None  # "1m", "5m", "1h", etc.


class MetricsReport(BaseModel):
    """
    Report generated from metrics analysis.
    """

    report_id: str
    generated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    time_range: dict[str, str] = Field(default_factory=dict)

    # Summary statistics
    summary: dict[str, Any] = Field(default_factory=dict)

    # Trends
    trends: dict[str, str] = Field(
        default_factory=dict
    )  # "improving", "stable", "degrading"

    # Recommendations
    recommendations: list[str] = Field(default_factory=list)

    # Detailed metrics
    metrics: AggregatedMetrics
