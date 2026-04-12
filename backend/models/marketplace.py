"""Marketplace models for playbook sharing."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


class MarketplacePlaybookStatus:
    """Marketplace playbook status constants."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MarketplacePlaybookModel(Base):
    """Model for marketplace playbooks."""

    __tablename__ = "marketplace_playbooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")

    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), default="intermediate")
    tags: Mapped[list] = mapped_column(JSON, default=list)

    author_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    author_name: Mapped[str] = mapped_column(String(100), nullable=False)

    source_definition_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("playbook_definitions.id", ondelete="SET NULL")
    )

    dag_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    documentation: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MarketplacePlaybookStatus.PENDING, index=True
    )

    reviewed_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)

    verified: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    download_count: Mapped[int] = mapped_column(Integer, default=0)
    rating_average: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)

    required_plugins: Mapped[list] = mapped_column(JSON, default=list)
    compatible_versions: Mapped[list] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_marketplace_playbooks_status_featured", "status", "featured"),
        Index("ix_marketplace_playbooks_category_status", "category", "status"),
    )

    @property
    def is_visible(self) -> bool:
        return self.status == MarketplacePlaybookStatus.APPROVED


class MarketplaceReviewModel(Base):
    """Model for marketplace playbook reviews."""

    __tablename__ = "marketplace_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    playbook_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("marketplace_playbooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        Index("ix_marketplace_reviews_playbook_user", "playbook_id", "user_id", unique=True),
    )
