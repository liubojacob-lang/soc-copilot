"""Schemas for user operations."""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime

from models.user import UserRole


class UserBase(BaseModel):
    """Base user schema."""
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    role: UserRole = Field(default=UserRole.ANALYST)


class UserCreate(UserBase):
    """Schema for creating a user."""
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Schema for updating a user."""
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """Schema for user in database."""
    id: str
    is_active: bool
    created_at: str
    updated_at: str
    last_login_at: Optional[str] = None

    class Config:
        from_attributes = True


class UserResponse(UserInDB):
    """Schema for user response (excludes sensitive data)."""
    pass


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefresh(BaseModel):
    """Schema for token refresh."""
    refresh_token: str


class MeResponse(UserResponse):
    """Schema for /me endpoint."""
    permissions: list[str] = Field(default_factory=list)
