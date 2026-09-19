"""Unified message broker package."""

from .base import MessageBroker
from .factory import get_broker, get_message_broker, inject_backend_setting
from .memory_broker import MemoryBroker
from .redis_broker import RedisBroker
from .schemas import (
    BrokerMessage,
    ConsumerConfig,
    EventEnvelope,
    EventPriority,
    PublishOptions,
)

__all__ = [
    "BrokerMessage",
    "ConsumerConfig",
    "EventEnvelope",
    "EventPriority",
    "MemoryBroker",
    "MessageBroker",
    "PublishOptions",
    "RedisBroker",
    "get_broker",
    "get_message_broker",
    "inject_backend_setting",
]
