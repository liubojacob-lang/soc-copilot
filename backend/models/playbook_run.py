"""Playbook run and step models for execution tracking."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


class PlaybookRunModel(Base):
    """Model for tracking playbook execution runs."""

    __tablename__ = "playbook_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    playbook_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    playbook_version: Mapped[str] = mapped_column(String(20), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # dry_run / apply
    status: Mapped[str] = mapped_column(
        String(20), index=True, nullable=False
    )  # pending / running / success / failed / partial
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
        default=lambda: datetime.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)

    # v0.7 DAG support fields
    engine_version: Mapped[str] = mapped_column(
        String(20), default="v0.6", index=True, nullable=False
    )  # v0.6 / v0.7
    execution_mode: Mapped[str] = mapped_column(
        String(20), default="linear", index=True, nullable=False
    )  # linear / dag
    definition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("playbook_definitions.id", ondelete="SET NULL"),
        index=True,
    )
    failure_strategy: Mapped[str] = mapped_column(
        String(20), default="fail_fast", nullable=False
    )  # fail_fast / continue
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100), unique=True, index=True
    )
    parent_run_id: Mapped[str | None] = mapped_column(
        String(36), index=True
    )  # For nested/sub-flow runs
    trigger_source: Mapped[str] = mapped_column(
        String(50), default="manual", index=True
    )  # manual / webhook / cron / api
    trigger_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("playbook_triggers.id", ondelete="SET NULL"), index=True
    )  # v0.7.1: Associated trigger
    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )  # When cancel was requested

    # v0.7.3: Context variable system and replay fields
    input_context_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: {}
    )  # Initial context at run start
    context_json: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: {}
    )  # Dynamic accumulated variables during execution
    replay_of_run_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("playbook_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )  # Parent run for replay

    # v0.7.4: Queue management
    queued_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )  # When run was added to queue

    # Relationships
    steps = relationship(
        "PlaybookRunStepModel", back_populates="run", cascade="all, delete-orphan"
    )
    definition = relationship(
        "PlaybookDefinitionModel", back_populates="runs", foreign_keys=[definition_id]
    )
    node_runs = relationship("PlaybookNodeRunModel", cascade="all, delete-orphan")
    # v0.7.3: Replay lineage relationships
    replay_parent = relationship(
        "PlaybookRunModel", remote_side=[id], foreign_keys=[replay_of_run_id]
    )
    replay_children = relationship(
        "PlaybookRunModel", foreign_keys=[replay_of_run_id], overlaps="replay_parent"
    )


class PlaybookRunStepModel(Base):
    """Model for tracking individual steps within a playbook run."""

    __tablename__ = "playbook_run_steps"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("playbook_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    step_index: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    step_id: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., "ti_lookup_otx"
    step_name: Mapped[str] = mapped_column(String(200), nullable=False)
    step_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., "ti_lookup"
    status: Mapped[str] = mapped_column(
        String(20), index=True, nullable=False
    )  # pending / running / success / failed / skipped
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    error_text: Mapped[str | None] = mapped_column(Text)
    skipped_reason: Mapped[str | None] = mapped_column(Text)

    # Relationships
    run = relationship("PlaybookRunModel", back_populates="steps")
