"""AI User Settings for model preferences."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey as SQLForeignKey
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class AIUserSettingModel(Base):
    """Model for user-specific AI settings."""

    __tablename__ = "ai_user_settings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), SQLForeignKey("users.id"), nullable=False, unique=True, index=True
    )
    default_model_id: Mapped[str] = mapped_column(
        String(100), nullable=True
    )  # References ai_models.id
    created_at: Mapped[str] = mapped_column(
        String(255), nullable=False, default=lambda: datetime.now().isoformat()
    )
    updated_at: Mapped[str] = mapped_column(
        String(255), nullable=False, default=lambda: datetime.now().isoformat()
    )
