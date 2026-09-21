"""Schemas for user operations."""

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_serializer,
    field_validator,
)

from models.user import UserRole


class UserBase(BaseModel):
    model_config = {"from_attributes": True}
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
    is_totp_enabled: bool = False
    totp_policy: str = "sudo"
    created_at: str  # v1.0: ORM sends datetime; field_validator converts to ISO str
    updated_at: str
    last_login_at: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", "updated_at", "last_login_at", mode="before")
    @classmethod
    def _dt_to_str(cls, v: object) -> str | None:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)


class UserResponse(UserInDB):
    """Schema for user response (excludes sensitive data)."""

    @field_serializer("created_at", "updated_at", "last_login_at", when_used="always")
    def _serialize_dt(v: object) -> str | None:
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)


class UserLogin(BaseModel):
    """Schema for user login."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Schema for token response.

    Body tokens are populated only when EXPOSE_TOKENS_IN_BODY=true (tests /
    legacy clients). The default cookie flow keeps tokens out of the body.
    """

    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: UserResponse
    csrf_token: str | None = None  # CSRF token for protected requests
    must_change_password: bool | None = False  # Force password change on first login
    require_2fa: bool = (
        False  # True when 2FA code is required before issuing full tokens
    )
    pre_auth_token: str | None = (
        None  # Short-lived token used to complete 2FA login challenge
    )


class TokenRefresh(BaseModel):
    """Schema for token refresh.

    refresh_token is optional: cookie-authenticated clients omit it and the
    backend falls back to the refresh_token HttpOnly cookie.
    """

    refresh_token: str | None = None


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


# ============================================================================
# Two-Factor Authentication (TOTP - RFC 6238) Schemas
# ============================================================================


class TOTPStatusResponse(BaseModel):
    """2FA status and policy response."""

    is_enabled: bool
    policy: str  # "sudo" | "login"


class TOTPSetupResponse(BaseModel):
    """Response returned when initiating 2FA setup."""

    secret: str
    qr_code: str  # data:image/png;base64,...
    provisioning_uri: str
    backup_codes: list[str]


class TOTPEnableRequest(BaseModel):
    """Request to verify code and activate 2FA."""

    secret: str
    code: str
    policy: str = "sudo"  # "sudo" | "login"
    backup_codes: list[str] = Field(default_factory=list)


class TOTPVerifyRequest(BaseModel):
    """Request to verify a 2FA code for Sudo Mode."""

    code: str


class TOTPSudoResponse(BaseModel):
    """Response returned upon successful sudo-mode 2FA verification."""

    valid: bool
    sudo_token: str
    expires_in_seconds: int = 600


class TOTPPolicyRequest(BaseModel):
    """Request to switch 2FA authentication policy."""

    policy: str = Field(..., pattern="^(sudo|login)$")
    code: str


class TOTPDisableRequest(BaseModel):
    """Request to disable 2FA."""

    code: str
    password: str


class Login2FARequest(BaseModel):
    """Request to complete login when 2FA is required."""

    pre_auth_token: str
    code: str
