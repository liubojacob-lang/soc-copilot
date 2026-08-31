"""
Alert CRUD Schemas

Provides request/response schemas for alert CRUD operations and triage workflow.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AlertStatus(str, Enum):
    """Alert triage workflow states."""

    NEW = "new"
    TRIAGED = "triaged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    REOPENED = "reopened"


class AlertSeverity(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertSource(str, Enum):
    """Supported alert sources."""

    WAZUH = "wazuh"
    SNORT = "snort"
    OSQUERY = "osquery"
    SURICATA = "suricata"
    CROWDSTRIKE = "crowdstrike"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class AlertCreate(BaseModel):
    """Schema for creating a new alert manually."""

    tenant_id: str = Field(default="default", max_length=64)
    source: str = Field(..., max_length=50, description="Alert source: wazuh, snort, osquery, etc.")
    external_event_id: str | None = Field(None, max_length=255)
    event_type: str = Field(..., max_length=100, description="Event type: malware, bruteforce, etc.")
    severity: str = Field(..., max_length=20, description="critical, high, medium, low, info")
    title: str = Field(..., min_length=1)
    description: str | None = None
    source_ip: str | None = Field(None, max_length=50)
    destination_ip: str | None = Field(None, max_length=50)
    protocol: str | None = Field(None, max_length=20)
    agent_name: str | None = Field(None, max_length=255)
    agent_id: str | None = Field(None, max_length=50)
    agent_ip: str | None = Field(None, max_length=50)
    rule_id: str | None = Field(None, max_length=100)
    rule_level: int | None = None
    rule_groups: list[str] | None = None
    rule_mitre: list[str] | None = None
    full_log: str | None = None
    location: str | None = Field(None, max_length=500)
    geoip: dict[str, Any] | None = None
    raw_data: dict[str, Any] | None = None
    tags: list[str] | None = None
    threat_score: int | None = Field(None, ge=0, le=100)
    iocs: dict[str, Any] | None = None
    mitre_tactics: list[str] | None = None
    mitre_techniques: list[str] | None = None
    classification: str | None = Field(None, max_length=50)


class AlertUpdate(BaseModel):
    """Schema for updating an existing alert.  All fields are optional."""

    title: str | None = None
    description: str | None = None
    severity: str | None = Field(None, max_length=20)
    source_ip: str | None = Field(None, max_length=50)
    destination_ip: str | None = Field(None, max_length=50)
    protocol: str | None = Field(None, max_length=20)
    agent_name: str | None = Field(None, max_length=255)
    agent_id: str | None = Field(None, max_length=50)
    agent_ip: str | None = Field(None, max_length=50)
    rule_id: str | None = Field(None, max_length=100)
    rule_level: int | None = None
    rule_groups: list[str] | None = None
    rule_mitre: list[str] | None = None
    full_log: str | None = None
    location: str | None = Field(None, max_length=500)
    geoip: dict[str, Any] | None = None
    raw_data: dict[str, Any] | None = None
    tags: list[str] | None = None
    assigned_to: str | None = Field(None, max_length=255)
    resolution_note: str | None = None
    root_cause: str | None = None
    remediation: str | None = None
    threat_score: int | None = Field(None, ge=0, le=100)
    iocs: dict[str, Any] | None = None
    mitre_tactics: list[str] | None = None
    mitre_techniques: list[str] | None = None
    classification: str | None = Field(None, max_length=50)


class AlertFilter(BaseModel):
    """Schema for filtering and searching alerts."""

    status: str | None = Field(None, description="Filter by alert status")
    severity: str | None = Field(None, description="Filter by severity level")
    source: str | None = Field(None, description="Filter by alert source")
    event_type: str | None = Field(None, description="Filter by event type")
    agent_name: str | None = Field(None, description="Filter by agent name")
    source_ip: str | None = Field(None, description="Filter by source IP")
    assigned_to: str | None = Field(None, description="Filter by assigned user")
    search: str | None = Field(None, description="Search in title, description, source_ip, full_log")
    created_from: datetime | None = Field(None, description="Created after (UTC)")
    created_to: datetime | None = Field(None, description="Created before (UTC)")
    tenant_id: str | None = Field(None, description="Filter by tenant (admin only)")


class AlertTriageRequest(BaseModel):
    """Schema for requesting a status change (triage step)."""

    new_status: AlertStatus = Field(..., description="Target alert status")
    resolution_note: str | None = Field(None, description="Optional resolution note")
    root_cause: str | None = Field(None, description="Optional root cause analysis")


class BatchStatusUpdate(BaseModel):
    """Schema for batch status updates."""

    alert_ids: list[int] = Field(..., min_length=1, max_length=500)
    new_status: AlertStatus = Field(..., description="Target status for all alerts")
    resolution_note: str | None = Field(None, description="Common resolution note")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class AlertResponse(BaseModel):
    """Unified alert response schema."""

    model_config = {"from_attributes": True}

    id: int
    tenant_id: str
    source: str
    external_event_id: str | None = None
    event_type: str
    severity: str
    title: str
    description: str | None = None
    source_ip: str | None = None
    destination_ip: str | None = None
    protocol: str | None = None
    agent_name: str | None = None
    agent_id: str | None = None
    agent_ip: str | None = None
    rule_id: str | None = None
    rule_level: int | None = None
    rule_groups: str | None = None
    rule_mitre: str | None = None
    full_log: str | None = None
    location: str | None = None
    geoip: dict[str, Any] | None = None
    raw_data: dict[str, Any] | None = None
    tags: list[str] | None = None
    classification: str | None = None
    fingerprint: str | None = None
    aggregated_count: int = 1
    last_seen_at: datetime | None = None
    status: str = "new"
    assigned_to: str | None = None
    assigned_at: datetime | None = None
    resolution_note: str | None = None
    root_cause: str | None = None
    remediation: str | None = None
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    escalated_to: str | None = None
    escalated_at: datetime | None = None
    escalation_reason: str | None = None
    threat_score: int | None = None
    enriched_at: datetime | None = None
    iocs: dict[str, Any] | None = None
    mitre_tactics: list[str] | None = None
    mitre_techniques: list[str] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    event_timestamp: datetime | None = None


class AlertStats(BaseModel):
    """Alert statistics summary."""

    total: int = 0
    by_status: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_source: dict[str, int] = Field(default_factory=dict)
    last_24h: int = 0
    last_7d: int = 0
    last_30d: int = 0


class AlertTriageResponse(BaseModel):
    """Response after a triage status change."""

    alert_id: int
    old_status: str
    new_status: str
    changed_by: str
    changed_at: datetime
    resolution_note: str | None = None

# ── v0.9.0 Batch Alert Update (comprehensive) ─────────────────────

class BatchAlertUpdateItem(BaseModel):
    """Single item in batch alert update."""

    alert_id: int = Field(..., description="Alert ID to update")
    severity: str | None = Field(None, max_length=20, description="New severity")
    status: AlertStatus | None = Field(None, description="New status")
    assigned_to: str | None = Field(None, max_length=255, description="Assign to user")
    resolution_note: str | None = Field(None, description="Resolution note")


class BatchAlertUpdate(BaseModel):
    """Schema for comprehensive batch alert updates."""

    items: list[BatchAlertUpdateItem] = Field(
        ..., min_length=1, max_length=200, description="Alert updates (1-200)"
    )


class BatchAlertUpdateResponse(BaseModel):
    """Response for batch alert update."""

    total: int = Field(..., description="Total items submitted")
    success_count: int = Field(..., description="Number of successful updates")
    failed_count: int = Field(..., description="Number of failed updates")
    errors: list[dict] = Field(
        default_factory=list,
        description="Error details for failed items [{alert_id, error}]",
    )
