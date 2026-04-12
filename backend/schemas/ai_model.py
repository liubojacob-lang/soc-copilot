"""Schemas for AI model operations."""


from pydantic import BaseModel, ConfigDict, Field


class AIModelResponse(BaseModel):
    """Schema for AI model response."""

    id: str
    provider: str
    display_name: str
    description: str | None = None
    enabled: bool
    is_default: bool
    capabilities: dict | None = None
    max_tokens: int | None = None
    config: dict | None = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class AIModelListResponse(BaseModel):
    """Schema for AI model list response."""

    models: list[AIModelResponse]
    total: int
    default_model_id: str | None = None

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
    latency_ms: float | None = None
    provider_raw: str | None = None
    error_message: str | None = None
    response: str | None = None

    model_config = ConfigDict(protected_namespaces=())


class ChatRequestWithModel(BaseModel):
    """Schema for chat request with model selection."""

    message: str = Field(..., min_length=1, max_length=10000)
    model_id: str | None = Field(
        None, description="Specific model ID to use (uses default if not provided)"
    )
    conversation_history: list[dict] | None = Field(
        default_factory=list, description="Previous conversation messages"
    )
    conversation_id: str | None = Field(
        None, description="Conversation ID for continuity"
    )

    model_config = ConfigDict(protected_namespaces=())


class ChatResponseWithModel(BaseModel):
    """Schema for chat response with model info."""

    message: str
    response: str
    model_id: str
    provider: str
    conversation_id: str | None = None
    processed_at: str

    model_config = ConfigDict(protected_namespaces=())
