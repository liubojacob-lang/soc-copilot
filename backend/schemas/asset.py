"""Schemas for asset management."""

import ipaddress
import re
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

_HOSTNAME_RE = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)


class Criticality(str, Enum):
    """Asset criticality levels."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AssetBase(BaseModel):
    """Base asset schema."""

    hostname: str | None = Field(None, description="Asset hostname")
    ip: str | None = Field(None, description="Asset IP address")
    owner: str | None = Field(None, description="Asset owner")
    business: str | None = Field(None, description="Business unit")
    criticality: Criticality = Field(
        default=Criticality.medium, description="Asset criticality"
    )
    tags: list[str] = Field(default_factory=list, description="Asset tags")
    notes: str | None = Field(None, description="Additional notes")
    is_active: bool = Field(default=True, description="Whether asset is active")

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid IP address format: {v}") from None
        return v

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) > 253 or not _HOSTNAME_RE.match(v):
            raise ValueError(f"Invalid hostname format: {v}")
        return v


class AssetCreate(AssetBase):
    """Schema for creating an asset."""

    pass


class AssetUpdate(BaseModel):
    """Schema for updating an asset."""

    hostname: str | None = None
    ip: str | None = None
    owner: str | None = None
    business: str | None = None
    criticality: Criticality | None = None
    tags: list[str] | None = None
    notes: str | None = None
    is_active: bool | None = None

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"Invalid IP address format: {v}") from None
        return v

    @field_validator("hostname")
    @classmethod
    def validate_hostname(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if len(v) > 253 or not _HOSTNAME_RE.match(v):
            raise ValueError(f"Invalid hostname format: {v}")
        return v


class AssetResponse(AssetBase):
    """Schema for asset response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class AssetImportRequest(BaseModel):
    """Schema for bulk asset import."""

    assets: list[AssetCreate] = Field(..., description="List of assets to import")


class AssetImportResponse(BaseModel):
    """Schema for asset import response."""

    imported: int = Field(..., description="Number of assets imported")
    failed: int = Field(..., description="Number of assets failed to import")
    errors: list[str] = Field(default_factory=list, description="Error messages")


class AssetListRequest(BaseModel):
    """Schema for asset list request."""

    query: str | None = Field(None, description="Search query")
    limit: int = Field(default=50, ge=1, le=500, description="Maximum results")


class AssetListResponse(BaseModel):
    """Schema for asset list response."""

    items: list[AssetResponse]
    total: int
