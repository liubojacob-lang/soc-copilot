"""Schemas for history operations."""

from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Any


class HistoryCreate(BaseModel):
    """Schema for creating history record."""

    model_config = ConfigDict(protected_namespaces=())

    module: str = Field(..., description="Module name: analyzer, report, or timeline")
    input_text: str = Field(..., description="Original input text")
    output_json: dict[str, Any] = Field(..., description="Model output JSON")
    output_markdown: str | None = Field(None, description="Rendered markdown output")
    extracted_iocs: dict[str, list[str]] = Field(
        default_factory=dict, description="Extracted IOCs"
    )
    tags: dict[str, Any] | None = Field(None, description="Optional tags")
    request_id: str | None = Field(None, description="Request ID for tracing")
    model_used: str | None = Field(None, description="Model used for generation")
    degraded: bool | None = Field(False, description="Whether response was degraded")
    error_reason: str | None = Field(None, description="Error reason if degraded")


class HistoryResponse(BaseModel):
    """Schema for history response."""

    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    id: str
    module: str
    created_at: datetime
    input_text: str
    output_json: dict[str, Any]
    output_markdown: str | None
    extracted_iocs: dict[str, list[str]]
    tags: dict[str, Any] | None
    request_id: str | None
    model_used: str | None
    degraded: bool
    error_reason: str | None


class HistoryListResponse(BaseModel):
    """Schema for history list response."""

    model_config = ConfigDict(protected_namespaces=())

    items: list[HistoryResponse]
    total: int
