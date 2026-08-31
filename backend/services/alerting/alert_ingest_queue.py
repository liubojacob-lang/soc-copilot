"""Alert ingest queue bridge.

Provides lightweight async helpers that enqueue alerts and playbook results
onto the message broker without coupling routers/services to broker internals.
"""

from __future__ import annotations

import logging
from typing import Any

from services.message_broker import (
    EventEnvelope,
    EventPriority,
    get_broker,
)

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────
#  alert ingest
# ──────────────────────────────────────────────────────────────────────────


async def ingest_alert(alert: dict[str, Any]) -> str | None:
    """Enqueue an alert for async processing (dedup, enrichment, notification).

    Used after AlertCRUDService.create_alert() succeeds.
    """
    broker = await get_broker()
    msg_id = await broker.publish(
        EventEnvelope(
            event_id=str(alert.get("id", "unknown")),
            event_type="alert.created",
            source=alert.get("source", "api"),
            priority=_severity_to_priority(alert.get("severity", "medium")),
            payload=alert,
            metadata={"channel": "rest"},
        )
    )
    if msg_id:
        logger.debug("Alert enqueued  id=%s queue_id=%s", alert.get("id"), msg_id)
    else:
        logger.warning("Failed to enqueue alert  id=%s", alert.get("id"))
    return msg_id


# ──────────────────────────────────────────────────────────────────────────
#  playbook results
# ──────────────────────────────────────────────────────────────────────────


async def ingest_playbook_result(result: dict[str, Any]) -> str | None:
    """Enqueue a playbook completion event.

    Called after a playbook run finishes (success/failure).
    """
    broker = await get_broker()
    run_id = result.get("run_id", "unknown")
    msg_id = await broker.publish(
        EventEnvelope(
            event_id=run_id,
            event_type="playbook.completed",
            source="playbook_engine",
            priority=EventPriority.MEDIUM,
            payload=result,
            metadata={
                "status": result.get("status", "unknown"),
                "playbook_name": result.get("playbook_name", ""),
            },
        )
    )
    if msg_id:
        logger.debug("Playbook result enqueued  run_id=%s queue_id=%s", run_id, msg_id)
    return msg_id


# ──────────────────────────────────────────────────────────────────────────
#  helpers
# ──────────────────────────────────────────────────────────────────────────


def _severity_to_priority(severity: str) -> EventPriority:
    _map = {
        "critical": EventPriority.CRITICAL,
        "high": EventPriority.HIGH,
        "medium": EventPriority.MEDIUM,
        "low": EventPriority.LOW,
    }
    return _map.get((severity or "medium").lower(), EventPriority.MEDIUM)
