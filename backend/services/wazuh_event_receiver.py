"""Wazuh webhook receiver service, publishes into unified event bus."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from schemas.wazuh import WazuhWebhookEvent
from services.event_bus import get_event_bus
from services.wazuh_alert_mapper import get_alert_mapper

logger = logging.getLogger(__name__)


class WazuhEventReceiverService:
    """Receives webhook payloads and emits unified events."""

    def __init__(self):
        self.event_bus = get_event_bus()
        self.mapper = get_alert_mapper()

    async def ingest_webhook_event(
        self,
        payload: dict[str, Any],
        *,
        tenant_id: str = "default",
        source_ip: str | None = None,
    ) -> dict[str, Any]:
        event = WazuhWebhookEvent.model_validate(payload)
        mapped = self.mapper.map_alert(payload)

        event_id = str(event.id or mapped.get("id") or f"wazuh-{int(datetime.now(timezone.utc).timestamp())}")
        severity = (mapped.get("severity") or "medium").lower()

        message_id = await self.event_bus.publish(
            event_type="wazuh.alert.received",
            source="wazuh-webhook",
            payload={
                "wazuh": payload,
                "normalized_alert": mapped,
            },
            event_id=event_id,
            tenant_id=tenant_id,
            priority=severity,
            metadata={
                "ingest": "webhook",
                "source_ip": source_ip,
                "received_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        return {
            "accepted": message_id is not None,
            "event_id": event_id,
            "broker_message_id": message_id,
            "severity": severity,
        }


_receiver: WazuhEventReceiverService | None = None


def get_wazuh_event_receiver() -> WazuhEventReceiverService:
    global _receiver
    if _receiver is None:
        _receiver = WazuhEventReceiverService()
    return _receiver
