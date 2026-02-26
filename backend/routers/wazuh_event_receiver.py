"""Event-driven Wazuh webhook router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from schemas.events import EventIngestResponse
from services.wazuh_event_receiver import get_wazuh_event_receiver

router = APIRouter(prefix="/api/v1/wazuh/events", tags=["Wazuh Event Receiver"])


@router.post("/webhook", response_model=EventIngestResponse)
async def receive_wazuh_webhook(request: Request) -> EventIngestResponse:
    """Receive Wazuh webhook and forward to unified event bus."""
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON payload: {exc}")

    tenant_id = request.headers.get("x-tenant-id", "default")
    source_ip = request.client.host if request.client else None

    receiver = get_wazuh_event_receiver()
    result = await receiver.ingest_webhook_event(payload, tenant_id=tenant_id, source_ip=source_ip)

    return EventIngestResponse(
        accepted=result["accepted"],
        broker_message_id=result.get("broker_message_id"),
        event_id=result["event_id"],
        route="wazuh-webhook->event-bus",
    )
