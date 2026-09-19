"""Trigger invocation model for tracking webhook and cron executions."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class TriggerInvocationModel(Base):
    """Model for tracking trigger executions with idempotency support."""

    __tablename__ = "trigger_invocations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    trigger_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("playbook_triggers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True, unique=True  # uq_trigger_invocations_idempotency_key (0006)
    )

    run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("playbook_runs.id", ondelete="SET NULL"), nullable=True
    )
    request_hash: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # SHA-256 hash
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    # expires_at is 24 hours after created_at for idempotency retention
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC) + timedelta(hours=24),
        index=True,
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure expires_at is always 24 hours after created_at
        if self.created_at and not kwargs.get("expires_at"):
            self.expires_at = self.created_at + timedelta(hours=24)
