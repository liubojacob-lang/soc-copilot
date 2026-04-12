"""Unified async event bus over MessageBroker."""

from __future__ import annotations

import logging
from typing import Any

from services.message_broker import (
    EventEnvelope,
    EventPriority,
    PublishOptions,
    get_message_broker,
)

logger = logging.getLogger(__name__)


class EventBus:
    """Central event bus for alerts, notifications and correlation events."""

    async def publish(
        self,
        event_type: str,
        source: str,
        payload: dict[str, Any],
        *,
        event_id: str,
        priority: str = "medium",
        tenant_id: str = "default",
        metadata: dict[str, Any] | None = None,
        delay_seconds: int = 0,
    ) -> str | None:
        envelope = EventEnvelope(
            event_id=event_id,
            event_type=event_type,
            source=source,
            tenant_id=tenant_id,
            priority=EventPriority(
                priority if priority in EventPriority._value2member_map_ else "medium"
            ),
            payload=payload,
            metadata=metadata or {},
        )
        broker = get_message_broker()
        return await broker.publish(
            envelope, PublishOptions(delay_seconds=delay_seconds)
        )

    def broker_stats(self) -> dict[str, dict[str, int | str]]:
        return get_message_broker().get_queue_stats()


_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
