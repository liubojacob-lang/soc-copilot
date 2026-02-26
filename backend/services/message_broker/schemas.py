"""Message broker schemas and contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EventPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class EventEnvelope(BaseModel):
    """Unified event envelope for all internal event traffic."""

    model_config = ConfigDict(extra="allow")

    event_id: str
    event_type: str
    source: str
    tenant_id: str = "default"
    priority: EventPriority = EventPriority.MEDIUM
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3


class BrokerMessage(BaseModel):
    """Delivery representation returned to consumers."""

    model_config = ConfigDict(extra="allow")

    message_id: str
    stream: str
    envelope: EventEnvelope
    raw_data: dict[str, Any] = Field(default_factory=dict)


class ConsumerConfig(BaseModel):
    """Consumer runtime settings."""

    model_config = ConfigDict(extra="allow")

    consumer_group: str = "soc_workers"
    consumer_name: str
    count: int = 10
    block_ms: int = 5000
    claim_idle_ms: int = 60_000


class PublishOptions(BaseModel):
    """Publish options for delayed delivery and retention."""

    model_config = ConfigDict(extra="allow")

    max_length: int = 10000
    delay_seconds: int = 0
    dlq_on_failure: bool = True
