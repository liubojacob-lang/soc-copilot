"""History model for storing analysis results."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class HistoryModel(Base):
    """Model for storing analysis history."""

    __tablename__ = "history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    module: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        index=True,
        nullable=False,
    )
    input_text: Mapped[str] = mapped_column(String, nullable=False)
    output_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_markdown: Mapped[str | None] = mapped_column(String, nullable=True)
    extracted_iocs: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: {}
    )
    tags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    primary_asset_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True
    )
