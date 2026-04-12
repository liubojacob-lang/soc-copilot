"""API Key model for API authentication."""

import secrets
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class APIKeyModel(Base):
    """Model for API keys."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    key_hash: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    key_prefix: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # First 8 chars for display
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        String(30),
        index=True,
        nullable=False,
        default=lambda: datetime.now().isoformat(),
    )
    last_used_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    expires_at: Mapped[str | None] = mapped_column(String(30), nullable=True)

    @staticmethod
    def generate_key() -> str:
        """Generate a secure random API key."""
        return f"sk_{secrets.token_urlsafe(32)}"
