"""In-memory broker fallback using collections.deque.

Used when Redis is unavailable. Not durable — messages are lost on restart.
Provides identical MessageBroker interface for graceful degradation.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime
from typing import Any

from .base import MessageBroker
from .schemas import (
    BrokerMessage,
    ConsumerConfig,
    EventEnvelope,
    EventPriority,
    PublishOptions,
)

logger = logging.getLogger(__name__)


class MemoryBroker(MessageBroker):
    """Non-durable in-memory broker. Same interface, zero external deps.

    Keeps all state in-process. Messages survive only while the process lives.
    Suitable as a silent fallback when Redis/Kafka are unreachable.
    """

    # Class-level shared state so multiple singleton refs see same queues
    _queues: dict[str, deque[tuple[str, EventEnvelope]]] = defaultdict(deque)
    _pending: dict[
        str, dict[str, list[str]]
    ] = defaultdict(lambda: defaultdict(list))

    def __init__(self) -> None:
        self._delayed: list[tuple[float, str, EventEnvelope]] = []
        self._dlq: deque[tuple[str, EventEnvelope, str]] = deque()

    # ──────────────────────────────────────────────────────────────────
    #  publish
    # ──────────────────────────────────────────────────────────────────

    async def publish(
        self, envelope: EventEnvelope, options: PublishOptions | None = None
    ) -> str | None:
        options = options or PublishOptions()
        try:
            envelope.timestamp = envelope.timestamp or datetime.now(UTC)
            msg_id = str(uuid.uuid4())

            if options.delay_seconds > 0:
                execute_at = time.time() + options.delay_seconds
                self._delayed.append((execute_at, msg_id, envelope))
                asyncio.create_task(
                    self._schedule_delayed(msg_id, options.delay_seconds)
                )
                return msg_id

            stream = _resolve_stream(envelope.priority.value)
            self._queues[stream].append((msg_id, envelope))
            return msg_id
        except Exception as exc:
            logger.error("Memory publish failed: %s", exc)
            return None

    async def _schedule_delayed(self, msg_id: str, delay_s: float) -> None:
        await asyncio.sleep(delay_s)
        for i, (_, mid, env) in enumerate(self._delayed):
            if mid == msg_id:
                stream = _resolve_stream(env.priority.value)
                self._queues[stream].append((mid, env))
                self._delayed.pop(i)
                break

    # ──────────────────────────────────────────────────────────────────
    #  consume
    # ──────────────────────────────────────────────────────────────────

    async def consume(
        self, config: ConsumerConfig, priority_order: bool = True
    ) -> list[BrokerMessage]:
        ordered = (
            ["critical", "high", "medium", "low"] if priority_order else ["medium"]
        )
        out: list[BrokerMessage] = []

        for priority in ordered:
            stream = _resolve_stream(priority)
            q = self._queues.get(stream)
            if not q:
                continue

            taken: list[tuple[str, EventEnvelope]] = []
            while q and len(taken) < config.count:
                taken.append(q.popleft())

            for msg_id, envelope in taken:
                self._pending[config.consumer_group][
                    config.consumer_name
                ].append(msg_id)
                out.append(
                    BrokerMessage(
                        message_id=msg_id,
                        stream=stream,
                        envelope=envelope,
                        raw_data={"priority": priority},
                    )
                )

            if out and priority_order:
                break

        return out

    # ──────────────────────────────────────────────────────────────────
    #  ack / nack
    # ──────────────────────────────────────────────────────────────────

    async def ack(
        self, stream: str, message_id: str, consumer_group: str
    ) -> bool:
        try:
            for name, ids in self._pending.get(consumer_group, {}).items():
                if message_id in ids:
                    ids.remove(message_id)
                    return True
            return False
        except Exception:
            return False

    async def nack(
        self,
        stream: str,
        message_id: str,
        consumer_group: str,
        envelope: EventEnvelope,
        reason: str,
    ) -> bool:
        try:
            envelope.retry_count += 1
            envelope.metadata["last_error"] = reason
            envelope.metadata["failed_at"] = datetime.now(UTC).isoformat()

            if envelope.retry_count > envelope.max_retries:
                self._dlq.append((message_id, envelope, reason))
                logger.info(
                    "Memory DLQ enqueued msg=%s reason=%s", message_id, reason
                )
                return True

            delay = min(2 ** envelope.retry_count, 300)
            asyncio.create_task(
                self._requeue_after(message_id, envelope, delay)
            )
            return True
        except Exception as exc:
            logger.error("Memory nack failed: %s", exc)
            return False

    async def _requeue_after(
        self, msg_id: str, envelope: EventEnvelope, delay_s: float
    ) -> None:
        await asyncio.sleep(delay_s)
        stream = _resolve_stream(envelope.priority.value)
        self._queues[stream].append((msg_id, envelope))

    # ──────────────────────────────────────────────────────────────────
    #  dlq / delayed
    # ──────────────────────────────────────────────────────────────────

    async def replay_dlq(
        self, dlq_stream: str, target_stream: str, limit: int = 100
    ) -> int:
        replayed = 0
        while self._dlq and replayed < limit:
            msg_id, envelope, _ = self._dlq.popleft()
            envelope.retry_count = 0
            envelope.metadata["replayed_from_dlq"] = True
            stream = _resolve_stream(envelope.priority.value)
            self._queues[stream].append((msg_id, envelope))
            replayed += 1
        return replayed

    async def process_delayed_messages(self, limit: int = 100) -> int:
        now = time.time()
        moved = 0
        due: list[tuple[str, EventEnvelope]] = []
        remaining: list[tuple[float, str, EventEnvelope]] = []
        for ts, mid, env in self._delayed:
            if ts <= now and moved < limit:
                due.append((mid, env))
                moved += 1
            else:
                remaining.append((ts, mid, env))
        self._delayed = remaining
        for mid, env in due:
            stream = _resolve_stream(env.priority.value)
            self._queues[stream].append((mid, env))
        return moved

    # ──────────────────────────────────────────────────────────────────
    #  stats / health
    # ──────────────────────────────────────────────────────────────────

    def get_queue_stats(self) -> dict[str, dict[str, int | str]]:
        stats: dict[str, dict[str, int | str]] = {}
        for priority in ("critical", "high", "medium", "low"):
            stream = _resolve_stream(priority)
            stats[priority] = {
                "stream": stream,
                "length": len(self._queues.get(stream, deque())),
                "pending": 0,
            }
        stats["dlq"] = {
            "stream": "memory:dlq",
            "length": len(self._dlq),
            "pending": 0,
        }
        stats["delayed"] = {
            "stream": "memory:delayed",
            "length": len(self._delayed),
            "pending": 0,
        }
        return stats

    def health_check(self) -> dict[str, bool]:
        return {"memory": True, "streams": True}


def _resolve_stream(priority: str) -> str:
    allowed = {"critical", "high", "medium", "low"}
    return f"events:{priority if priority in allowed else 'medium'}"
