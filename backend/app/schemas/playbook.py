"""Schemas for playbook operations."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional
from datetime import datetime


class QueryTemplate(BaseModel):
    """Schema for a single query template."""

    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(..., description="Query name")
    description: str = Field(..., description="Query description")
    query: str = Field(..., description="Query string")
    time_range: str = Field(..., description="Time range for the query")
    fields_expected: list[str] = Field(..., description="Expected fields in results")
    prerequisite: str = Field(..., description="Required log type or condition")


class PlatformQueries(BaseModel):
    """Schema for queries for a specific platform."""

    model_config = ConfigDict(protected_namespaces=())

    platform: str = Field(..., description="Platform name: splunk, elastic_kql, sentinel_kql")
    queries: list[QueryTemplate] = Field(..., description="List of queries")


class GenerateQueriesRequest(BaseModel):
    """Schema for generating queries request."""

    model_config = ConfigDict(protected_namespaces=())

    module: str = Field(..., description="Source module: analyzer, timeline, report")
    history_id: Optional[str] = Field(None, description="History record ID to load IOCs from")
    iocs: Optional[dict[str, list[str]]] = Field(None, description="Direct IOC input")
    platforms: list[str] = Field(
        default=["splunk"],
        description="Target platforms: splunk, elastic_kql, sentinel_kql"
    )
    time_ranges: list[str] = Field(
        default=["last_24h"],
        description="Time ranges: last_1h, last_24h, last_7d"
    )


class GenerateQueriesResponse(BaseModel):
    """Schema for generate queries response."""

    model_config = ConfigDict(protected_namespaces=()))

    request_id: str
    degraded: bool = False
    error_reason: Optional[str] = None
    results: list[PlatformQueries]
    meta: dict[str, Any] = Field(default_factory=dict)


class RemediationStep(BaseModel):
    """Schema for a single remediation step."""

    model_config = ConfigDict(protected_namespaces=()))

    action: str = Field(..., description="Action description")
    method: str = Field(..., description="Method or tool to use")
    command: Optional[str] = Field(None, description="Command if applicable")


class RemediationAction(BaseModel):
    """Schema for a remediation action."""

    model_config = ConfigDict(protected_namespaces=()))

    title: str = Field(..., description="Action title")
    risk: str = Field(..., description="Risk level: low, medium, high, critical")
    category: str = Field(..., description="Category: containment, eradication, recovery")
    priority: int = Field(..., description="Priority order (1=highest)")
    steps: list[RemediationStep] = Field(..., description="Action steps")
    verification: list[str] = Field(..., description="Verification steps")
    rollback: list[str] = Field(..., description="Rollback steps")
    rationale: str = Field(..., description="Why this action is recommended")


class GenerateActionsRequest(BaseModel):
    """Schema for generating actions request."""

    model_config = ConfigDict(protected_namespaces=()))

    history_id: str = Field(..., description="History record ID")
    policy: str = Field(
        default="safe",
        description="Policy: safe (defensive only), moderate, aggressive"
    )
    include_verification_steps: bool = Field(default=True, description="Include verification steps")


class GenerateActionsResponse(BaseModel):
    """Schema for generate actions response."""

    model_config = ConfigDict(protected_namespaces=()))

    request_id: str
    degraded: bool = False
    error_reason: Optional[str] = None
    actions: list[RemediationAction]
    meta: dict[str, Any] = Field(default_factory=dict)


class PlaybookOutputResponse(BaseModel):
    """Schema for playbook output response."""

    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    id: str
    created_at: datetime
    history_id: Optional[str]
    output_type: str
    platform: Optional[str]
    output_json: dict[str, Any]
    request_id: Optional[str]
    degraded: bool
    error_reason: Optional[str]


class PlaybookHistoryResponse(BaseModel):
    """Schema for playbook history response."""

    model_config = ConfigDict(protected_namespaces=())

    items: list[PlaybookOutputResponse]
    total: int
