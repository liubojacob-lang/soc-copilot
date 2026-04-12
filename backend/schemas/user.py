"""Schemas for user operations."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field

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

    role: UserRole | None = None
    is_active: bool | None = None


class UserInDB(UserBase):
    """Schema for user in database."""

    id: str
    is_active: bool
    created_at: str
    updated_at: str
    last_login_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


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
    csrf_token: str | None = None  # CSRF token for protected requests
    must_change_password: bool | None = False  # Force password change on first login


class TokenRefresh(BaseModel):
    """Schema for token refresh."""

    refresh_token: str


class MeResponse(UserResponse):
    """Schema for /me endpoint."""

    permissions: list[str] = Field(default_factory=list)


class PasswordResetRequest(BaseModel):
    """Schema for admin password reset request."""

    new_password: str = Field(..., min_length=8, max_length=100)


class ChangePasswordRequest(BaseModel):
    """Schema for user changing their own password."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str
