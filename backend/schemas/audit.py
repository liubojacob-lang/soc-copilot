"""Schemas for audit log operations."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class AuditLogBase(BaseModel):
    """Base audit log schema."""
    action: str
    method: str
    path: str
    status_code: int


class AuditLogInDB(AuditLogBase):
    """Schema for audit log in database."""
    id: str
    user_id: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    duration_ms: Optional[int] = None
    extra_json: dict = Field(default_factory=dict)
    created_at: str

    class Config:
        from_attributes = True


class AuditLogResponse(AuditLogInDB):
    """Schema for audit log response."""
    username: Optional[str] = None  # Joined from users table


class AuditLogListResponse(BaseModel):
    """Schema for audit log list response."""
    total: int
    page: int
    page_size: int
    items: list[AuditLogResponse]


class AuditLogFilter(BaseModel):
    """Schema for audit log filtering."""
    user_id: Optional[str] = None
    action: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[str] = None  # Changed to str to support categories like "4xx", "error"
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=100)
