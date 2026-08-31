"""
SIEM Log database model.

Stores security event logs ingested from various sources
with structured search and Elasticsearch integration.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship

from db.session import Base


class SIEMLog(Base):
    """SIEM log entry for security event storage and search."""

    __tablename__ = "siem_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True)

    # Event metadata
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String(100), nullable=False)  # e.g., wazuh, syslog, cloudtrail
    log_type = Column(
        String(50), nullable=False, default="raw"
    )  # syslog, cef, json, raw

    # Data
    raw_data = Column(Text, nullable=False)
    parsed_fields = Column(JSON, nullable=False, default=dict)

    # Optional linkage to security alert
    alert_id = Column(
        String(36),
        ForeignKey("security_alerts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Relationships
    alert = relationship("SecurityAlert", backref="siem_logs", lazy="selectin")

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_siem_logs_tenant_ts", "tenant_id", "timestamp"),
        Index("ix_siem_logs_tenant_source", "tenant_id", "source"),
        Index("ix_siem_logs_tenant_type", "tenant_id", "log_type"),
    )
