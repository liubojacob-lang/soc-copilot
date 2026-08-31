"""Message broker factory with memory fallback.

Selects backend from:
- config (core/config.py → queue_backend)
- env (MESSAGE_BROKER, REDIS_URL)
- auto-degrade to MemoryBroker when Redis is unreachable
"""

from __future__ import annotations

import logging
import os

from .base import MessageBroker
from .kafka_broker import KafkaBroker
from .memory_broker import MemoryBroker
from .redis_broker import RedisBroker

logger = logging.getLogger(__name__)

_broker: MessageBroker | None = None
_broker_failed_health: bool = False


def get_message_broker() -> MessageBroker:
    """Return singleton broker based on configuration.

    Selection priority:
    1. Cached singleton (if healthy)
    2. queue_backend setting from core config (when available, via _inject)
    3. MESSAGE_BROKER env var  ("redis" | "kafka" | "memory")
    4. REDIS_URL env var          → RedisBroker if present
    5. memory fallback             → MemoryBroker (always works)
    """
    global _broker, _broker_failed_health

    if _broker is not None and not _broker_failed_health:
        return _broker

    # Refresh config each call so hot-reload works
    backend = _broker_backend_setting or os.getenv("MESSAGE_BROKER", "").lower()

    if backend == "kafka":
        _broker = KafkaBroker()
        return _broker

    if backend == "memory":
        _broker = MemoryBroker()
        return _broker

    # Try Redis (default) — degrade to memory if it fails health check
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    consumer_group = os.getenv("MESSAGE_CONSUMER_GROUP", "soc_workers")

    try:
        candidate = RedisBroker(redis_url=redis_url, consumer_group=consumer_group)
        health = candidate.health_check()
        if health.get("redis"):
            _broker = candidate
            _broker_failed_health = False
            logger.info("Message broker: redis backend healthy")
            return _broker
    except Exception as exc:
        logger.warning(
            "Redis broker init failed (degrading to memory): %s", exc
        )

    logger.warning("Redis unavailable — switching to MemoryBroker fallback")
    _broker = MemoryBroker()
    _broker_failed_health = False  # memory always healthy
    return _broker


def set_message_broker_for_test(broker: MessageBroker | None) -> None:
    """Inject broker in tests."""
    global _broker
    _broker = broker


# ── config injection ──────────────────────────────────────────────────

_broker_backend_setting: str | None = None


def inject_backend_setting(backend: str) -> None:
    """Called by core/config loader to pass queue_backend into factory."""
    global _broker_backend_setting, _broker, _broker_failed_health
    _broker_backend_setting = backend.lower() if backend else None
    # Reset so next get_message_broker() picks up new setting
    _broker = None
    _broker_failed_health = False


# ── convenience: get_broker (async wrapper for DI scenarios) ──────────

async def get_broker() -> MessageBroker:
    """Async convenience for FastAPI dependency injection."""
    return get_message_broker()
