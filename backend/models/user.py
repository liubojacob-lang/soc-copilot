"""User model for authentication and RBAC."""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Enum as SQLEnum, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum

from db.session import Base


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    ANALYST = "analyst"
    AUDITOR = "auditor"


class UserModel(Base):
    """Model for user accounts."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="default")
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.ANALYST.value, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(String(30), index=True, nullable=False, default=lambda: datetime.now().isoformat())
    updated_at: Mapped[datetime] = mapped_column(String(30), nullable=False, default=lambda: datetime.now().isoformat())
    last_login_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    
    # Password security fields
    password_changed_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[str | None] = mapped_column(String(30), nullable=True)
    password_history: Mapped[dict] = mapped_column(JSON, nullable=False, default=lambda: [])

    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_users_role_is_active', 'role', 'is_active'),
    )
