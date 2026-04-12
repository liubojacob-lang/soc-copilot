"""Event correlation rule model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class CorrelationRule(Base):
    """Rule for correlating multiple events into security incidents.

    Rules define how to group related events based on:
    - Time window (events within N minutes)
    - Common entities (IP, user, hostname)
    - Similarity thresholds
    - Custom conditions
    """

    __tablename__ = "correlation_rules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, default="default"
    )

    # Rule metadata
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Correlation parameters
    time_window_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=300,
        doc="Time window for correlation (default: 5 minutes)",
    )

    # Entity matching
    entity_types: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {"ip_address": True, "username": True, "hostname": False},
        doc="Which entities to match on",
    )

    # Similarity thresholds
    min_similarity: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.7, doc="Minimum similarity score (0-1)"
    )

    # Custom conditions (optional)
    conditions: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
        doc="Additional correlation conditions (e.g., severity, category)",
    )

    # Action to take
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="aggregate",
        doc="Action: aggregate, suppress, escalate, or tag",
    )

    action_params: Mapped[dict] = mapped_column(
        JSON, nullable=True, doc="Action-specific parameters"
    )

    # Priority and grouping
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        doc="Rule priority (higher = evaluated first)",
    )

    group_by_field: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        doc="Field to group by (e.g., 'severity', 'attack_type')",
    )

    # Statistics
    total_correlations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_triggered: Mapped[datetime] = mapped_column(
        String(50), nullable=True, doc="ISO format timestamp"
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        String(50), default=lambda: datetime.now(UTC).isoformat()
    )

    updated_at: Mapped[datetime] = mapped_column(
        String(50),
        default=lambda: datetime.now(UTC).isoformat(),
        onupdate=lambda: datetime.now(UTC).isoformat(),
    )

    created_by: Mapped[str] = mapped_column(
        String(100), nullable=True, doc="User who created the rule"
    )

    # Indexes
    __table_args__ = (
        Index("idx_correlation_rules_enabled_priority", "enabled", "priority"),
    )
