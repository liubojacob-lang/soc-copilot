"""Redis Streams broker implementation with retries, DLQ and delayed queue."""

from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from typing import Any

import redis

from observability.metrics import (
    observe_queue_consume,
    observe_queue_dlq,
    observe_queue_retry,
    set_queue_lag,
)

from .base import MessageBroker
from .schemas import (
    BrokerMessage,
    ConsumerConfig,
    EventEnvelope,
    EventPriority,
    PublishOptions,
)

logger = logging.getLogger(__name__)


class RedisBroker(MessageBroker):
    """Redis Streams based broker with consumer groups and reliability patterns."""

    def __init__(self, redis_url: str, consumer_group: str = "soc_workers"):
        self.redis_client = redis.from_url(redis_url, decode_responses=False)
        self.consumer_group = consumer_group
        self.streams = {
            EventPriority.CRITICAL.value: "events:critical",
            EventPriority.HIGH.value: "events:high",
            EventPriority.MEDIUM.value: "events:medium",
            EventPriority.LOW.value: "events:low",
        }
        self.dlq_stream = "events:dlq"
        self.delayed_zset = "events:delayed"
        self.retry_stream = "events:retry"
        self._setup_streams()

    def _setup_streams(self) -> None:
        all_streams = list(self.streams.values()) + [self.dlq_stream, self.retry_stream]
        for stream in all_streams:
            try:
                self.redis_client.xgroup_create(
                    stream, self.consumer_group, id="0", mkstream=True
                )
            except redis.ResponseError as exc:
                if "BUSYGROUP" not in str(exc):
                    logger.error("Unable to create group on %s: %s", stream, exc)

    def _stream_for_priority(self, priority: str) -> str:
        return self.streams.get(priority, self.streams[EventPriority.MEDIUM.value])

    async def publish(
        self, envelope: EventEnvelope, options: PublishOptions | None = None
    ) -> str | None:
        options = options or PublishOptions()
        try:
            envelope.timestamp = envelope.timestamp or datetime.now(UTC)
            stream = self._stream_for_priority(envelope.priority.value)
            serialized = envelope.model_dump(mode="json")
            raw = json.dumps(serialized, ensure_ascii=False, default=str)

            if options.delay_seconds > 0:
                execute_at = int(time.time() + options.delay_seconds)
                delayed_payload = {
                    "target_stream": stream,
                    "envelope": raw,
                    "created_at": datetime.now(UTC).isoformat(),
                }
                delayed_id = self.redis_client.xadd(
                    "events:delayed:storage",
                    {"payload": json.dumps(delayed_payload, ensure_ascii=False)},
                    maxlen=options.max_length,
                )
                self.redis_client.zadd(self.delayed_zset, {delayed_id: execute_at})
                return (
                    delayed_id.decode()
                    if isinstance(delayed_id, bytes)
                    else str(delayed_id)
                )

            message_id = self.redis_client.xadd(
                stream,
                {
                    "envelope": raw,
                    "event_type": envelope.event_type,
                    "source": envelope.source,
                    "tenant_id": envelope.tenant_id,
                    "priority": envelope.priority.value,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                maxlen=options.max_length,
            )
            return (
                message_id.decode()
                if isinstance(message_id, bytes)
                else str(message_id)
            )
        except Exception as exc:
            logger.error("Redis publish failed: %s", exc)
            return None

    async def consume(
        self, config: ConsumerConfig, priority_order: bool = True
    ) -> list[BrokerMessage]:
        ordered = (
            ["critical", "high", "medium", "low"] if priority_order else ["medium"]
        )
        out: list[BrokerMessage] = []

        # reclaim idle pending messages first (failure replay)
        for stream in (self.streams[p] for p in ordered):
            out.extend(self._claim_idle_pending(stream, config))

        # then read fresh messages
        for stream in (self.streams[p] for p in ordered):
            try:
                result = self.redis_client.xreadgroup(
                    config.consumer_group,
                    config.consumer_name,
                    {stream: ">"},
                    count=config.count,
                    block=config.block_ms,
                )
                if not result:
                    continue
                for stream_name, messages in result:
                    stream_label = (
                        stream_name.decode()
                        if isinstance(stream_name, bytes)
                        else str(stream_name)
                    )
                    for message_id, data in messages:
                        consume_start = time.perf_counter()
                        parsed = self._decode_message(stream_name, message_id, data)
                        if parsed:
                            out.append(parsed)
                            observe_queue_consume(
                                stream_label,
                                config.consumer_group,
                                "success",
                                time.perf_counter() - consume_start,
                            )
                if out and priority_order:
                    break
            except Exception as exc:
                logger.error("Redis consume failed on %s: %s", stream, exc)
                observe_queue_consume(stream, config.consumer_group, "error")

        return out

    def _claim_idle_pending(
        self, stream: str, config: ConsumerConfig
    ) -> list[BrokerMessage]:
        claimed: list[BrokerMessage] = []
        try:
            pending = self.redis_client.xpending_range(
                stream,
                config.consumer_group,
                min="-",
                max="+",
                count=config.count,
                idle=config.claim_idle_ms,
            )
            ids = [item["message_id"] for item in pending] if pending else []
            if not ids:
                return claimed

            claimed_data = self.redis_client.xclaim(
                stream,
                config.consumer_group,
                config.consumer_name,
                min_idle_time=config.claim_idle_ms,
                message_ids=ids,
            )
            for msg_id, data in claimed_data:
                parsed = self._decode_message(stream, msg_id, data)
                if parsed:
                    claimed.append(parsed)
        except Exception as exc:
            logger.debug("Claim pending skipped for %s: %s", stream, exc)
        return claimed

    def _decode_message(
        self, stream: Any, message_id: Any, data: dict[bytes, bytes]
    ) -> BrokerMessage | None:
        try:
            raw = data.get(b"envelope", b"{}")
            envelope_payload = json.loads(raw.decode("utf-8"))
            envelope = EventEnvelope.model_validate(envelope_payload)
            stream_name = stream.decode() if isinstance(stream, bytes) else str(stream)
            msg_id = (
                message_id.decode()
                if isinstance(message_id, bytes)
                else str(message_id)
            )
            return BrokerMessage(
                message_id=msg_id,
                stream=stream_name,
                envelope=envelope,
                raw_data={
                    (k.decode() if isinstance(k, bytes) else str(k)): (
                        v.decode() if isinstance(v, bytes) else v
                    )
                    for k, v in data.items()
                },
            )
        except Exception as exc:
            logger.error("Message decode failed: %s", exc)
            return None

    async def ack(self, stream: str, message_id: str, consumer_group: str) -> bool:
        try:
            self.redis_client.xack(stream, consumer_group, message_id)
            return True
        except Exception as exc:
            logger.error("ACK failed for %s: %s", message_id, exc)
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

            self.redis_client.xack(stream, consumer_group, message_id)

            if envelope.retry_count > envelope.max_retries:
                return await self._push_to_dlq(envelope, reason)

            retry_delay = min(2**envelope.retry_count, 300)
            observe_queue_retry(stream)
            return bool(
                await self.publish(envelope, PublishOptions(delay_seconds=retry_delay))
            )
        except Exception as exc:
            logger.error("NACK failed for %s: %s", message_id, exc)
            return False

    async def _push_to_dlq(self, envelope: EventEnvelope, reason: str) -> bool:
        try:
            payload = envelope.model_dump(mode="json")
            payload["dlq_reason"] = reason
            payload["dlq_at"] = datetime.now(UTC).isoformat()
            self.redis_client.xadd(
                self.dlq_stream,
                {
                    "envelope": json.dumps(payload, ensure_ascii=False, default=str),
                    "event_type": envelope.event_type,
                    "source": envelope.source,
                },
            )
            observe_queue_dlq(self.dlq_stream)
            return True
        except Exception as exc:
            logger.error("DLQ push failed: %s", exc)
            return False

    async def replay_dlq(
        self, dlq_stream: str, target_stream: str, limit: int = 100
    ) -> int:
        replayed = 0
        try:
            msgs = self.redis_client.xrange(dlq_stream, min="-", max="+", count=limit)
            for message_id, data in msgs:
                envelope_raw = data.get(b"envelope", b"{}")
                envelope = EventEnvelope.model_validate(
                    json.loads(envelope_raw.decode("utf-8"))
                )
                envelope.retry_count = 0
                envelope.metadata["replayed_from_dlq"] = True
                envelope.priority = (
                    EventPriority(target_stream.split(":")[-1])
                    if target_stream.split(":")[-1] in self.streams
                    else EventPriority.MEDIUM
                )
                if await self.publish(envelope):
                    self.redis_client.xdel(dlq_stream, message_id)
                    replayed += 1
        except Exception as exc:
            logger.error("DLQ replay failed: %s", exc)
        return replayed

    async def process_delayed_messages(self, limit: int = 100) -> int:
        moved = 0
        now_ts = int(time.time())
        try:
            due_ids = self.redis_client.zrangebyscore(
                self.delayed_zset, "-inf", now_ts, start=0, num=limit
            )
            if not due_ids:
                return moved

            for delayed_id in due_ids:
                entries = self.redis_client.xrange(
                    "events:delayed:storage", min=delayed_id, max=delayed_id, count=1
                )
                if not entries:
                    self.redis_client.zrem(self.delayed_zset, delayed_id)
                    continue
                _, data = entries[0]
                payload_raw = data.get(b"payload", b"{}")
                payload = json.loads(payload_raw.decode("utf-8"))
                envelope = EventEnvelope.model_validate(json.loads(payload["envelope"]))
                if await self.publish(envelope):
                    self.redis_client.zrem(self.delayed_zset, delayed_id)
                    self.redis_client.xdel("events:delayed:storage", delayed_id)
                    moved += 1
        except Exception as exc:
            logger.error("Delayed processing failed: %s", exc)
        return moved

    def get_queue_stats(self) -> dict[str, dict[str, int | str]]:
        stats: dict[str, dict[str, int | str]] = {}
        for priority, stream in self.streams.items():
            pending = 0
            try:
                length = self.redis_client.xlen(stream)
                pendings = self.redis_client.xpending_range(
                    stream, self.consumer_group, min="-", max="+", count=100
                )
                pending = len(pendings or [])
                stats[priority] = {
                    "stream": stream,
                    "length": int(length),
                    "pending": int(pending),
                }
                set_queue_lag(stream, int(length))
            except Exception:
                stats[priority] = {"stream": stream, "length": -1, "pending": -1}

        try:
            stats["dlq"] = {
                "stream": self.dlq_stream,
                "length": int(self.redis_client.xlen(self.dlq_stream)),
                "pending": 0,
            }
            stats["delayed"] = {
                "stream": self.delayed_zset,
                "length": int(self.redis_client.zcard(self.delayed_zset)),
                "pending": 0,
            }
        except Exception:
            pass

        return stats

    def health_check(self) -> dict[str, bool]:
        health = {"redis": False, "streams": False}
        try:
            self.redis_client.ping()
            health["redis"] = True
            for stream in self.streams.values():
                self.redis_client.xinfo_stream(stream)
            health["streams"] = True
        except Exception:
            pass
        return health
