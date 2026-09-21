"""Schemas for IOC hits."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class IOCType(str, Enum):
    """IOC types."""

    ip = "ip"
    domain = "domain"
    url = "url"
    hash = "hash"


class IOCSource(str, Enum):
    """IOC sources."""

    local = "local"
    llm = "llm"
    manual = "manual"


class IOCHitBase(BaseModel):
    """Base IOC hit schema."""

    history_id: str | None = Field(None, description="Associated history record ID")
    asset_id: str | None = Field(None, description="Associated asset ID")
    ioc_type: str = Field(..., description="IOC type")
    ioc_value: str = Field(..., description="IOC value")
    confidence: int = Field(default=60, ge=0, le=100, description="Confidence score")
    source: str = Field(..., description="IOC source")
    context_snippet: str | None = Field(None, description="Context snippet")
    notes: str | None = Field(None, description="Additional notes")


class IOCHitCreate(IOCHitBase):
    """Schema for creating an IOC hit."""

    pass


class IOCHitResponse(IOCHitBase):
    """Schema for IOC hit response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class IOCHitListRequest(BaseModel):
    """Schema for IOC hit list request."""

    ioc: str | None = Field(None, description="Filter by IOC value")
    limit: int = Field(default=100, ge=1, le=500, description="Maximum results")


class IOCHitListResponse(BaseModel):
    """Schema for IOC hit list response."""

    items: list[IOCHitResponse]
    total: int
