"""Prompt Registry model - versioned prompt management."""

import uuid
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.session import Base


class PromptEnvironment(str, Enum):
    """Prompt deployment environment."""

    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class PromptRegistryModel(Base):
    """Model for versioned prompt registry.

    Supports multi-version prompt tracking per environment.
    Only one version per (name, environment) can be active at a time.
    """

    __tablename__ = "prompt_registry"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content: Mapped[str] = mapped_column(String, nullable=False)
    variables: Mapped[dict | list] = mapped_column(
        JSON, nullable=False, default=lambda: []
    )
    environment: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PromptEnvironment.DEV.value,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    created_by: Mapped[str] = mapped_column(
        String(255), nullable=False, default="system"
    )
    created_at: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default=lambda: datetime.now(UTC).isoformat(),
    )
    updated_at: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default=lambda: datetime.now(UTC).isoformat(),
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "name", "version", "environment", name="uq_prompt_name_ver_env"
        ),
        Index("ix_prompt_env_active", "environment", "is_active", "name"),
    )
