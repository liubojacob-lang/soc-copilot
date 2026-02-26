"""Schemas for AI model operations."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List


class AIModelResponse(BaseModel):
    """Schema for AI model response."""
    id: str
    provider: str
    display_name: str
    description: Optional[str] = None
    enabled: bool
    is_default: bool
    capabilities: Optional[dict] = None
    max_tokens: Optional[int] = None
    config: Optional[dict] = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class AIModelListResponse(BaseModel):
    """Schema for AI model list response."""
    models: List[AIModelResponse]
    total: int
    default_model_id: Optional[str] = None

    model_config = ConfigDict(protected_namespaces=())


class SetDefaultModelRequest(BaseModel):
    """Schema for setting default model."""
    model_id: str = Field(..., description="Model ID to set as default")

    model_config = ConfigDict(protected_namespaces=())


class SetDefaultModelResponse(BaseModel):
    """Schema for set default model response."""
    success: bool
    model_id: str
    message: str = "Default model updated"

    model_config = ConfigDict(protected_namespaces=())


class TestModelRequest(BaseModel):
    """Schema for testing a model."""
    model_id: str = Field(..., description="Model ID to test")

    model_config = ConfigDict(protected_namespaces=())


class TestModelResponse(BaseModel):
    """Schema for model test response."""
    success: bool
    model_id: str
    latency_ms: Optional[float] = None
    provider_raw: Optional[str] = None
    error_message: Optional[str] = None
    response: Optional[str] = None

    model_config = ConfigDict(protected_namespaces=())


class ChatRequestWithModel(BaseModel):
    """Schema for chat request with model selection."""
    message: str = Field(..., min_length=1, max_length=10000)
    model_id: Optional[str] = Field(None, description="Specific model ID to use (uses default if not provided)")
    conversation_history: Optional[List[dict]] = Field(default_factory=list, description="Previous conversation messages")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for continuity")

    model_config = ConfigDict(protected_namespaces=())


class ChatResponseWithModel(BaseModel):
    """Schema for chat response with model info."""
    message: str
    response: str
    model_id: str
    provider: str
    conversation_id: Optional[str] = None
    processed_at: str

    model_config = ConfigDict(protected_namespaces=())
