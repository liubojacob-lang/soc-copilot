#!/usr/bin/env python3
"""Alert Consumer — Redis Streams → AlertCRUDService.

Lightweight async worker that pulls from ``alerts:ingest`` via the
unified broker, creates/updates alerts through AlertCRUDService,
and acknowledges messages.

Standalone usage::

    python workers/alert_consumer.py [worker_id]

Environment:
    WORKER_ID          worker instance id (default "1")
    QUEUE_BACKEND      redis | kafka | memory    (default: redis)
    REDIS_URL          redis://host:port/db      (default: redis://redis:6379/0)
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.session import AsyncSessionLocal
from schemas.alert_schema import AlertCreate
from services.alert_crud_service import AlertCRUDService
from services.message_broker import (
    ConsumerConfig,
    EventEnvelope,
    get_broker,
)

logger = logging.getLogger("alert_consumer")


class AlertConsumer:
    """Consumes ``alerts:ingest`` stream and persists alerts via CRUD."""

    STREAM = "alerts:ingest"
    GROUP = "alert-workers"

    def __init__(self, consumer_id: str) -> None:
        self.consumer_id = consumer_id
        self.running = True
        self.stats = Stats()

    async def run(self) -> None:
        broker = await get_broker()
        logger.info(
            "AlertConsumer %s starting on stream=%s", self.consumer_id, self.STREAM
        )
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

        stats_task = asyncio.create_task(self._report_stats(broker))

        try:
            while self.running:
                config = ConsumerConfig(
                    consumer_group=self.GROUP,
                    consumer_name=self.consumer_id,
                    count=10,
                    block_ms=5000,
                )
                messages = await broker.consume(config, priority_order=False)
                if not messages:
                    continue

                for msg in messages:
                    try:
                        await self._handle(msg, broker)
                    except Exception:
                        logger.exception("Handler failed msg_id=%s", msg.message_id)

                await asyncio.sleep(0.1)  # tiny back-pressure valve
        finally:
            self.running = False
            stats_task.cancel()
            logger.info(
                "AlertConsumer %s shut down — processed=%d errors=%d",
                self.consumer_id,
                self.stats.processed,
                self.stats.errors,
            )

    async def _handle(self, msg: Any, broker: Any) -> None:
        envelope: EventEnvelope = msg.envelope
        payload: dict[str, Any] = envelope.payload or {}

        try:
            logger.info(
                "→ alert_consumer msg_id=%s event_id=%s severity=%s",
                msg.message_id,
                envelope.event_id,
                envelope.priority.value,
            )

            # Build AlertCreate from payload
            alert_data = AlertCreate(
                title=payload.get("title", "Queued Alert"),
                source=payload.get("source", envelope.source),
                severity=payload.get("severity", "medium"),
                description=payload.get("description", ""),
                rule_groups=payload.get("rule_groups"),
                rule_mitre=payload.get("rule_mitre"),
                tags=payload.get("tags"),
                mitre_tactics=payload.get("mitre_tactics"),
                mitre_techniques=payload.get("mitre_techniques"),
                iocs=payload.get("iocs"),
                external_event_id=payload.get("external_event_id"),
            )

            async with AsyncSessionLocal() as session:
                svc = AlertCRUDService(session=session)
                alert = await svc.create_alert(
                    alert_data, created_by=payload.get("created_by")
                )
                await svc.commit()
                logger.info(
                    "  ✓ persisted alert_id=%s title=%s",
                    getattr(alert, "id", "?"),
                    payload.get("title", ""),
                )

            await broker.ack(msg.stream, msg.message_id, self.GROUP)
            self.stats.processed += 1

        except Exception:
            self.stats.errors += 1
            reason = str(sys.exc_info()[1])
            await broker.nack(
                msg.stream,
                msg.message_id,
                self.GROUP,
                envelope,
                reason,
            )
            raise

    async def _report_stats(self, broker: Any) -> None:
        while self.running:
            await asyncio.sleep(60)
            if self.stats.processed == 0:
                continue
            qs = broker.get_queue_stats()
            lag = qs.get("medium", {}).get("length", "?")  # type: ignore[union-attr]
            logger.info(
                "📊 alert_consumer %s — processed=%d errors=%d queue_lag≈%s",
                self.consumer_id,
                self.stats.processed,
                self.stats.errors,
                lag,
            )

    def _shutdown(self, signum: int, frame: Any) -> None:
        logger.info("Received signal %d — shutting down gracefully", signum)
        self.running = False


class Stats:
    processed: int = 0
    errors: int = 0


# ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    worker_id = os.getenv("WORKER_ID", sys.argv[1] if len(sys.argv) > 1 else "1")
    consumer = AlertConsumer(f"alert-consumer-{worker_id}")
    await consumer.run()


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s  %(name)-16s %(levelname)s  %(message)s",
    )
    asyncio.run(main())
