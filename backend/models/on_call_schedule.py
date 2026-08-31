"""On-call schedule model for notification escalation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class OnCallSchedule(Base):
    """Represents an on-call rotation schedule entry.

    Used by the escalation service to determine who should receive
    escalated notifications for unacknowledged alerts.
    """

    __tablename__ = "on_call_schedules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    end_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    rotation_group: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, default="default"
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_on_call_active_window", "rotation_group", "start_date", "end_date"),
        Index("ix_on_call_user_window", "user_id", "start_date", "end_date"),
    )
