"""Wazuh event schemas (Pydantic v2)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WazuhWebhookRule(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int | str | None = None
    level: int | None = None
    description: str | None = None
    groups: list[str] | None = None


class WazuhWebhookAgent(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    name: str | None = None
    ip: str | None = None


class WazuhWebhookEvent(BaseModel):
    """Normalized webhook payload accepted from Wazuh."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    timestamp: datetime | None = None
    rule: WazuhWebhookRule | None = None
    agent: WazuhWebhookAgent | None = None
    full_log: str | None = None
    location: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)

    def resolved_timestamp(self) -> datetime:
        return self.timestamp or datetime.now(timezone.utc)
