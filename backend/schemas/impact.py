"""Schemas for impact analysis."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from enum import Enum


class Severity(str, Enum):
    """Impact severity levels."""

    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AffectedAsset(BaseModel):
    """Affected asset information."""

    asset_id: str = Field(..., description="Asset ID")
    hostname: Optional[str] = Field(None, description="Asset hostname")
    ip: Optional[str] = Field(None, description="Asset IP")
    criticality: str = Field(..., description="Asset criticality")
    reason: str = Field(..., description="Reason for impact")


class ContainmentPriority(BaseModel):
    """Containment priority information."""

    asset_id: str = Field(..., description="Asset ID")
    priority: int = Field(..., ge=1, le=10, description="Priority level (1-10)")
    reason: str = Field(..., description="Reason for priority")


class ImpactAnalysis(BaseModel):
    """Impact analysis result."""

    affected_assets: List[AffectedAsset] = Field(default_factory=list)
    business_impact: str = Field(..., description="Business impact description")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    severity: Severity = Field(..., description="Impact severity")
    containment_priority: List[ContainmentPriority] = Field(default_factory=list)
    recommended_next_queries: List[str] = Field(default_factory=list)


class DegradedImpactAnalysis(BaseModel):
    """Degraded mode impact analysis (minimal valid response)."""

    affected_assets: List[AffectedAsset] = Field(default_factory=list)
    business_impact: str = "Unable to perform impact analysis in degraded mode"
    risk_score: int = Field(default=0, ge=0, le=100)
    severity: Severity = Field(default=Severity.low)
    containment_priority: List[ContainmentPriority] = Field(default_factory=list)
    recommended_next_queries: List[str] = Field(default_factory=list)
