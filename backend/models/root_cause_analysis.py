"""Root cause analysis model."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class RootCauseAnalysis(Base):
    """AI-generated root cause analysis for security alerts.

    Provides deep analysis of alert root causes using:
    - Alert context and related events
    - Historical similar cases
    - System state at time of alert
    - Chain-of-thought reasoning
    """

    __tablename__ = "root_cause_analyses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Alert association
    alert_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, doc="ID of the analyzed alert"
    )

    # Root cause classification
    root_cause_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Primary category: misconfiguration, attack, failure, unknown",
    )

    root_cause_subcategory: Mapped[str] = mapped_column(
        String(100), nullable=True, doc="More specific classification"
    )

    # Confidence metrics
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        doc="Confidence in root cause assessment (0-1)",
    )

    # Chain of reasoning
    reasoning_steps: Mapped[dict] = mapped_column(
        JSON, nullable=False, doc="Step-by-step reasoning chain"
    )

    # Evidence chain
    evidence_chain: Mapped[dict] = mapped_column(
        JSON, nullable=False, doc="Supporting evidence for each reasoning step"
    )

    # Verification steps
    verification_steps: Mapped[list] = mapped_column(
        JSON, nullable=False, doc="Steps to verify the root cause hypothesis"
    )

    # Suggested remediation
    suggested_remediation: Mapped[str] = mapped_column(
        Text, nullable=True, doc="AI-suggested remediation actions"
    )

    remediation_priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
        doc="Priority: critical, high, medium, low",
    )

    # Related alerts (historical)
    similar_alerts: Mapped[list] = mapped_column(
        JSON, nullable=True, doc="IDs of historically similar alerts"
    )

    # AI model info
    ai_model: Mapped[str] = mapped_column(
        String(100), nullable=False, doc="AI model used for analysis"
    )

    ai_prompt_version: Mapped[str] = mapped_column(
        String(50), nullable=True, doc="Version of the prompt used"
    )

    # Analysis metadata
    analysis_duration_ms: Mapped[int] = mapped_column(
        Float, nullable=True, doc="Time taken to perform analysis"
    )

    # Feedback loop
    human_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Whether human analyst verified this analysis",
    )

    human_feedback: Mapped[str] = mapped_column(
        Text, nullable=True, doc="Feedback from human analyst"
    )

    feedback_category: Mapped[str] = mapped_column(
        String(50), nullable=True, doc="accurate, partially_accurate, inaccurate"
    )

    # Timestamps
    created_at: Mapped[str] = mapped_column(
        String(50), default=lambda: datetime.now(UTC).isoformat()
    )

    updated_at: Mapped[str] = mapped_column(
        String(50), default=lambda: datetime.now(UTC).isoformat()
    )

    # Indexes
    __table_args__ = (
        Index("idx_root_cause_alert_id", "alert_id"),
        Index("idx_root_cause_category", "root_cause_category"),
        Index("idx_root_cause_confidence", "confidence"),
    )
