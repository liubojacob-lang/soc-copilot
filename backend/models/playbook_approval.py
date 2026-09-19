"""Playbook Approval Model for human-in-the-loop nodes."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class PlaybookApprovalModel(Base):
    """Model for human approval requests in playbooks."""

    __tablename__ = "playbook_approvals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("playbook_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    requested_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    rejected_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )  # pending/approved/rejected/expired
    title: Mapped[str | None] = mapped_column(String(200))
    message: Mapped[str | None] = mapped_column(Text)
    comments: Mapped[str | None] = mapped_column(Text)
    timeout_seconds: Mapped[int | None] = mapped_column(Integer)
    on_timeout: Mapped[str] = mapped_column(
        String(20), nullable=False, default="fail"
    )  # approve/reject/fail
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __init__(self, **kwargs):
        """Initialize approval with optional expiration calculation."""
        super().__init__(**kwargs)
        if self.timeout_seconds and not self.expires_at:
            self.expires_at = datetime.now(UTC) + timedelta(
                seconds=self.timeout_seconds
            )
