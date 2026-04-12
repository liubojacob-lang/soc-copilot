"""Example usage for unified message broker."""

from __future__ import annotations

from services.message_broker import (
    ConsumerConfig,
    EventEnvelope,
    EventPriority,
    get_message_broker,
)


async def publish_alert_event(alert: dict) -> str | None:
    broker = get_message_broker()
    envelope = EventEnvelope(
        event_id=str(alert.get("id", "unknown")),
        event_type="alert.created",
        source=alert.get("source", "soc"),
        priority=EventPriority(alert.get("severity", "medium")),
        payload=alert,
        metadata={"module": "security-alerts"},
    )
    return await broker.publish(envelope)


async def consume_events(worker_name: str = "worker_1") -> None:
    broker = get_message_broker()
    cfg = ConsumerConfig(consumer_name=worker_name)
    messages = await broker.consume(cfg)
    for msg in messages:
        try:
            # business logic
            _ = msg.envelope.payload
            await broker.ack(msg.stream, msg.message_id, cfg.consumer_group)
        except Exception as exc:
            await broker.nack(
                msg.stream, msg.message_id, cfg.consumer_group, msg.envelope, str(exc)
            )
