"""Message broker factory."""

from __future__ import annotations

import os

from .base import MessageBroker
from .kafka_broker import KafkaBroker
from .redis_broker import RedisBroker

_broker: MessageBroker | None = None


def get_message_broker() -> MessageBroker:
    """Return singleton broker based on configuration."""
    global _broker
    if _broker is not None:
        return _broker

    broker_kind = os.getenv("MESSAGE_BROKER", "redis").lower()
    if broker_kind == "kafka":
        _broker = KafkaBroker()
        return _broker

    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    consumer_group = os.getenv("MESSAGE_CONSUMER_GROUP", "soc_workers")
    _broker = RedisBroker(redis_url=redis_url, consumer_group=consumer_group)
    return _broker


def set_message_broker_for_test(broker: MessageBroker | None) -> None:
    """Inject broker in tests."""
    global _broker
    _broker = broker
