"""Schemas for playbook run operations."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional, Literal
from datetime import datetime


class PlaybookRunCreateRequest(BaseModel):
    """Schema for creating a new playbook run."""

    model_config = ConfigDict(protected_namespaces=())

    playbook_name: str = Field(..., description="Name of the playbook to run")
    mode: Literal["dry_run", "apply"] = Field("dry_run", description="Execution mode")
    input_json: dict[str, Any] = Field(default_factory=dict, description="Input parameters for the playbook")


class PlaybookRunResponse(BaseModel):
    """Schema for playbook run response."""

    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    id: str
    playbook_name: str
    playbook_version: str
    mode: str
    status: str
    created_by_user_id: Optional[str]
    input_json: dict[str, Any]
    output_json: dict[str, Any]
    started_at: datetime
    finished_at: Optional[datetime]
    error_message: Optional[str]


class PlaybookRunStepResponse(BaseModel):
    """Schema for playbook run step response."""

    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    id: str
    run_id: str
    step_index: int
    step_id: str
    step_name: str
    step_type: str
    status: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration_ms: Optional[int]
    input_json: dict[str, Any]
    output_json: dict[str, Any]
    error_text: Optional[str]
    skipped_reason: Optional[str]


class PlaybookRunListResponse(BaseModel):
    """Schema for playbook run list response."""

    model_config = ConfigDict(protected_namespaces=())

    items: list[PlaybookRunResponse]
    total: int
    page: int
    page_size: int


class PlaybookResumeRequest(BaseModel):
    """Schema for resuming a playbook run."""

    model_config = ConfigDict(protected_namespaces=())

    from_step_index: Optional[int] = Field(None, description="Resume from this step (0-based)")
    run_mode: Optional[Literal["dry_run", "apply"]] = Field(None, description="Override run mode")


class PlaybookResumeResponse(BaseModel):
    """Schema for playbook run resume response."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: str
    from_step: int
    output_json: dict[str, Any]


class PlaybookRunWithStepsResponse(BaseModel):
    """Schema for playbook run with steps response."""

    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    run: PlaybookRunResponse
    steps: list[PlaybookRunStepResponse]


# Available playbooks
AVAILABLE_PLAYBOOKS = {
    "phishing_triage": {
        "name": "Phishing Email Triage",
        "description": "Analyze phishing emails with IOC extraction, threat intelligence lookup, asset correlation, and remediation planning",
        "version": "1.0.0",
        "estimated_duration_seconds": 60,
        "steps": ["ioc_extract", "ti_lookup_otx", "asset_enrich", "risk_score", "action_plan"],
    },
    "endpoint_malware_triage": {
        "name": "Endpoint Malware Triage",
        "description": "Investigate malware alerts with IOC extraction, threat intelligence, asset impact analysis, and containment recommendations",
        "version": "1.0.0",
        "estimated_duration_seconds": 90,
        "steps": ["ioc_extract", "ti_lookup_otx", "asset_enrich", "risk_score", "timeline_build", "action_plan"],
    },
    "suspicious_login_triage": {
        "name": "Suspicious Login Triage",
        "description": "Investigate suspicious login activity with user context, threat intel, asset criticality, and remediation actions",
        "version": "1.0.0",
        "estimated_duration_seconds": 45,
        "steps": ["ioc_extract", "ti_lookup_otx", "asset_enrich", "risk_score", "action_plan"],
    },
}
