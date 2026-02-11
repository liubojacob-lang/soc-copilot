"""User model for authentication and RBAC."""

import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Enum as SQLEnum
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
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.ANALYST.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(String(30), index=True, nullable=False, default=lambda: datetime.now().isoformat())
    updated_at: Mapped[datetime] = mapped_column(String(30), nullable=False, default=lambda: datetime.now().isoformat())
    last_login_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
