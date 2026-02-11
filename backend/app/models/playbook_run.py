"""Playbook run and step models for execution tracking."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, JSON, Text, Boolean, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


class PlaybookRunModel(Base):
    """Model for tracking playbook execution runs."""

    __tablename__ = "playbook_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    playbook_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    playbook_version: Mapped[str] = mapped_column(String(20), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # dry_run / apply
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # pending / running / success / failed / partial
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    # Relationships
    steps = relationship("PlaybookRunStepModel", back_populates="run", cascade="all, delete-orphan")


class PlaybookRunStepModel(Base):
    """Model for tracking individual steps within a playbook run."""

    __tablename__ = "playbook_run_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    step_id: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "ti_lookup_otx"
    step_name: Mapped[str] = mapped_column(String(200), nullable=False)
    step_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "ti_lookup"
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)  # pending / running / success / failed / skipped
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    error_text: Mapped[str | None] = mapped_column(Text)
    skipped_reason: Mapped[str | None] = mapped_column(Text)

    # Relationships
    run = relationship("PlaybookRunModel", back_populates="steps")
