"""Audit log model for tracking all operations."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class AuditLogModel(Base):
    """Model for audit logging."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    action: Mapped[str] = mapped_column(
        String(100), index=True, nullable=False
    )  # login, playbook_run, user_create, etc.
    method: Mapped[str] = mapped_column(String(10), nullable=False)  # GET, POST, etc.
    path: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # user, playbook_run, api_key, etc.
    target_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    created_at: Mapped[datetime] = mapped_column(
        String(255),
        index=True,
        nullable=False,
        default=lambda: datetime.now().isoformat(),
    )
