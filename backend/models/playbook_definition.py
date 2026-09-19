"""DAG-based playbook definition models for v0.7."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


class PlaybookDefinitionStatus:
    """Playbook definition status constants."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PlaybookDefinitionModel(Base):
    """Model for storing DAG-based playbook definitions with version management."""

    __tablename__ = "playbook_definitions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )  # v1.1: soft delete
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    definition_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # v0.7.3: Version management fields
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PlaybookDefinitionStatus.DRAFT, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # v0.7.4: Dify workflow integration
    execution_engine: Mapped[str] = mapped_column(
        String(20), default="native", nullable=False
    )  # native

    # Relationships
    triggers = relationship(
        "PlaybookTriggerModel",
        back_populates="definition",
        cascade="all, delete-orphan",
    )
    runs = relationship(
        "PlaybookRunModel",
        back_populates="definition",
        foreign_keys="PlaybookRunModel.definition_id",
    )
    versions = relationship(
        "PlaybookDefinitionVersionModel",
        back_populates="definition",
        cascade="all, delete-orphan",
    )

    @property
    def can_modify(self) -> bool:
        """Check if this definition can be modified."""
        return self.status == PlaybookDefinitionStatus.DRAFT

    @property
    def can_publish(self) -> bool:
        """Check if this definition can be published."""
        return self.status == PlaybookDefinitionStatus.DRAFT

    @property
    def dag_json(self) -> dict:
        """Alias for definition_json for backward compatibility."""
        return self.definition_json

    @dag_json.setter
    def dag_json(self, value: dict) -> None:
        """Setter for dag_json alias."""
        self.definition_json = value


class PlaybookTriggerModel(Base):
    """Model for storing trigger configurations for playbooks."""

    __tablename__ = "playbook_triggers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    definition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("playbook_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(200))
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # v0.7.1: New fields for enhanced trigger system
    secret: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Webhook secret
    cron_expr: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Cron schedule
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Relationships
    definition = relationship("PlaybookDefinitionModel", back_populates="triggers")


class PlaybookDefinitionVersionModel(Base):
    """Model for storing version history of playbook definitions."""

    __tablename__ = "playbook_definition_versions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    playbook_definition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("playbook_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    dag_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    definition = relationship("PlaybookDefinitionModel", back_populates="versions")

    def to_dict(self) -> dict:
        """Convert version to dictionary for export."""
        return {
            "id": self.id,
            "playbook_definition_id": self.playbook_definition_id,
            "version_no": self.version_no,
            "dag_json": self.dag_json,
            "name": self.name,
            "description": self.description,
            "created_by_user_id": self.created_by_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "change_note": self.change_note,
        }
