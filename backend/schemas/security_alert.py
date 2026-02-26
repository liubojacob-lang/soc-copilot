"""
Schemas for Security Alert ingestion and management.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class SecurityAlertIngest(BaseModel):
    """Schema for receiving alerts from external security tools."""

    source: str = Field(..., description="Alert source (wazuh, snort, osquery, etc)")
    event_id: str = Field(..., description="Unique event ID from source system")
    timestamp: str = Field(..., description="Event timestamp (ISO 8601 format)")
    event_type: str = Field(..., description="Event type/category")
    severity: str = Field(..., description="Severity level (critical, high, medium, low, info)")
    title: str = Field(..., description="Alert title")
    description: Optional[str] = Field(None, description="Alert description")

    # Network information
    source_ip: Optional[str] = Field(None, description="Source IP address")
    destination_ip: Optional[str] = Field(None, description="Destination IP address")
    protocol: Optional[str] = Field(None, description="Network protocol")

    # Host/Agent information
    agent_name: Optional[str] = Field(None, description="Agent/hostname")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    agent_ip: Optional[str] = Field(None, description="Agent IP address")

    # Rule information
    rule_id: Optional[str] = Field(None, description="Rule ID that triggered")
    rule_level: Optional[int] = Field(None, description="Rule level/severity")
    rule_groups: List[str] = Field(default_factory=list, description="Rule groups/categories")
    rule_mitre: List[str] = Field(default_factory=list, description="MITRE ATT&CK tactics")

    # Log and location
    full_log: Optional[str] = Field(None, description="Full log message")
    location: Optional[str] = Field(None, description="Log file location")
    geoip: Optional[Dict[str, Any]] = Field(None, description="Geographic IP information")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Original raw alert data")

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
    description: Optional[str]
    source_ip: Optional[str]
    destination_ip: Optional[str]
    protocol: Optional[str]
    agent_name: Optional[str]
    agent_id: Optional[str]
    agent_ip: Optional[str]
    rule_id: Optional[str]
    rule_level: Optional[int]
    rule_groups: Optional[str]
    rule_mitre: Optional[str]
    status: str
    assigned_to: Optional[str]
    created_at: datetime
    event_timestamp: Optional[datetime]

    class Config:
        from_attributes = True


class SecurityAlertListResponse(BaseModel):
    """Schema for paginated alert list response."""

    total: int
    alerts: List[SecurityAlertResponse]
    page: int
    page_size: int


class SecurityAlertUpdate(BaseModel):
    """Schema for updating alert status and metadata."""

    status: Optional[str] = Field(None, description="New status (open, investigating, closed, false_positive)")
    assigned_to: Optional[str] = Field(None, description="User assigned to investigate")
    resolution: Optional[str] = Field(None, description="Resolution notes")


class SecurityAlertStats(BaseModel):
    """Schema for alert statistics."""

    total: int
    by_severity: Dict[str, int]
    by_status: Dict[str, int]
    by_source: Dict[str, int]
    last_24h: int
    last_7d: int
    last_30d: int
