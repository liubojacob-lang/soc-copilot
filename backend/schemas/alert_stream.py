"""
Wazuh Real-time Alert Stream Schemas

Defines data models for real-time alert streaming via WebSocket.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class WazuhAgent(BaseModel):
    """Wazuh agent information."""

    id: str
    name: str
    ip: str | None = None
    status: str | None = None


class WazuhRule(BaseModel):
    """Wazuh rule information."""

    id: int
    level: int
    description: str
    groups: list[str] = Field(default_factory=list)
    mitre: dict[str, Any] | None = None


class MITRETactic(BaseModel):
    """MITRE ATT&CK tactic information."""

    id: str | None = None
    technique: str | None = None
    tactic: str | None = None


class WazuhAlertStream(BaseModel):
    """
    Real-time Wazuh alert for streaming.

    Optimized format for WebSocket transmission with enriched context.
    """

    # Core identifiers
    id: str = Field(..., description="Unique alert ID")
    timestamp: datetime = Field(..., description="Alert timestamp")
    source: str = Field(default="wazuh", description="Alert source")

    # Alert classification
    severity: SeverityLevel = Field(..., description="Alert severity")
    event_type: str = Field(..., description="Event type (e.g., ssh_login, malware)")
    title: str = Field(..., description="Alert title")

    # Wazuh specific data
    rule: WazuhRule = Field(..., description="Wazuh rule information")
    agent: WazuhAgent = Field(..., description="Wazuh agent information")
    full_log: str | None = Field(None, description="Full log message")
    location: str | None = Field(None, description="Log file location")

    # Enriched data
    mitre: MITRETactic | None = Field(None, description="MITRE ATT&CK mapping")
    iocs: list[str] = Field(default_factory=list, description="Extracted IOCs")
    source_ip: str | None = Field(None, description="Source IP address")
    dest_ip: str | None = Field(None, description="Destination IP address")
    username: str | None = Field(None, description="Username involved")

    # Analysis metadata
    analyzed: bool = Field(default=False, description="Whether AI analysis is complete")
    correlation_id: str | None = Field(None, description="Correlation group ID")
    risk_score: float | None = Field(
        None, description="Calculated risk score (0-100)"
    )

    # Processing metadata
    received_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When SOC Copilot received the alert",
    )
    processed_at: datetime | None = Field(
        None, description="When processing completed"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class WazuhStreamMessage(BaseModel):
    """
    WebSocket message format for Wazuh alert stream.
    """

    type: str = Field(..., description="Message type: alert, heartbeat, stats, error")
    data: dict[str, Any] = Field(..., description="Message payload")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Message timestamp"
    )
    channel: str = Field(default="wazuh", description="Channel name")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AlertStreamFilter(BaseModel):
    """
    Filter criteria for alert stream subscription.
    """

    min_severity: SeverityLevel | None = Field(
        None, description="Minimum severity level"
    )
    agent_ids: list[str] | None = Field(None, description="Filter by agent IDs")
    event_types: list[str] | None = Field(None, description="Filter by event types")
    source_ips: list[str] | None = Field(None, description="Filter by source IPs")
    has_mitre: bool | None = Field(
        None, description="Only alerts with MITRE mapping"
    )
    limit: int | None = Field(None, description="Max alerts to stream (0=unlimited)")


class AlertStreamStats(BaseModel):
    """
    Alert stream statistics.
    """

    total_alerts: int = Field(..., description="Total alerts streamed")
    alerts_by_severity: dict[str, int] = Field(
        default_factory=dict, description="Alerts grouped by severity"
    )
    alerts_by_event_type: dict[str, int] = Field(
        default_factory=dict, description="Alerts grouped by event type"
    )
    top_agents: list[dict[str, Any]] = Field(
        default_factory=list, description="Top alerting agents"
    )
    top_source_ips: list[dict[str, Any]] = Field(
        default_factory=list, description="Top source IPs"
    )
    stream_start_time: datetime = Field(..., description="When stream started")
    last_alert_time: datetime | None = Field(
        None, description="Last alert timestamp"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AlertAggregation(BaseModel):
    """
    Aggregated alert data for reducing noise.
    """

    aggregation_key: str = Field(..., description="Unique key for this aggregation")
    alert_count: int = Field(..., description="Number of alerts in aggregation")
    first_seen: datetime = Field(..., description="First alert timestamp")
    last_seen: datetime = Field(..., description="Last alert timestamp")
    severity: SeverityLevel = Field(..., description="Highest severity in group")
    sample_alert: WazuhAlertStream = Field(..., description="Sample alert from group")
    iocs: list[str] = Field(default_factory=list, description="All IOCs from group")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
