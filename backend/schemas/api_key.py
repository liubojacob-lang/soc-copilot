"""Schemas for API key operations."""


from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class APIKeyBase(BaseModel):
    """Base API key schema."""

    description: str = Field(..., max_length=500)


class APIKeyCreate(APIKeyBase):
    """Schema for creating an API key."""

    expires_in_days: int | None = Field(None, ge=1, le=365)


class APIKeyUpdate(BaseModel):
    """Schema for updating an API key."""

    description: str | None = Field(None, max_length=500)
    is_active: bool | None = None
    expires_at: str | None = None


class APIKeyInDB(BaseModel):
    """Schema for API key in database."""

    id: str
    user_id: str
    key_prefix: str
    description: str
    is_active: bool
    created_at: str
    last_used_at: str | None = None
    expires_at: str | None = None

    model_config = ConfigDict(from_attributes=True)


class APIKeyCreateResponse(BaseModel):
    """Schema for API key creation response (includes actual key)."""

    key: str  # Only shown once during creation
    api_key: APIKeyInDB


class APIKeyResponse(APIKeyInDB):
    """Schema for API key response (no actual key)."""

    pass
