"""Schemas for playbook run operations."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# v0.7 DAG Execution Status Types
NodeStatus = Literal["pending", "running", "success", "failed", "skipped", "cancelled"]
RunStatus = Literal["pending", "running", "success", "failed", "partial", "cancelled"]
EngineVersion = Literal["v0.6", "v0.7"]
ExecutionMode = Literal["linear", "dag"]
FailureStrategy = Literal["fail_fast", "continue"]


class PlaybookRunCreateRequest(BaseModel):
    """Schema for creating a new playbook run."""

    model_config = ConfigDict(protected_namespaces=())

    playbook_name: str = Field(..., description="Name of the playbook to run")
    mode: Literal["dry_run", "apply"] = Field("dry_run", description="Execution mode")
    input_json: dict[str, Any] = Field(
        default_factory=dict, description="Input parameters for the playbook"
    )


class PlaybookRunResponse(BaseModel):
    """Schema for playbook run response."""

    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)

    id: str
    playbook_name: str
    playbook_version: str
    mode: str
    status: str
    created_by_user_id: str | None
    input_json: dict[str, Any]
    output_json: dict[str, Any]
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None


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
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    input_json: dict[str, Any]
    output_json: dict[str, Any]
    error_text: str | None
    skipped_reason: str | None


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

    from_step_index: int | None = Field(
        None, description="Resume from this step (0-based)"
    )
    run_mode: Literal["dry_run", "apply"] | None = Field(
        None, description="Override run mode"
    )


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
        "steps": [
            "ioc_extract",
            "ti_lookup_otx",
            "asset_enrich",
            "risk_score",
            "action_plan",
        ],
    },
    "endpoint_malware_triage": {
        "name": "Endpoint Malware Triage",
        "description": "Investigate malware alerts with IOC extraction, threat intelligence, asset impact analysis, and containment recommendations",
        "version": "1.0.0",
        "estimated_duration_seconds": 90,
        "steps": [
            "ioc_extract",
            "ti_lookup_otx",
            "asset_enrich",
            "risk_score",
            "timeline_build",
            "action_plan",
        ],
    },
    "suspicious_login_triage": {
        "name": "Suspicious Login Triage",
        "description": "Investigate suspicious login activity with user context, threat intel, asset criticality, and remediation actions",
        "version": "1.0.0",
        "estimated_duration_seconds": 45,
        "steps": [
            "ioc_extract",
            "ti_lookup_otx",
            "asset_enrich",
            "risk_score",
            "action_plan",
        ],
    },
}


# ==================== v0.7 DAG Playbook Schemas ====================


class PlaybookDefinitionCreate(BaseModel):
    """Schema for creating a DAG playbook definition."""

    name: str = Field(..., min_length=1, max_length=200)
    version: str = Field("1.0.0", description="Version string")
    description: str | None = Field(None, description="Playbook description")
    dag: dict[str, Any] = Field(..., description="DAG definition with nodes and edges")
    is_active: bool = Field(True, description="Active status")


class PlaybookDefinitionUpdate(BaseModel):
    """Schema for updating a DAG playbook definition."""

    name: str | None = Field(None, min_length=1, max_length=200)
    version: str | None = Field(None)
    description: str | None = Field(None)
    dag: dict[str, Any] | None = Field(None)
    is_active: bool | None = Field(None)


class PlaybookDefinitionResponse(BaseModel):
    """Schema for DAG playbook definition response."""

    model_config = ConfigDict(from_attributes=False)

    id: str
    name: str
    version: str
    description: str | None
    dag: dict[str, Any]
    created_by_user_id: str | None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    # Computed fields
    node_count: int = Field(0)
    edge_count: int = Field(0)


class PlaybookDefinitionListResponse(BaseModel):
    """Response for DAG playbook definitions list."""

    items: list[PlaybookDefinitionResponse]
    total: int
    page: int
    page_size: int


class DAGPlaybookRunCreate(BaseModel):
    """Schema for creating a DAG playbook run."""

    mode: Literal["dry_run", "apply"] = Field("dry_run")
    input_context: dict[str, Any] = Field(default_factory=dict)
    failure_strategy: FailureStrategy = Field("fail_fast")
    # P0-3: Idempotency key for request deduplication
    idempotency_key: str | None = Field(
        None, description="Unique key to prevent duplicate runs"
    )


class DAGNodeRunResponse(BaseModel):
    """Schema for DAG node run response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    node_id: str
    node_name: str
    node_type: str
    status: NodeStatus
    started_at: datetime | None
    finished_at: datetime | None
    attempt_count: int
    last_error: str | None
    input_json: dict[str, Any]
    output_json: dict[str, Any]
    created_at: datetime


class DAGNodeAttemptResponse(BaseModel):
    """Schema for DAG node attempt response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    node_run_id: str
    attempt_no: int
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    log_text: str | None
    output_json: dict[str, Any]
    error_text: str | None


class DAGPlaybookRunResponse(BaseModel):
    """Schema for DAG playbook run response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    playbook_name: str
    playbook_version: str
    engine_version: EngineVersion
    mode: str
    status: RunStatus
    failure_strategy: FailureStrategy
    created_by_user_id: str | None
    input_json: dict[str, Any]
    output_json: dict[str, Any]
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None

    # DAG-specific
    definition_id: str | None
    execution_mode: ExecutionMode

    # Node summary
    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0
    running_nodes: int = 0
    pending_nodes: int = 0

    # Control flags
    cancel_requested_at: datetime | None
    can_resume: bool = False


class DAGPlaybookRunWithNodesResponse(BaseModel):
    """Schema for DAG playbook run with nodes."""

    run: DAGPlaybookRunResponse
    nodes: list[DAGNodeRunResponse]


class DAGNodeRunWithAttemptsResponse(BaseModel):
    """Schema for DAG node run with attempts."""

    node_run: DAGNodeRunResponse
    attempts: list[DAGNodeAttemptResponse]


class PlaybookRunCancelRequest(BaseModel):
    """Schema for cancelling a run."""

    reason: str | None = Field(None, description="Cancellation reason")


class PlaybookRunResumeRequest(BaseModel):
    """Schema for resuming a run."""

    from_node_id: str | None = Field(None, description="Resume from specific node")
    failure_strategy: FailureStrategy | None = Field(
        None, description="Override failure strategy"
    )


class PlaybookRunCancelResponse(BaseModel):
    """Schema for cancel response."""

    run_id: str
    status: RunStatus
    message: str


class PlaybookRunErrorResponse(BaseModel):
    """Structured error response for playbook run failures."""

    success: bool = Field(False, description="Always false for error responses")
    error_code: str = Field(..., description="Error code for categorization")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(
        None, description="Additional error details"
    )
    trace_id: str | None = Field(None, description="Request trace ID for debugging")
