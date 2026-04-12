"""Backward-compatible queue manager adapter.

Legacy code still imports MessageQueueManager. Internally it now delegates to the
new MessageBroker abstraction to provide:
- consumer groups
- ack/nack
- retry with delay
- DLQ
- delayed queue and replay
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from services.message_broker import (
    ConsumerConfig,
    EventEnvelope,
    EventPriority,
    get_message_broker,
)

logger = logging.getLogger(__name__)


class MessageQueueManager:
    """Compatibility wrapper for existing code paths."""

    def __init__(self, redis_url: str | None = None):
        self.broker = get_message_broker()
        self.consumer_group = "soc_workers"
        self.streams = {
            "critical": "events:critical",
            "high": "events:high",
            "medium": "events:medium",
            "low": "events:low",
        }

    def publish_alert(
        self, alert: dict, severity: str = "medium", max_length: int = 10000
    ) -> str | None:
        """Legacy synchronous publish API."""
        envelope = EventEnvelope(
            event_id=str(alert.get("id", "unknown")),
            event_type="alert.created",
            source=alert.get("source", "unknown"),
            priority=EventPriority(
                severity if severity in EventPriority._value2member_map_ else "medium"
            ),
            payload=alert,
            metadata={"compat": True, "max_length": max_length},
        )
        return self._run_async(self.broker.publish(envelope))

    async def publish_alert_async(
        self, alert: dict, severity: str = "medium", max_length: int = 10000
    ) -> str | None:
        """Async publish API for new callers."""
        envelope = EventEnvelope(
            event_id=str(alert.get("id", "unknown")),
            event_type="alert.created",
            source=alert.get("source", "unknown"),
            priority=EventPriority(
                severity if severity in EventPriority._value2member_map_ else "medium"
            ),
            payload=alert,
            metadata={"compat": True, "max_length": max_length},
        )
        return await self.broker.publish(envelope)

    async def consume_alerts_async(
        self,
        worker_id: str,
        count: int = 1,
        block: int = 5000,
        priority_order: bool = True,
    ) -> list[dict[str, Any]]:
        cfg = ConsumerConfig(
            consumer_group=self.consumer_group,
            consumer_name=f"worker_{worker_id}",
            count=count,
            block_ms=block,
        )
        messages = await self.broker.consume(cfg, priority_order=priority_order)
        return [
            {
                "message_id": msg.message_id,
                "stream": msg.stream,
                "alert": msg.envelope.payload,
                "severity": msg.envelope.priority.value,
                "raw_data": msg.raw_data,
                "envelope": msg.envelope,
            }
            for msg in messages
        ]

    def consume_alerts(
        self,
        worker_id: str,
        count: int = 1,
        block: int = 5000,
        priority_order: bool = True,
    ) -> list[dict[str, Any]]:
        cfg = ConsumerConfig(
            consumer_group=self.consumer_group,
            consumer_name=f"worker_{worker_id}",
            count=count,
            block_ms=block,
        )
        messages = self._run_async(
            self.broker.consume(cfg, priority_order=priority_order)
        )
        out = []
        for msg in messages:
            out.append(
                {
                    "message_id": msg.message_id,
                    "stream": msg.stream,
                    "alert": msg.envelope.payload,
                    "severity": msg.envelope.priority.value,
                    "raw_data": msg.raw_data,
                    "envelope": msg.envelope,
                }
            )
        return out

    def acknowledge(self, stream: str, message_id: str) -> bool:
        return self._run_async(self.broker.ack(stream, message_id, self.consumer_group))

    async def acknowledge_async(self, stream: str, message_id: str) -> bool:
        return await self.broker.ack(stream, message_id, self.consumer_group)

    def negative_acknowledge(
        self, stream: str, message_id: str, envelope: EventEnvelope, reason: str
    ) -> bool:
        return self._run_async(
            self.broker.nack(stream, message_id, self.consumer_group, envelope, reason)
        )

    def replay_failed_messages(
        self, target_priority: str = "medium", limit: int = 100
    ) -> int:
        target_stream = self.streams.get(target_priority, self.streams["medium"])
        return self._run_async(
            self.broker.replay_dlq("events:dlq", target_stream, limit=limit)
        )

    def process_delayed_queue(self, limit: int = 100) -> int:
        return self._run_async(self.broker.process_delayed_messages(limit=limit))

    def get_queue_stats(self) -> dict[str, dict[str, int | str]]:
        return self.broker.get_queue_stats()

    def health_check(self) -> dict[str, bool]:
        return self.broker.health_check()

    def _run_async(self, coro):
        try:
            loop = asyncio.get_running_loop()
            # For async contexts, callers should use async methods when available.
            # Keep compat by creating a task and waiting in a threadsafe way is not possible here,
            # so we fail loud and instruct migration.
            raise RuntimeError(
                "Cannot call sync queue API from an active event loop; use async queue APIs"
            )
        except RuntimeError as exc:
            if "active event loop" in str(exc):
                raise
            return asyncio.run(coro)


_mq_manager_instance: MessageQueueManager | None = None


def get_message_queue_manager(redis_url: str | None = None) -> MessageQueueManager:
    global _mq_manager_instance
    if _mq_manager_instance is None:
        _mq_manager_instance = MessageQueueManager(redis_url)
    return _mq_manager_instance
