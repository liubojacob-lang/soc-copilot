"""Notification service with plugin-based providers."""

from __future__ import annotations

import logging

from services.event_bus import get_event_bus
from services.notifications import (
    EmailProvider,
    FeishuProvider,
    NotificationMessage,
    NotificationRegistry,
    SlackProvider,
)
from services.notifications.templates import render_alert_template

logger = logging.getLogger(__name__)


class NotificationService:
    """Backward-compatible facade over pluggable notification providers."""

    def __init__(self):
        self.registry = NotificationRegistry()
        self.event_bus = get_event_bus()
        self._register_builtin()

        # backward-compatible attributes referenced by existing routers/tests
        feishu = self.registry.get("feishu")
        slack = self.registry.get("slack")
        email = self.registry.get("email")
        self.feishu_webhook = getattr(feishu, "webhook_url", None)
        self.slack_webhook = getattr(slack, "webhook_url", None)
        self.email_config = {
            "to": getattr(email, "to_email", None),
            "smtp_server": getattr(email, "smtp_server", None),
            "smtp_port": getattr(email, "smtp_port", None),
            "username": getattr(email, "smtp_user", None),
            "password": getattr(email, "smtp_password", None),
        }

    def _register_builtin(self) -> None:
        self.registry.register(FeishuProvider())
        self.registry.register(SlackProvider())
        self.registry.register(EmailProvider())

    def register_provider(self, provider) -> None:
        """Dynamic provider registration for extensions."""
        self.registry.register(provider)

    async def send_alert(
        self, alert: dict, channels: list[str] | None = None
    ) -> dict[str, bool]:
        title, body, severity = render_alert_template(alert)
        message = NotificationMessage(
            title=title, body=body, severity=severity, payload=alert
        )

        results: dict[str, bool] = {}
        for provider in self.registry.iter_selected(channels):
            try:
                success = await provider.send(message)
                results[provider.name] = success
                try:
                    await self.event_bus.publish(
                        event_type=(
                            "notification.sent" if success else "notification.failed"
                        ),
                        source=f"notification-{provider.name}",
                        payload={
                            "channel": provider.name,
                            "alert_id": alert.get("id"),
                            "success": success,
                        },
                        event_id=f"{alert.get('id', 'na')}:{provider.name}",
                        priority=severity,
                    )
                except Exception as bus_exc:
                    logger.warning(
                        "Event bus publish skipped for %s: %s", provider.name, bus_exc
                    )
            except Exception as exc:
                logger.error("Notification failed on %s: %s", provider.name, exc)
                results[provider.name] = False
        return results


_notification_service: NotificationService | None = None


def get_notification_service() -> NotificationService:
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
