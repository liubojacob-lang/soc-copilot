"""
Alert Evaluation Service

This service evaluates WebSocket metrics against alert rules and
sends notifications when thresholds are exceeded.

Features:
- Real-time rule evaluation
- Multiple notification channels (log, webhook, email)
- Alert history tracking
- Cooldown management
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from httpx import AsyncClient

from core.logger import get_logger
from models.monitoring_alerts import (
    AlertRule,
    AlertNotification,
    AlertHistory,
    AlertSeverity,
    AlertChannelType,
    MetricType
)
from models.websocket_metrics import AggregatedMetrics

logger = get_logger(__name__)


class NotificationChannel:
    """Base class for notification channels."""

    async def send(self, notification: AlertNotification) -> bool:
        """Send a notification. Returns True if successful."""
        raise NotImplementedError


class LogNotificationChannel(NotificationChannel):
    """Log-based notification channel."""

    async def send(self, notification: AlertNotification) -> bool:
        """Log notification."""
        log_level = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical,
        }.get(notification.severity, logger.warning)

        log_level(
            f"Alert: {notification.title} | "
            f"Rule: {notification.rule_name} | "
            f"Severity: {notification.severity.value} | "
            f"Message: {notification.message}"
        )

        return True


class WebhookNotificationChannel(NotificationChannel):
    """Webhook-based notification channel."""

    def __init__(self):
        self.client = AsyncClient(timeout=10.0)

    async def send(self, notification: AlertNotification) -> bool:
        """Send notification via webhook."""
        webhook_url = notification.channel_config.get("webhook_url")

        if not webhook_url:
            logger.error("Webhook URL not configured")
            return False

        try:
            payload = {
                "id": notification.id,
                "rule_name": notification.rule_name,
                "severity": notification.severity.value,
                "title": notification.title,
                "message": notification.message,
                "details": notification.details,
                "timestamp": notification.created_at,
            }

            response = await self.client.post(webhook_url, json=payload)
            response.raise_for_status()

            logger.info(f"Webhook notification sent: {webhook_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False


class EmailNotificationChannel(NotificationChannel):
    """Email-based notification channel."""

    async def send(self, notification: AlertNotification) -> bool:
        """Send notification via email."""
        # TODO: Implement email sending
        logger.warning("Email notification channel not yet implemented")
        return False


class AlertEvaluator:
    """
    Evaluates metrics against alert rules and triggers notifications.
    """

    def __init__(self):
        # Alert rules: {rule_id: AlertRule}
        self.rules: Dict[str, AlertRule] = {}
        # Alert history
        self.history: List[AlertHistory] = []
        # Notification channels
        self.channels: Dict[AlertChannelType, NotificationChannel] = {
            AlertChannelType.LOG: LogNotificationChannel(),
            AlertChannelType.WEBHOOK: WebhookNotificationChannel(),
            AlertChannelType.EMAIL: EmailNotificationChannel(),
        }
        self._lock = asyncio.Lock()

    async def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        async with self._lock:
            if not rule.id:
                rule.id = f"rule_{int(time.time() * 1000)}"

            self.rules[rule.id] = rule
            logger.info(f"Added alert rule: {rule.name} ({rule.id})")

    async def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing alert rule."""
        async with self._lock:
            if rule_id not in self.rules:
                return False

            rule = self.rules[rule_id]

            for key, value in updates.items():
                if hasattr(rule, key):
                    setattr(rule, key, value)

            rule.updated_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Updated alert rule: {rule.name} ({rule_id})")
            return True

    async def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        async with self._lock:
            if rule_id in self.rules:
                del self.rules[rule_id]
                logger.info(f"Removed alert rule: {rule_id}")
                return True
            return False

    async def get_rules(self, user_id: Optional[str] = None) -> List[AlertRule]:
        """Get alert rules, optionally filtered by user."""
        async with self._lock:
            rules = list(self.rules.values())

            if user_id:
                rules = [r for r in rules if r.user_id == user_id]

            return rules

    async def get_rule(self, rule_id: str) -> Optional[AlertRule]:
        """Get a specific alert rule."""
        async with self._lock:
            return self.rules.get(rule_id)

    async def evaluate_metrics(
        self,
        metrics: AggregatedMetrics,
        user_id: Optional[str] = None
    ) -> List[AlertNotification]:
        """
        Evaluate metrics against all rules and trigger notifications.

        Args:
            metrics: Current aggregated metrics
            user_id: Optional user ID to filter rules

        Returns:
            List of notifications sent
        """
        notifications = []

        # Get relevant rules
        rules = await self.get_rules(user_id)
        rules = [r for r in rules if r.enabled]

        # Extract metric values
        metric_values = self._extract_metric_values(metrics)

        # Evaluate each rule
        for rule in rules:
            should_trigger, reason = rule.should_trigger(
                metric_values,
                current_time=time.time()
            )

            if should_trigger:
                # Record trigger
                rule.record_trigger()

                # Create notification
                notification = await self._create_notification(rule, metric_values)

                # Send to each channel
                for channel_type in rule.channels:
                    channel = self.channels.get(channel_type)

                    if channel:
                        notification.channel = channel_type
                        notification.channel_config = rule.channel_config.get(
                            channel_type.value,
                            {}
                        )

                        success = await channel.send(notification)

                        if success:
                            notification.status = "sent"
                            notification.sent_at = datetime.now(timezone.utc).isoformat()
                        else:
                            notification.status = "failed"

                        notifications.append(notification)

                # Record in history
                await self._record_alert(rule, metric_values, notifications)

        return notifications

    def _extract_metric_values(self, metrics: AggregatedMetrics) -> Dict[str, float]:
        """Extract metric values from aggregated metrics."""
        return {
            "health_score": metrics.health_score,
            "active_connections": metrics.connection.active_connections,
            "message_send_rate": metrics.message.current_send_rate,
            "message_receive_rate": metrics.message.current_receive_rate,
            "total_errors": metrics.error.total_errors,
            "error_rate": (
                metrics.error.total_errors / metrics.message.total_messages_sent
                if metrics.message.total_messages_sent > 0
                else 0.0
            ),
            "avg_latency": metrics.performance.avg_latency_ms,
            "p50_latency": metrics.performance.p50_latency_ms,
            "p95_latency": metrics.performance.p95_latency_ms,
            "p99_latency": metrics.performance.p99_latency_ms,
        }

    async def _create_notification(
        self,
        rule: AlertRule,
        metrics: Dict[str, float]
    ) -> AlertNotification:
        """Create an alert notification."""
        # Build title and message
        title = f"Alert: {rule.name}"

        condition_descriptions = []
        for condition in rule.conditions:
            condition_descriptions.append(
                f"{condition.metric_type.value} {condition.operator.value} {condition.threshold}"
            )

        message = (
            f"Alert rule '{rule.name}' triggered. "
            f"Conditions: {' AND ' if rule.require_all else ' OR '.join(condition_descriptions)}. "
        )

        # Add current values
        current_values = []
        for condition in rule.conditions:
            value = metrics.get(condition.metric_type.value)
            if value is not None:
                current_values.append(f"{condition.metric_type.value}={value:.2f}")

        message += f"Current values: {', '.join(current_values)}"

        return AlertNotification(
            rule_id=rule.id,
            rule_name=rule.name,
            severity=rule.severity,
            title=title,
            message=message,
            details={
                "rule_id": rule.id,
                "rule_name": rule.name,
                "conditions": [c.model_dump() for c in rule.conditions],
                "metrics": metrics,
            },
        )

    async def _record_alert(
        self,
        rule: AlertRule,
        metrics: Dict[str, float],
        notifications: List[AlertNotification]
    ) -> None:
        """Record alert in history."""
        history_entry = AlertHistory(
            rule_id=rule.id,
            rule_name=rule.name,
            user_id=rule.user_id,
            severity=rule.severity,
            triggered_at=datetime.now(timezone.utc).isoformat(),
            metrics_snapshot=metrics,
            notifications_sent=[n.id for n in notifications if n.id],
        )

        self.history.append(history_entry)

        # Trim history if needed
        if len(self.history) > 1000:
            self.history = self.history[-1000:]

    async def get_history(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AlertHistory]:
        """Get alert history."""
        history = self.history

        if user_id:
            history = [h for h in history if h.user_id == user_id]

        # Return most recent first
        return list(reversed(history[-limit:]))

    async def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get alert statistics."""
        rules = await self.get_rules(user_id)
        history = await self.get_history(user_id, limit=1000)

        triggers_by_severity = {"info": 0, "warning": 0, "error": 0, "critical": 0}
        for entry in history:
            triggers_by_severity[entry.severity.value] += 1

        return {
            "total_rules": len(rules),
            "active_rules": len([r for r in rules if r.enabled]),
            "total_triggers": len(history),
            "triggers_by_severity": triggers_by_severity,
            "recent_triggers": history[:10],
        }


# Global instance
_evaluator: Optional[AlertEvaluator] = None


def get_alert_evaluator() -> AlertEvaluator:
    """Get or create the global alert evaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = AlertEvaluator()
    return _evaluator


async def start_alert_evaluator():
    """Initialize the alert evaluator."""
    evaluator = get_alert_evaluator()
    logger.info("Alert evaluator initialized")
    return evaluator
