"""Playbook Node Run Model for tracking DAG node execution."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


class PlaybookNodeRunModel(Base):
    """Model for tracking individual node executions within a DAG run."""

    __tablename__ = "playbook_node_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("playbook_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    node_id: Mapped[str] = mapped_column(
        String(100), index=True, nullable=False
    )  # DAG node id
    node_name: Mapped[str] = mapped_column(String(200), nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)  # executor type
    status: Mapped[str] = mapped_column(
        String(20), index=True, nullable=False, default="pending"
    )  # pending/running/success/failed/skipped/cancelled
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    input_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    attempts = relationship(
        "PlaybookNodeAttemptModel",
        back_populates="node_run",
        cascade="all, delete-orphan",
    )
