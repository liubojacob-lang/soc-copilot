"""
Security Alert data model for ingested alerts from external security tools.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from db.session import Base

Base = Base


class SecurityAlert(Base):
    """Security Alert model for external alerts from Wazuh, Snort, OSQuery, etc."""

    __tablename__ = "security_alerts"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Source identification
    tenant_id = Column(String(64), nullable=False, index=True, default="default")
    source = Column(
        String(50), nullable=False, index=True
    )  # wazuh, snort, osquery, etc
    external_event_id = Column(String(255), nullable=False, index=True)

    # Event details
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(
        String(20), nullable=False, index=True
    )  # critical, high, medium, low, info
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    # Network information
    source_ip = Column(String(50), nullable=True, index=True)
    destination_ip = Column(String(50), nullable=True)
    protocol = Column(String(20), nullable=True)

    # Host/Agent information
    agent_name = Column(String(255), nullable=True, index=True)
    agent_id = Column(String(50), nullable=True)
    agent_ip = Column(String(50), nullable=True)

    # Rule information
    rule_id = Column(String(100), nullable=True)
    rule_level = Column(Integer, nullable=True)
    rule_groups = Column(Text, nullable=True)  # Comma-separated groups
    rule_mitre = Column(Text, nullable=True)  # Comma-separated MITRE tactics

    # Log and location data
    full_log = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)
    geoip = Column(JSON, nullable=True)  # Geographic location data

    # Raw data storage
    raw_data = Column(JSON, nullable=True)  # Original alert data

    # Status and workflow
    status = Column(
        String(20), default="new", nullable=False, index=True
    )  # new, investigating, resolved, false_positive, escalated
    assigned_to = Column(String(255), nullable=True, index=True)  # User assigned to
    assigned_at = Column(DateTime(timezone=True), nullable=True)  # Assignment timestamp

    # Resolution
    resolution_note = Column(Text, nullable=True)  # Resolution notes
    root_cause = Column(Text, nullable=True)  # Root cause analysis
    remediation = Column(Text, nullable=True)  # Remediation steps
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(255), nullable=True)  # User ID who resolved it

    # Escalation
    escalated_to = Column(String(255), nullable=True)  # Escalated to user/role
    escalated_at = Column(DateTime(timezone=True), nullable=True)
    escalation_reason = Column(Text, nullable=True)

    # Threat Intelligence
    threat_score = Column(Integer, nullable=True)  # 0-100
    enriched_at = Column(DateTime(timezone=True), nullable=True)  # Last enrichment time
    iocs = Column(JSON, nullable=True)  # Extracted IOCs
    mitre_tactics = Column(JSON, nullable=True)  # MITRE ATT&CK tactics
    mitre_techniques = Column(JSON, nullable=True)  # MITRE ATT&CK techniques

    # Tags and classification
    tags = Column(JSON, nullable=True)  # User-defined tags
    classification = Column(
        String(50), nullable=True
    )  # True positive, false positive, etc

    # Deduplication and Aggregation
    fingerprint = Column(
        String(64), nullable=True, index=True
    )  # Alert fingerprint for deduplication
    aggregated_count = Column(
        Integer, default=1, nullable=False
    )  # Number of aggregated alerts
    last_seen_at = Column(
        DateTime(timezone=True), nullable=True
    )  # Last time this alert was seen
    is_aggregated = Column(
        Integer, default=0, nullable=False
    )  # Whether this is an aggregated alert (0=no, 1=yes)

    # Legacy fields (for backward compatibility)
    closed_at = resolved_at
    closed_by = resolved_by
    resolution = resolution_note

    # Relationships
    notes = relationship(
        "AlertNoteModel", back_populates="alert", cascade="all, delete-orphan"
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Event timestamp (from source system)
    event_timestamp = Column(DateTime(timezone=True), nullable=True, index=True)

    # Indexes for common queries
    __table_args__ = (
        Index(
            "ix_security_alerts_source_event_id",
            "source",
            "external_event_id",
            unique=True,
        ),
        Index("ix_security_alerts_severity_status", "severity", "status"),
        Index("ix_security_alerts_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<SecurityAlert(id={self.id}, source={self.source}, title={self.title[:50]}...)>"

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary representation."""
        return {
            "id": self.id,
            "source": self.source,
            "external_event_id": self.external_event_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "protocol": self.protocol,
            "agent_name": self.agent_name,
            "agent_id": self.agent_id,
            "agent_ip": self.agent_ip,
            "rule_id": self.rule_id,
            "rule_level": self.rule_level,
            "rule_groups": self.rule_groups.split(",") if self.rule_groups else [],
            "rule_mitre": self.rule_mitre.split(",") if self.rule_mitre else [],
            "full_log": self.full_log,
            "location": self.location,
            "geoip": self.geoip,
            "raw_data": self.raw_data,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "resolution": self.resolution,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "closed_by": self.closed_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "event_timestamp": (
                self.event_timestamp.isoformat() if self.event_timestamp else None
            ),
        }
