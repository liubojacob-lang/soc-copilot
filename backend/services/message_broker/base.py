"""Abstract message broker interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from .schemas import BrokerMessage, ConsumerConfig, EventEnvelope, PublishOptions


class MessageBroker(ABC):
    """Abstract broker contract, supports Redis/Kafka interchangeable backends."""

    @abstractmethod
    async def publish(
        self, envelope: EventEnvelope, options: PublishOptions | None = None
    ) -> str | None:
        """Publish a unified event envelope and return broker message id."""

    @abstractmethod
    async def consume(
        self, config: ConsumerConfig, priority_order: bool = True
    ) -> list[BrokerMessage]:
        """Consume events using consumer group semantics."""

    @abstractmethod
    async def ack(self, stream: str, message_id: str, consumer_group: str) -> bool:
        """Acknowledge successful processing."""

    @abstractmethod
    async def nack(
        self,
        stream: str,
        message_id: str,
        consumer_group: str,
        envelope: EventEnvelope,
        reason: str,
    ) -> bool:
        """Negative acknowledge: retry or route to DLQ."""

    @abstractmethod
    async def replay_dlq(
        self, dlq_stream: str, target_stream: str, limit: int = 100
    ) -> int:
        """Replay DLQ messages back to target stream."""

    @abstractmethod
    async def process_delayed_messages(self, limit: int = 100) -> int:
        """Move due delayed events into active streams."""

    @abstractmethod
    def get_queue_stats(self) -> dict[str, dict[str, int | str]]:
        """Return queue health and pending metrics."""

    @abstractmethod
    def health_check(self) -> dict[str, bool]:
        """Health probe for broker dependencies."""
