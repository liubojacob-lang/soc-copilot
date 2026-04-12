"""Playbook output model for storing generated queries and actions."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class PlaybookOutputModel(Base):
    """Model for storing playbook-generated queries and actions."""

    __tablename__ = "playbook_outputs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(),
        index=True,
        nullable=False,
    )
    history_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
    output_type: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: {})
    request_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_reason: Mapped[str | None] = mapped_column(String, nullable=True)
