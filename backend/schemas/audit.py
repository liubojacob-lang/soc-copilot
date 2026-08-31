"""Schemas for audit log operations."""

from pydantic import BaseModel, ConfigDict, Field


class AuditLogBase(BaseModel):
    """Base audit log schema."""

    action: str
    method: str
    path: str
    status_code: int


class AuditLogInDB(AuditLogBase):
    """Schema for audit log in database."""

    id: str
    user_id: str | None = None
    target_type: str | None = None
    target_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    duration_ms: int | None = None
    extra_json: dict = Field(default_factory=dict)
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(AuditLogInDB):
    """Schema for audit log response."""

    username: str | None = None  # Joined from users table


class AuditLogListResponse(BaseModel):
    """Schema for audit log list response."""

    total: int
    page: int
    page_size: int
    items: list[AuditLogResponse]


class AuditLogFilter(BaseModel):
    """Schema for audit log filtering."""

    user_id: str | None = None
    action: str | None = None
    path: str | None = None
    status_code: str | None = (
        None  # Changed to str to support categories like "4xx", "error"
    )
    date_from: str | None = None
    date_to: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
