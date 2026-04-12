"""Schemas for timeline building."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from schemas.impact import ImpactAnalysis
from schemas.threat_intel import ThreatIntelAnalysis


class IOCsFinal(BaseModel):
    """Final merged IOCs."""

    model_config = ConfigDict(protected_namespaces=())

    ips: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    hashes: list[str] = Field(default_factory=list)


class IOCsLocal(BaseModel):
    """Local extracted IOCs."""

    model_config = ConfigDict(protected_namespaces=())

    ips: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    hashes: list[str] = Field(default_factory=list)


class IOCsLLM(BaseModel):
    """LLM extracted IOCs."""

    model_config = ConfigDict(protected_namespaces=())

    ips: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    urls: list[str] = Field(default_factory=list)
    hashes: list[str] = Field(default_factory=list)


class IOCCount(BaseModel):
    """IOC count statistics."""

    model_config = ConfigDict(protected_namespaces=())

    ips: int
    domains: int
    urls: int
    hashes: int
    total: int


class TimelineEvent(BaseModel):
    """A single timeline event."""

    timestamp: str
    type: str
    description: str
    key_fields: dict[str, Any]


class SuspiciousEvent(BaseModel):
    """A suspicious event with reasoning."""

    timestamp: str
    description: str
    reasoning: str
    severity: str


class TimelineRequest(BaseModel):
    """Request for timeline building."""

    raw_log: str = Field(..., description="Raw log content", min_length=1)
    log_type: str | None = Field(
        None, description="Log type: sysmon/windows/linux/nginx"
    )


class TimelineResponse(BaseModel):
    """Response from timeline building."""

    model_config = ConfigDict(protected_namespaces=())

    timeline: list[TimelineEvent]
    suspicious_top5: list[SuspiciousEvent]
    next_steps: list[str]

    # v0.2: IOC fields
    iocs: IOCsFinal
    iocs_local: IOCsLocal
    iocs_llm: IOCsLLM
    ioc_count: IOCCount

    # Metadata fields (v0.2)
    request_id: str | None = Field(None, description="Unique request ID for tracing")
    model_used: str | None = Field(None, description="AI model used")
    degraded: bool = Field(False, description="Whether degraded mode was used")
    error_reason: str | None = Field(None, description="Error reason if degraded")
    history_id: str | None = Field(
        None, description="History record ID for this timeline"
    )

    # Impact analysis (v0.3)
    impact_analysis: ImpactAnalysis = Field(..., description="Impact analysis result")

    # Threat intelligence (v0.4)
    threat_intel: ThreatIntelAnalysis = Field(
        ..., description="Threat intelligence analysis"
    )
