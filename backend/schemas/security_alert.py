"""
Schemas for Security Alert ingestion and management.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SecurityAlertIngest(BaseModel):
    """Schema for receiving alerts from external security tools."""

    source: str = Field(..., description="Alert source (wazuh, snort, osquery, etc)")
    event_id: str = Field(..., description="Unique event ID from source system")
    timestamp: str = Field(..., description="Event timestamp (ISO 8601 format)")
    event_type: str = Field(..., description="Event type/category")
    severity: str = Field(
        ..., description="Severity level (critical, high, medium, low, info)"
    )
    title: str = Field(..., description="Alert title")
    description: str | None = Field(None, description="Alert description")

    # Network information
    source_ip: str | None = Field(None, description="Source IP address")
    destination_ip: str | None = Field(None, description="Destination IP address")
    protocol: str | None = Field(None, description="Network protocol")

    # Host/Agent information
    agent_name: str | None = Field(None, description="Agent/hostname")
    agent_id: str | None = Field(None, description="Agent ID")
    agent_ip: str | None = Field(None, description="Agent IP address")

    # Rule information
    rule_id: str | None = Field(None, description="Rule ID that triggered")
    rule_level: int | None = Field(None, description="Rule level/severity")
    rule_groups: list[str] = Field(
        default_factory=list, description="Rule groups/categories"
    )
    rule_mitre: list[str] = Field(
        default_factory=list, description="MITRE ATT&CK tactics"
    )

    # Log and location
    full_log: str | None = Field(None, description="Full log message")
    location: str | None = Field(None, description="Log file location")
    geoip: dict[str, Any] | None = Field(
        None, description="Geographic IP information"
    )
    raw_data: dict[str, Any] | None = Field(
        None, description="Original raw alert data"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source": "wazuh",
                "event_id": "1677834400-12345",
                "timestamp": "2026-02-24T10:00:00Z",
                "event_type": "web_attack",
                "severity": "high",
                "title": "SQL Injection Attempt",
                "description": "SQL injection pattern detected in web request",
                "source_ip": "192.168.1.100",
                "destination_ip": "10.0.0.5",
                "protocol": "TCP",
                "agent_name": "web-server-01",
                "agent_id": "001",
                "rule_id": "31101",
                "rule_level": 12,
                "rule_groups": ["web", "web_attack"],
                "rule_mitre": ["TA0001", "initial-access"],
            }
        }


class SecurityAlertResponse(BaseModel):
    """Schema for alert response."""

    id: int
    source: str
    external_event_id: str
    event_type: str
    severity: str
    title: str
    description: str | None
    source_ip: str | None
    destination_ip: str | None
    protocol: str | None
    agent_name: str | None
    agent_id: str | None
    agent_ip: str | None
    rule_id: str | None
    rule_level: int | None
    rule_groups: str | None
    rule_mitre: str | None
    status: str
    assigned_to: str | None
    created_at: datetime
    event_timestamp: datetime | None

    class Config:
        from_attributes = True


class SecurityAlertListResponse(BaseModel):
    """Schema for paginated alert list response."""

    total: int
    alerts: list[SecurityAlertResponse]
    page: int
    page_size: int


class SecurityAlertUpdate(BaseModel):
    """Schema for updating alert status and metadata."""

    status: str | None = Field(
        None, description="New status (open, investigating, closed, false_positive)"
    )
    assigned_to: str | None = Field(None, description="User assigned to investigate")
    resolution: str | None = Field(None, description="Resolution notes")


class SecurityAlertStats(BaseModel):
    """Schema for alert statistics."""

    total: int
    by_severity: dict[str, int]
    by_status: dict[str, int]
    by_source: dict[str, int]
    last_24h: int
    last_7d: int
    last_30d: int
