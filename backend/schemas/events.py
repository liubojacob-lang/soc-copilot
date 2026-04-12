"""Unified event schemas for internal event-driven pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventIngestRequest(BaseModel):
    """Raw inbound event from external integrations."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    source: str
    event_type: str
    severity: str = "medium"
    tenant_id: str = "default"
    payload: dict[str, Any] = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class EventIngestResponse(BaseModel):
    accepted: bool
    broker_message_id: str | None = None
    event_id: str
    route: str
