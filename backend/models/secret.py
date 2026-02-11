"""Secret model for encrypted credential storage (v0.7.4)."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class SecretModel(Base):
    """Model for storing encrypted secrets and credentials."""

    __tablename__ = "secrets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.utcnow())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.utcnow(), onupdate=func.utcnow())

    def __repr__(self) -> str:
        return f"<Secret(id={self.id}, name={self.name})>"
