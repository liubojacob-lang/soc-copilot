"""Correlated event model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, JSON, Integer, Float, Text, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


class CorrelatedEvent(Base):
    """Aggregated security incident from multiple raw events.

    Represents a higher-level security incident that combines
    multiple related raw alerts/events into a single actionable item.
    """

    __tablename__ = "correlated_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Correlation metadata
    rule_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("correlation_rules.id"),
        nullable=False,
        index=True
    )

    # Event summary
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="AI-generated or template-based title"
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed description of the correlated incident"
    )

    # Severity and classification
    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
        doc="critical, high, medium, low"
    )

    attack_type: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="e.g., brute_force, phishing, malware, lateral_movement"
    )

    # Confidence score
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        doc="Aggregated confidence (0-1)"
    )

    # Raw event IDs
    raw_event_ids: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        doc="List of raw alert/event IDs included in this correlation"
    )

    raw_event_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total number of raw events aggregated"
    )

    # Common entities (extracted from all events)
    common_entities: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {},
        doc="Common IPs, users, hostnames across all events"
    )

    # Time range
    first_seen: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Earliest event timestamp (ISO format)"
    )

    last_seen: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Latest event timestamp (ISO format)"
    )

    # Status and workflow
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="open",
        index=True,
        doc="open, investigating, resolved, false_positive, closed"
    )

    assigned_to: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        doc="Analyst assigned to investigate"
    )

    # MITRE ATT&CK mapping
    tactics: Mapped[list] = mapped_column(
        JSON,
        nullable=True,
        doc="MITRE ATT&CK tactics (e.g., ['initial-access', 'execution'])"
    )

    techniques: Mapped[list] = mapped_column(
        JSON,
        nullable=True,
        doc="MITRE ATT&CK technique IDs"
    )

    # AI-generated insights
    ai_summary: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="AI-generated concise summary"
    )

    ai_remediation: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        doc="AI-suggested remediation steps"
    )

    # Risk score
    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=50.0,
        doc="Calculated risk score (0-100)"
    )

    # Impact analysis
    affected_assets: Mapped[list] = mapped_column(
        JSON,
        nullable=True,
        doc="List of affected asset IDs"
    )

    affected_users: Mapped[list] = mapped_column(
        JSON,
        nullable=True,
        doc="List of affected user IDs"
    )

    business_impact: Mapped[str] = mapped_column(
        String(20),
        nullable=True,
        doc="high, medium, low, none"
    )

    # Metadata
    created_at: Mapped[str] = mapped_column(
        String(50),
        default=lambda: datetime.now(timezone.utc).isoformat()
    )

    updated_at: Mapped[str] = mapped_column(
        String(50),
        default=lambda: datetime.now(timezone.utc).isoformat()
    )

    resolved_at: Mapped[str] = mapped_column(
        String(50),
        nullable=True
    )

    # Performance metrics
    correlation_time_ms: Mapped[int] = mapped_column(
        Integer,
        nullable=True,
        doc="Time taken to correlate (milliseconds)"
    )

    # Indexes
    __table_args__ = (
        Index('idx_correlated_events_status_severity', 'status', 'severity'),
        Index('idx_correlated_events_first_seen', 'first_seen'),
        Index('idx_correlated_events_attack_type', 'attack_type'),
    )

    # Relationships
    rule = relationship("CorrelationRule", backref="correlated_events")
