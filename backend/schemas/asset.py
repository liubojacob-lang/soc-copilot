"""Schemas for asset management."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from enum import Enum


class Criticality(str, Enum):
    """Asset criticality levels."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AssetBase(BaseModel):
    """Base asset schema."""

    hostname: Optional[str] = Field(None, description="Asset hostname")
    ip: Optional[str] = Field(None, description="Asset IP address")
    owner: Optional[str] = Field(None, description="Asset owner")
    business: Optional[str] = Field(None, description="Business unit")
    criticality: Criticality = Field(default=Criticality.medium, description="Asset criticality")
    tags: List[str] = Field(default_factory=list, description="Asset tags")
    notes: Optional[str] = Field(None, description="Additional notes")
    is_active: bool = Field(default=True, description="Whether asset is active")


class AssetCreate(AssetBase):
    """Schema for creating an asset."""

    pass


class AssetUpdate(BaseModel):
    """Schema for updating an asset."""

    hostname: Optional[str] = None
    ip: Optional[str] = None
    owner: Optional[str] = None
    business: Optional[str] = None
    criticality: Optional[Criticality] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class AssetResponse(AssetBase):
    """Schema for asset response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class AssetImportRequest(BaseModel):
    """Schema for bulk asset import."""

    assets: List[AssetCreate] = Field(..., description="List of assets to import")


class AssetImportResponse(BaseModel):
    """Schema for asset import response."""

    imported: int = Field(..., description="Number of assets imported")
    failed: int = Field(..., description="Number of assets failed to import")
    errors: List[str] = Field(default_factory=list, description="Error messages")


class AssetListRequest(BaseModel):
    """Schema for asset list request."""

    query: Optional[str] = Field(None, description="Search query")
    limit: int = Field(default=50, ge=1, le=500, description="Maximum results")


class AssetListResponse(BaseModel):
    """Schema for asset list response."""

    items: List[AssetResponse]
    total: int
