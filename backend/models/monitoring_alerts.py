"""
Monitoring Alert Rules Data Models

This module defines data models for alert rules that trigger based on
WebSocket monitoring metrics thresholds.

Models:
- AlertRule: Alert rule with threshold conditions
- AlertRuleEvaluation: Result of evaluating a rule against metrics
- AlertNotification: Notification sent when a rule triggers
- AlertHistory: Historical record of triggered alerts
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AlertSeverity(str, Enum):
    """Severity levels for alerts."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertOperator(str, Enum):
    """Comparison operators for alert conditions."""

    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    EQUAL = "eq"
    NOT_EQUAL = "ne"


class AlertChannelType(str, Enum):
    """Types of alert notification channels."""

    LOG = "log"
    WEBHOOK = "webhook"
    EMAIL = "email"
    SMS = "sms"


class AlertMetricType(str, Enum):
    """Specific metrics that can trigger alerts.

    Renamed from MetricType to avoid collision with the unrelated
    MetricCategory in websocket_metrics.py (which groups metrics by
    collection domain). This enum lists the concrete metric names an
    alert condition can reference.
    """

    HEALTH_SCORE = "health_score"
    ACTIVE_CONNECTIONS = "active_connections"
    MESSAGE_SEND_RATE = "message_send_rate"
    ERROR_RATE = "error_rate"
    AVG_LATENCY = "avg_latency"
    P95_LATENCY = "p95_latency"
    P99_LATENCY = "p99_latency"


class AlertCondition(BaseModel):
    """A single condition for an alert rule."""

    metric_type: AlertMetricType
    operator: AlertOperator
    threshold: float
    duration_seconds: int = 60  # How long condition must be true


class AlertRule(BaseModel):
    """
    Alert rule for monitoring metrics.

    Triggers when conditions are met for specified duration.
    """

    id: str | None = None
    user_id: str  # Owner of the rule
    name: str  # Rule name
    description: str = ""  # Rule description

    # Alert conditions
    conditions: list[AlertCondition] = Field(min_items=1, max_items=10)
    require_all: bool = True  # True = AND, False = OR

    # Alert properties
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True

    # Notification channels
    channels: list[AlertChannelType] = Field(
        default_factory=lambda: [AlertChannelType.LOG]
    )
    channel_config: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # Cooldown and limits
    cooldown_seconds: int = 300  # Don't alert again for 5 minutes
    max_notifications_per_hour: int = 10

    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_triggered_at: str | None = None

    # Trigger count
    total_triggers: int = 0

    def should_trigger(
        self, metrics: dict[str, float], current_time: float | None = None
    ) -> tuple[bool, str]:
        """
        Evaluate if alert should trigger based on current metrics.

        Args:
            metrics: Dictionary of metric names to values
            current_time: Current Unix timestamp

        Returns:
            (should_trigger, reason) tuple
        """
        import time

        if not self.enabled:
            return False, "Rule is disabled"

        # Check cooldown
        if self.last_triggered_at:
            last_trigger = datetime.fromisoformat(self.last_triggered_at).timestamp()
            if current_time is None:
                current_time = time.time()

            if current_time - last_trigger < self.cooldown_seconds:
                return False, "Rule in cooldown period"

        # Evaluate conditions
        condition_results = []

        for condition in self.conditions:
            metric_value = metrics.get(condition.metric_type.value)

            if metric_value is None:
                condition_results.append(False)
                continue

            # Evaluate condition
            result = self._evaluate_condition(
                metric_value, condition.operator, condition.threshold
            )
            condition_results.append(result)

        # Determine if all/any conditions met
        if self.require_all:
            triggered = all(condition_results)
            reason = (
                "All conditions met"
                if triggered
                else f"Not all conditions met: {condition_results}"
            )
        else:
            triggered = any(condition_results)
            reason = (
                "At least one condition met"
                if triggered
                else f"No conditions met: {condition_results}"
            )

        return triggered, reason

    def _evaluate_condition(
        self, value: float, operator: AlertOperator, threshold: float
    ) -> bool:
        """Evaluate a single condition."""
        if operator == AlertOperator.GREATER_THAN:
            return value > threshold
        elif operator == AlertOperator.GREATER_THAN_OR_EQUAL:
            return value >= threshold
        elif operator == AlertOperator.LESS_THAN:
            return value < threshold
        elif operator == AlertOperator.LESS_THAN_OR_EQUAL:
            return value <= threshold
        elif operator == AlertOperator.EQUAL:
            return value == threshold
        elif operator == AlertOperator.NOT_EQUAL:
            return value != threshold
        return False

    def record_trigger(self) -> None:
        """Record that this alert was triggered."""
        self.total_triggers += 1
        self.last_triggered_at = datetime.now(UTC).isoformat()


class AlertNotification(BaseModel):
    """
    Alert notification sent to a channel.
    """

    id: str | None = None
    rule_id: str
    rule_name: str
    severity: AlertSeverity

    # Message content
    title: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)

    # Channel information
    channel: AlertChannelType
    channel_config: dict[str, Any] = Field(default_factory=dict)

    # Status
    status: Literal["pending", "sent", "failed"] = "pending"
    error_message: str | None = None

    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    sent_at: str | None = None


class AlertHistory(BaseModel):
    """
    Historical record of triggered alerts.
    """

    id: str | None = None
    rule_id: str
    rule_name: str
    user_id: str

    # Trigger information
    severity: AlertSeverity
    triggered_at: str
    metrics_snapshot: dict[str, float] = Field(default_factory=dict)

    # Notifications sent
    notifications_sent: list[str] = Field(default_factory=list)  # Notification IDs

    # Resolution
    resolved_at: str | None = None
    resolution_notes: str | None = None


class AlertRuleCreate(BaseModel):
    """Schema for creating a new alert rule."""

    name: str
    description: str = ""
    conditions: list[AlertCondition]
    require_all: bool = True
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True
    channels: list[AlertChannelType] = Field(
        default_factory=lambda: [AlertChannelType.LOG]
    )
    channel_config: dict[str, dict[str, Any]] = Field(default_factory=dict)
    cooldown_seconds: int = 300
    max_notifications_per_hour: int = 10


class AlertRuleUpdate(BaseModel):
    """Schema for updating an alert rule."""

    name: str | None = None
    description: str | None = None
    conditions: list[AlertCondition] | None = None
    require_all: bool | None = None
    severity: AlertSeverity | None = None
    enabled: bool | None = None
    channels: list[AlertChannelType] | None = None
    channel_config: dict[str, dict[str, Any]] | None = None
    cooldown_seconds: int | None = None
    max_notifications_per_hour: int | None = None


class AlertRuleResponse(BaseModel):
    """Schema for alert rule response."""

    id: str
    user_id: str
    name: str
    description: str
    conditions: list[AlertCondition]
    require_all: bool
    severity: AlertSeverity
    enabled: bool
    channels: list[AlertChannelType]
    cooldown_seconds: int
    max_notifications_per_hour: int
    total_triggers: int
    created_at: str
    updated_at: str
    last_triggered_at: str | None

    class Config:
        from_attributes = True


class AlertStats(BaseModel):
    """Statistics for alerts."""

    total_rules: int
    active_rules: int
    total_triggers: int
    triggers_by_severity: dict[str, int] = Field(default_factory=dict)
    recent_triggers: list[AlertHistory] = Field(default_factory=list)
