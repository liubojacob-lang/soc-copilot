"""Schemas for blocked IP API."""

from datetime import datetime

from pydantic import BaseModel, Field


class BlockedIPBase(BaseModel):
    """Base blocked IP schema."""

    value: str = Field(..., description="IP address or domain to block")
    type: str = Field(default="ip", description="Type: ip, domain, url, hash")
    reason: str | None = Field(None, description="Reason for blocking")
    alert_id: str | None = Field(None, description="Related alert ID")
    expires_at: datetime | None = Field(None, description="Expiration time")


class BlockedIPCreate(BlockedIPBase):
    """Schema for creating a blocked IP."""

    pass


class BlockedIPUpdate(BaseModel):
    """Schema for updating a blocked IP."""

    reason: str | None = None
    is_active: bool | None = None
    expires_at: datetime | None = None


class BlockedIPResponse(BlockedIPBase):
    """Schema for blocked IP response."""

    id: str
    source: str
    created_by: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deactivated_at: datetime | None
    deactivated_by: str | None

    class Config:
        from_attributes = True


class BlockedIPListResponse(BaseModel):
    """Schema for blocked IP list response."""

    items: list[BlockedIPResponse]
    total: int


class BlockIPRequest(BaseModel):
    """Request to block an IP from threat source."""

    value: str = Field(..., description="IP or domain to block")
    type: str = Field(default="ip", description="Type of indicator")
    reason: str = Field(..., description="Reason for blocking")
    alert_id: str | None = Field(None, description="Related alert ID")
    expires_in_hours: int | None = Field(
        default=168, description="Hours until expiration (default 7 days)"
    )
