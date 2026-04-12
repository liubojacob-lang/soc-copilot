"""Pydantic schemas for DAG-based playbooks."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# Node and Edge schemas for DAG definition
class NodeSchema(BaseModel):
    """DAG node schema."""

    id: str = Field(..., description="Unique node identifier")
    name: str = Field(..., description="Node display name")
    type: str = Field(
        ..., description="Node executor type (e.g., 'ti_lookup_otx', 'decision')"
    )
    config: dict[str, Any] = Field(
        default_factory=dict, description="Node configuration"
    )
    inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Node input mapping (legacy, for backward compatibility)",
    )
    retry_policy: dict[str, Any] | None = Field(
        None, description="Retry policy configuration"
    )
    timeout_seconds: int = Field(300, description="Execution timeout")

    # v0.7.3: Context variable system fields
    outputs_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Map JSONPath expressions to context keys (e.g., {'$.pulse_info': 'context.ti.pulse'})",
    )
    inputs_template: dict[str, Any] = Field(
        default_factory=dict,
        description="Input template with variable references (e.g., {'ioc': '{{context.ioc}}'})",
    )

    @property
    def resolved_inputs(self) -> dict[str, Any]:
        """Return inputs, preferring inputs_template if available."""
        return self.inputs_template or self.inputs


class EdgeSchema(BaseModel):
    """DAG edge schema."""

    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    condition: str | None = Field(
        None, description="Condition expression (e.g., '$.output.score > 50')"
    )


class DAGSchema(BaseModel):
    """DAG schema."""

    nodes: list[NodeSchema] = Field(default_factory=list, description="DAG nodes")
    edges: list[EdgeSchema] = Field(default_factory=list, description="DAG edges")

    def get_node(self, node_id: str) -> NodeSchema | None:
        """Get node by ID."""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_outgoing_edges(self, node_id: str) -> list[EdgeSchema]:
        """Get outgoing edges from node."""
        return [e for e in self.edges if e.source == node_id]

    def get_incoming_edges(self, node_id: str) -> list[EdgeSchema]:
        """Get incoming edges to node."""
        return [e for e in self.edges if e.target == node_id]


# Playbook Definition schemas
class PlaybookDefinitionCreate(BaseModel):
    """Schema for creating a playbook definition."""

    name: str = Field(..., min_length=1, max_length=200)
    version: str = Field("1.0.0", description="Version string")
    description: str | None = Field(None, description="Playbook description")
    dag: DAGSchema = Field(..., description="DAG definition")


class PlaybookDefinitionUpdate(BaseModel):
    """Schema for updating a playbook definition."""

    name: str | None = Field(None, min_length=1, max_length=200)
    version: str | None = Field(None, description="Version string")
    description: str | None = Field(None, description="Playbook description")
    dag: DAGSchema | None = Field(None, description="DAG definition")
    is_active: bool | None = Field(None, description="Active status")


class PlaybookDefinitionOut(BaseModel):
    """Schema for playbook definition output."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: str
    description: str | None
    dag: DAGSchema = Field(..., alias="dag_json")
    created_by_user_id: str | None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    # v0.7.3: Version management fields
    status: str = Field(
        "draft", description="Playbook status (draft/published/archived)"
    )
    published_at: datetime | None = Field(
        None, description="When this was published"
    )
    current_version_no: int = Field(1, description="Current version number")

    # Computed fields
    node_count: int = Field(0, description="Number of nodes")
    edge_count: int = Field(0, description="Number of edges")
    version_count: int = Field(0, description="Number of versions")


# Run schemas
class PlaybookRunCreate(BaseModel):
    """Schema for creating a playbook run."""

    mode: Literal["dry_run", "apply"] = Field("dry_run", description="Execution mode")
    input_context: dict[str, Any] = Field(
        default_factory=dict, description="Initial input context"
    )
    failure_strategy: Literal["fail_fast", "continue"] = Field(
        "fail_fast", description="Failure handling strategy"
    )


class NodeRunStatus(BaseModel):
    """Node run status."""

    node_id: str
    node_name: str
    node_type: str
    status: Literal["pending", "running", "success", "failed", "skipped", "cancelled"]
    started_at: datetime | None
    finished_at: datetime | None
    attempt_count: int
    last_error: str | None
    output: dict[str, Any] = Field(default_factory=dict, alias="output_json")
    input: dict[str, Any] = Field(default_factory=dict, alias="input_json")


class NodeAttemptOut(BaseModel):
    """Schema for node attempt output."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    node_run_id: str
    attempt_no: int
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    log_text: str | None
    output: dict[str, Any] = Field(default_factory=dict, alias="output_json")
    error: str | None = Field(None, alias="error_text")


class NodeRunWithAttempts(NodeRunStatus):
    """Node run with attempts."""

    attempts: list[NodeAttemptOut] = Field(default_factory=list)


class PlaybookRunStatus(BaseModel):
    """Detailed playbook run status."""

    id: str
    playbook_name: str
    playbook_version: str
    engine_version: str
    mode: str
    status: str
    failure_strategy: str
    started_at: datetime
    finished_at: datetime | None
    error_message: str | None

    # DAG-specific fields
    definition_id: str | None
    execution_mode: str

    # Node runs summary
    node_runs: list[NodeRunStatus] = Field(default_factory=list)
    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0
    running_nodes: int = 0
    pending_nodes: int = 0

    # Control flags
    cancel_requested: bool = False
    can_resume: bool = False


# Cancel/Resume schemas
class PlaybookRunCancel(BaseModel):
    """Schema for cancelling a run."""

    reason: str | None = Field(None, description="Cancellation reason")


class PlaybookRunResume(BaseModel):
    """Schema for resuming a run."""

    from_node_id: str | None = Field(
        None, description="Resume from specific node (null = from failed)"
    )


# Response wrappers
class PlaybookDefinitionListResponse(BaseModel):
    """Response for playbook definitions list."""

    items: list[PlaybookDefinitionOut]
    total: int
    page: int
    page_size: int


class PlaybookRunResponse(BaseModel):
    """Response for playbook run creation."""

    run_id: str
    status: str
    message: str


class PlaybookNodeRunsResponse(BaseModel):
    """Response for node runs list."""

    run_id: str
    node_runs: list[NodeRunWithAttempts]
    total: int


# v0.7.3: Version Management Schemas
class PlaybookDefinitionVersionOut(BaseModel):
    """Schema for playbook definition version output."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    playbook_definition_id: str
    version_no: int
    dag_json: dict[str, Any]
    name: str | None
    description: str | None
    created_by_user_id: str | None
    created_at: datetime
    change_note: str | None


class PlaybookDefinitionPublish(BaseModel):
    """Schema for publishing a playbook definition."""

    change_note: str | None = Field(None, description="Change note for this version")


class PlaybookDefinitionRestore(BaseModel):
    """Schema for restoring a playbook definition from version."""

    change_note: str | None = Field(
        None, description="Change note for the restoration"
    )


class PlaybookVersionListResponse(BaseModel):
    """Response for version history list."""

    definition_id: str
    versions: list[PlaybookDefinitionVersionOut]
    total: int
    current_version_no: int


# v0.7.3: Replay Schemas
class PlaybookRunReplay(BaseModel):
    """Schema for replaying a playbook run."""

    mode: Literal["dry_run", "apply"] = Field(
        "dry_run", description="Execution mode for replay"
    )
    override_context: dict[str, Any] | None = Field(
        None, description="Optional context overrides"
    )


class PlaybookRunReplayResponse(BaseModel):
    """Response for replay creation."""

    run_id: str
    original_run_id: str
    mode: str
    status: str
    message: str


class ReplayChainNode(BaseModel):
    """Node in replay chain."""

    run_id: str
    playbook_name: str
    mode: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    replay_of_run_id: str | None


class ReplayChainResponse(BaseModel):
    """Response for replay chain."""

    root_run_id: str
    chain: list[ReplayChainNode]
    total: int
    depth: int


# v0.7.3: Context Variable Schemas
class ContextVariableReference(BaseModel):
    """Schema for context variable reference."""

    reference: str = Field(
        ...,
        description="Variable reference (e.g., 'context.xxx', 'input.xxx', 'node.<node_id>.field')",
    )
    value: Any = Field(..., description="Resolved value")


class ContextRenderRequest(BaseModel):
    """Schema for rendering context variables."""

    template: str = Field(
        ..., description="Template string with {{variable}} placeholders"
    )
    context: dict[str, Any] = Field(..., description="Current context")


class ContextRenderResponse(BaseModel):
    """Response for context rendering."""

    rendered: str
    used_variables: list[str]


class PlaybookRunContextOut(BaseModel):
    """Schema for playbook run context output."""

    run_id: str
    input_context: dict[str, Any]
    context: dict[str, Any]
    node_outputs: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Node outputs mapped to context"
    )


# v0.7.3: Import/Export Schemas
class PlaybookExportFormat(BaseModel):
    """Schema for playbook export format."""

    format: Literal["json", "yaml"] = Field("json", description="Export format")


class PlaybookImportRequest(BaseModel):
    """Schema for playbook import."""

    format: Literal["json", "yaml"] = Field("json", description="Import format")
    content: str = Field(..., description="Playbook definition content")
    name: str | None = Field(None, description="Override playbook name (optional)")
    publish: bool = Field(
        False, description="Auto-publish after import (default: draft)"
    )


class PlaybookExportData(BaseModel):
    """Schema for playbook export data."""

    name: str
    description: str | None
    version: str
    status: str
    current_version_no: int
    dag: DAGSchema
    created_at: datetime
    updated_at: datetime
    created_by_user_id: str | None


class PlaybookImportResponse(BaseModel):
    """Response for playbook import."""

    definition_id: str
    name: str
    version: str
    status: str
    message: str
