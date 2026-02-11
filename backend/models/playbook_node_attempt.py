"""Playbook Node Attempt Model for retry tracking."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, JSON, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


class PlaybookNodeAttemptModel(Base):
    """Model for tracking retry attempts for failed nodes."""

    __tablename__ = "playbook_node_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("playbook_node_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    attempt_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending/running/success/failed
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    log_text: Mapped[str | None] = mapped_column(Text)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    error_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    node_run = relationship("PlaybookNodeRunModel", back_populates="attempts")
