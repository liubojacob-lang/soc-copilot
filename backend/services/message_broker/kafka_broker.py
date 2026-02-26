"""Kafka broker placeholder for future migration."""

from __future__ import annotations

from .base import MessageBroker
from .schemas import BrokerMessage, ConsumerConfig, EventEnvelope, PublishOptions


class KafkaBroker(MessageBroker):
    """Not implemented yet. Keeps extension point stable for future Kafka adoption."""

    async def publish(self, envelope: EventEnvelope, options: PublishOptions | None = None) -> str | None:
        raise NotImplementedError("KafkaBroker is not implemented yet")

    async def consume(self, config: ConsumerConfig, priority_order: bool = True) -> list[BrokerMessage]:
        raise NotImplementedError("KafkaBroker is not implemented yet")

    async def ack(self, stream: str, message_id: str, consumer_group: str) -> bool:
        raise NotImplementedError("KafkaBroker is not implemented yet")

    async def nack(
        self,
        stream: str,
        message_id: str,
        consumer_group: str,
        envelope: EventEnvelope,
        reason: str,
    ) -> bool:
        raise NotImplementedError("KafkaBroker is not implemented yet")

    async def replay_dlq(self, dlq_stream: str, target_stream: str, limit: int = 100) -> int:
        raise NotImplementedError("KafkaBroker is not implemented yet")

    async def process_delayed_messages(self, limit: int = 100) -> int:
        raise NotImplementedError("KafkaBroker is not implemented yet")

    def get_queue_stats(self) -> dict[str, dict[str, int | str]]:
        raise NotImplementedError("KafkaBroker is not implemented yet")

    def health_check(self) -> dict[str, bool]:
        return {"kafka": False}
