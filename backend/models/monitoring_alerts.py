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

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime, timezone
from enum import Enum
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


class MetricType(str, Enum):
    """Types of metrics that can trigger alerts."""
    HEALTH_SCORE = "health_score"
    ACTIVE_CONNECTIONS = "active_connections"
    MESSAGE_SEND_RATE = "message_send_rate"
    ERROR_RATE = "error_rate"
    AVG_LATENCY = "avg_latency"
    P95_LATENCY = "p95_latency"
    P99_LATENCY = "p99_latency"


class AlertCondition(BaseModel):
    """A single condition for an alert rule."""
    metric_type: MetricType
    operator: AlertOperator
    threshold: float
    duration_seconds: int = 60  # How long condition must be true


class AlertRule(BaseModel):
    """
    Alert rule for monitoring metrics.

    Triggers when conditions are met for specified duration.
    """

    id: Optional[str] = None
    user_id: str  # Owner of the rule
    name: str  # Rule name
    description: str = ""  # Rule description

    # Alert conditions
    conditions: List[AlertCondition] = Field(min_items=1, max_items=10)
    require_all: bool = True  # True = AND, False = OR

    # Alert properties
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True

    # Notification channels
    channels: List[AlertChannelType] = Field(default_factory=lambda: [AlertChannelType.LOG])
    channel_config: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Cooldown and limits
    cooldown_seconds: int = 300  # Don't alert again for 5 minutes
    max_notifications_per_hour: int = 10

    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_triggered_at: Optional[str] = None

    # Trigger count
    total_triggers: int = 0

    def should_trigger(
        self,
        metrics: Dict[str, float],
        current_time: Optional[float] = None
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
                metric_value,
                condition.operator,
                condition.threshold
            )
            condition_results.append(result)

        # Determine if all/any conditions met
        if self.require_all:
            triggered = all(condition_results)
            reason = "All conditions met" if triggered else f"Not all conditions met: {condition_results}"
        else:
            triggered = any(condition_results)
            reason = "At least one condition met" if triggered else f"No conditions met: {condition_results}"

        return triggered, reason

    def _evaluate_condition(
        self,
        value: float,
        operator: AlertOperator,
        threshold: float
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
        self.last_triggered_at = datetime.now(timezone.utc).isoformat()


class AlertNotification(BaseModel):
    """
    Alert notification sent to a channel.
    """

    id: Optional[str] = None
    rule_id: str
    rule_name: str
    severity: AlertSeverity

    # Message content
    title: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)

    # Channel information
    channel: AlertChannelType
    channel_config: Dict[str, Any] = Field(default_factory=dict)

    # Status
    status: Literal["pending", "sent", "failed"] = "pending"
    error_message: Optional[str] = None

    # Timestamps
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sent_at: Optional[str] = None


class AlertHistory(BaseModel):
    """
    Historical record of triggered alerts.
    """

    id: Optional[str] = None
    rule_id: str
    rule_name: str
    user_id: str

    # Trigger information
    severity: AlertSeverity
    triggered_at: str
    metrics_snapshot: Dict[str, float] = Field(default_factory=dict)

    # Notifications sent
    notifications_sent: List[str] = Field(default_factory=list)  # Notification IDs

    # Resolution
    resolved_at: Optional[str] = None
    resolution_notes: Optional[str] = None


class AlertRuleCreate(BaseModel):
    """Schema for creating a new alert rule."""
    name: str
    description: str = ""
    conditions: List[AlertCondition]
    require_all: bool = True
    severity: AlertSeverity = AlertSeverity.WARNING
    enabled: bool = True
    channels: List[AlertChannelType] = Field(default_factory=lambda: [AlertChannelType.LOG])
    channel_config: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    cooldown_seconds: int = 300
    max_notifications_per_hour: int = 10


class AlertRuleUpdate(BaseModel):
    """Schema for updating an alert rule."""
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[List[AlertCondition]] = None
    require_all: Optional[bool] = None
    severity: Optional[AlertSeverity] = None
    enabled: Optional[bool] = None
    channels: Optional[List[AlertChannelType]] = None
    channel_config: Optional[Dict[str, Dict[str, Any]]] = None
    cooldown_seconds: Optional[int] = None
    max_notifications_per_hour: Optional[int] = None


class AlertRuleResponse(BaseModel):
    """Schema for alert rule response."""
    id: str
    user_id: str
    name: str
    description: str
    conditions: List[AlertCondition]
    require_all: bool
    severity: AlertSeverity
    enabled: bool
    channels: List[AlertChannelType]
    cooldown_seconds: int
    max_notifications_per_hour: int
    total_triggers: int
    created_at: str
    updated_at: str
    last_triggered_at: Optional[str]

    class Config:
        from_attributes = True


class AlertStats(BaseModel):
    """Statistics for alerts."""
    total_rules: int
    active_rules: int
    total_triggers: int
    triggers_by_severity: Dict[str, int] = Field(default_factory=dict)
    recent_triggers: List[AlertHistory] = Field(default_factory=list)
