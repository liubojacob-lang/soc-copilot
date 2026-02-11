"""Schemas for report generation."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class ReportGenerationRequest(BaseModel):
    """Request for report generation."""

    alert_json: str = Field(..., description="JSON string from analyzer output")
    additional_notes: Optional[str] = Field(None, description="Additional user notes")


class ReportGenerationResponse(BaseModel):
    """Response from report generation."""

    model_config = ConfigDict(protected_namespaces=())

    ticket_template: str
    daily_report_template: str
    postmortem_template: str

    # Metadata fields (v0.2)
    request_id: Optional[str] = Field(None, description="Unique request ID for tracing")
    model_used: Optional[str] = Field(None, description="AI model used")
    degraded: bool = Field(False, description="Whether degraded mode was used")
    error_reason: Optional[str] = Field(None, description="Error reason if degraded")
