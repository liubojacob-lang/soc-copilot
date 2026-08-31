"""Case management database models.

Cases aggregate related alerts, track investigation progress, and support
team collaboration through timeline entries, comments, and SLA tracking.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from db.session import Base


class CaseModel(Base):
    """Case model for aggregating and tracking security investigations."""

    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deleted_at = Column(
        DateTime(timezone=True), nullable=True, index=True
    )  # v1.1: soft delete
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    severity = Column(
        String(20),
        nullable=False,
        default="medium",
        index=True,
    )  # low / medium / high / critical
    status = Column(
        String(30),
        nullable=False,
        default="new",
        index=True,
    )  # new / investigating / pending_review / resolved / closed
    assigned_to = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sla_due_at = Column(DateTime(timezone=True), nullable=True)
    resolution = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Tenant support
    tenant_id = Column(String(64), nullable=False, index=True, default="default")

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    alerts = relationship(
        "SecurityAlert",
        secondary="case_alerts",
        back_populates="cases",
        lazy="selectin",
    )
    timeline_entries = relationship(
        "CaseTimelineEntry",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseTimelineEntry.occurred_at.desc()",
    )
    comments = relationship(
        "CaseComment",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseComment.created_at.asc()",
    )
    assignee = relationship(
        "UserModel",
        foreign_keys=[assigned_to],
        lazy="selectin",
    )

    # Indexes
    __table_args__ = (
        Index("ix_cases_severity_status", "severity", "status"),
        Index("ix_cases_sla_due_at", "sla_due_at"),
        Index("ix_cases_created_at", "created_at"),
    )


class CaseAlertAssociation(Base):
    """Association table linking cases to security alerts (many-to-many)."""

    __tablename__ = "case_alerts"

    case_id = Column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        primary_key=True,
    )
    alert_id = Column(
        Integer,
        ForeignKey("security_alerts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    added_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    added_by = Column(String(36), nullable=True)

    __table_args__ = (
        Index("ix_case_alerts_case_id", "case_id"),
        Index("ix_case_alerts_alert_id", "alert_id"),
    )


class CaseTimelineEntry(Base):
    """Timeline entries summarizing events within a case."""

    __tablename__ = "case_timeline_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deleted_at = Column(
        DateTime(timezone=True), nullable=True, index=True
    )  # v1.1: soft delete
    case_id = Column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entry_type = Column(
        String(30),
        nullable=False,
        index=True,
    )  # alert / status_change / comment / assignment / resolution
    summary = Column(Text, nullable=False)
    source_alert_id = Column(
        Integer,
        ForeignKey("security_alerts.id", ondelete="SET NULL"),
        nullable=True,
    )
    performed_by = Column(String(36), nullable=True)
    occurred_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )

    # Additional metadata
    metadata_json = Column(Text, nullable=True)  # JSON string for extra context

    # Relationships
    case = relationship("CaseModel", back_populates="timeline_entries")

    __table_args__ = (Index("ix_case_timeline_case_type", "case_id", "entry_type"),)


class CaseComment(Base):
    """User comments on cases."""

    __tablename__ = "case_comments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    deleted_at = Column(
        DateTime(timezone=True), nullable=True, index=True
    )  # v1.1: soft delete
    case_id = Column(
        String(36),
        ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(String(36), nullable=False, index=True)
    username = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    case = relationship("CaseModel", back_populates="comments")

    __table_args__ = (Index("ix_case_comments_case_created", "case_id", "created_at"),)
