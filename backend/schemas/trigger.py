"""Pydantic schemas for trigger operations."""

from datetime import datetime
from typing import Any, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


# Webhook trigger schemas
class WebhookTriggerCreate(BaseModel):
    """Schema for creating a webhook trigger."""
    definition_id: str = Field(..., description="Playbook definition ID to trigger")
    name: Optional[str] = Field(None, max_length=200, description="Trigger name")
    config: dict[str, Any] = Field(default_factory=dict, description="Additional configuration")
    is_active: bool = Field(True, description="Whether the trigger is active")


class WebhookTriggerResponse(BaseModel):
    """Schema for webhook trigger response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    definition_id: str
    type: Literal["webhook"]
    name: Optional[str]
    config: dict[str, Any] = Field(..., alias="config_json")
    secret: str
    webhook_url: str = Field(..., description="Full webhook URL")
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_triggered_at: Optional[datetime]


class WebhookTriggerOut(BaseModel):
    """Schema for webhook trigger output (without secret)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    definition_id: str
    type: Literal["webhook"]
    name: Optional[str]
    config: dict[str, Any] = Field(..., alias="config_json")
    secret_prefix: str = Field(..., description="First few characters of secret")
    webhook_url: str = Field(..., description="Full webhook URL")
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_triggered_at: Optional[datetime]


# Cron trigger schemas
class CronTriggerCreate(BaseModel):
    """Schema for creating a cron trigger."""
    definition_id: str = Field(..., description="Playbook definition ID to trigger")
    cron_expr: str = Field(..., description="Cron expression (e.g., '0 0 * * *' for midnight daily)")
    name: Optional[str] = Field(None, max_length=200, description="Trigger name")
    config: dict[str, Any] = Field(default_factory=dict, description="Additional configuration")
    is_active: bool = Field(True, description="Whether the trigger is active")


class CronTriggerResponse(BaseModel):
    """Schema for cron trigger response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    definition_id: str
    type: Literal["cron"]
    name: Optional[str]
    config: dict[str, Any] = Field(..., alias="config_json")
    cron_expr: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_triggered_at: Optional[datetime]


# Trigger schemas (generic)
class TriggerUpdate(BaseModel):
    """Schema for updating a trigger."""
    name: Optional[str] = Field(None, max_length=200)
    config: Optional[dict[str, Any]] = None
    cron_expr: Optional[str] = Field(None, description="For cron triggers only")
    is_active: Optional[bool] = None


class TriggerOut(BaseModel):
    """Schema for trigger output (generic)."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    definition_id: str
    type: str
    name: Optional[str]
    config: dict[str, Any] = Field(..., alias="config_json")
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_triggered_at: Optional[datetime]

    # Type-specific fields (optional)
    secret_prefix: Optional[str] = None
    cron_expr: Optional[str] = None
    webhook_url: Optional[str] = None


class TriggerListResponse(BaseModel):
    """Response for trigger list."""
    items: list[TriggerOut]
    total: int
    page: int
    page_size: int


# Trigger invocation schemas
class TriggerInvocationOut(BaseModel):
    """Schema for trigger invocation output."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    trigger_id: str
    idempotency_key: Optional[str]
    run_id: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime
    expires_at: datetime


class WebhookTestRequest(BaseModel):
    """Schema for testing a webhook trigger."""
    payload: dict[str, Any] = Field(default_factory=dict, description="Test payload")
    idempotency_key: Optional[str] = Field(None, description="Optional idempotency key")


class WebhookTestResponse(BaseModel):
    """Schema for webhook test response."""
    run_id: Optional[str]
    status: str
    message: str
    cached: bool = False
    invocation_id: Optional[str]


# Secret regeneration response
class SecretRegenerateResponse(BaseModel):
    """Response for secret regeneration."""
    secret: str = Field(..., description="New webhook secret")
    message: str


# Triggers list with definition info
class TriggerWithDefinition(TriggerOut):
    """Trigger with playbook definition info."""
    definition_name: str = Field(..., description="Name of the playbook definition")
