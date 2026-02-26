"""AI Model configuration for model selection and testing."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, JSON, Integer, Text as SQLText
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base

if TYPE_CHECKING:
    pass


class AIProvider(str):
    """AI Provider identifiers."""
    ANTHROPIC = "anthropic"
    ZHIPU = "zhipu"
    OPENAI = "openai"
    NVIDIA = "nvidia"
    MOONSHOT = "moonshot"
    OPENROUTER = "openrouter"
    LOCAL = "local"


class AIModelCapability(str):
    """AI Model capabilities."""
    CHAT = "chat"
    JSON = "json"
    VISION = "vision"
    TOOLS = "tools"


class AIModelModel(Base):
    """Model for available AI models."""

    __tablename__ = "ai_models"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(SQLText, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    capabilities: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Non-sensitive config like base_url, default temperature
    created_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now().isoformat())
    updated_at: Mapped[str] = mapped_column(String(30), nullable=False, default=lambda: datetime.now().isoformat())
