"""Schemas for alert analysis."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from schemas.impact import ImpactAnalysis
from schemas.threat_intel import ThreatIntelAnalysis


class EventType(str, Enum):
    """Security event types."""

    scan = "scan"
    bruteforce = "bruteforce"
    malware = "malware"
    c2 = "c2"
    phishing = "phishing"
    abnormal_login = "abnormal_login"
    lateral_movement = "lateral_movement"
    data_exfil = "data_exfil"
    unknown = "unknown"


class Severity(str, Enum):
    """Severity levels."""

    high = "high"
    medium = "medium"
    low = "low"


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


class Entities(BaseModel):
    """Extracted entities."""

    model_config = ConfigDict(protected_namespaces=())

    users: list[str] = Field(default_factory=list)
    hosts: list[str] = Field(default_factory=list)
    processes: list[str] = Field(default_factory=list)


class RecommendedAction(BaseModel):
    """A recommended action with verification."""

    action: str = Field(..., description="The action to take")
    priority: str = Field(..., description="Priority: high, medium, low")
    details: str = Field(default="", description="Detailed explanation")
    description: str | None = Field(
        default=None, description="Alias for details for frontend compatibility"
    )
    verification: str = Field(
        default="", description="How to verify the action was effective"
    )
    automated: bool = Field(
        default=False, description="Whether action can be automated"
    )

    model_config = ConfigDict(protected_namespaces=())

    def model_post_init(self, __context: object) -> None:
        if not self.description and self.details:
            self.description = self.details
        elif not self.details and self.description:
            self.details = self.description


class AlertAnalysisRequest(BaseModel):
    """Request for alert analysis."""

    raw_log: str | None = Field(
        None, description="Raw alert/log content", max_length=50000
    )
    title: str | None = Field(None, description="Alert title")
    description: str | None = Field(None, description="Alert description")
    source: str | None = Field(None, description="Alert source")
    severity: str | None = Field(None, description="Alert severity")


class AlertAnalysisResponse(BaseModel):
    """Response from alert analysis."""

    model_config = ConfigDict(protected_namespaces=())

    # Analysis results
    event_type: EventType
    severity: Severity
    attack_pattern: str | None = Field(
        None, description="Identified attack pattern or technique"
    )
    iocs: IOCsFinal
    iocs_local: IOCsLocal
    iocs_llm: IOCsLLM
    ioc_count: IOCCount
    entities: Entities
    summary: str
    evidence_points: list[str]
    recommended_actions: list[RecommendedAction]
    escalation_needed: bool
    confidence: int = Field(ge=0, le=100)

    # Metadata fields (v0.2)
    request_id: str | None = Field(None, description="Unique request ID for tracing")
    model_used: str | None = Field(None, description="AI model used")
    degraded: bool = Field(False, description="Whether degraded mode was used")
    error_reason: str | None = Field(None, description="Error reason if degraded")
    history_id: str | None = Field(
        None, description="History record ID for this analysis"
    )

    # Impact analysis (v0.3)
    impact_analysis: ImpactAnalysis = Field(..., description="Impact analysis result")

    # Threat intelligence (v0.4)
    threat_intel: ThreatIntelAnalysis = Field(
        ..., description="Threat intelligence analysis"
    )
