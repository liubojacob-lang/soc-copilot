"""Schemas for case management."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# ── Enums ──────────────────────────────────────────────────────────


class CaseSeverity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class CaseStatus(str, Enum):
    new = "new"
    investigating = "investigating"
    pending_review = "pending_review"
    resolved = "resolved"
    closed = "closed"


# Valid status transitions
VALID_TRANSITIONS: dict[CaseStatus, list[CaseStatus]] = {
    CaseStatus.new: [CaseStatus.investigating, CaseStatus.closed],
    CaseStatus.investigating: [
        CaseStatus.pending_review,
        CaseStatus.resolved,
        CaseStatus.closed,
    ],
    CaseStatus.pending_review: [CaseStatus.resolved, CaseStatus.closed],
    CaseStatus.resolved: [CaseStatus.closed],
    CaseStatus.closed: [],  # Terminal state
}


# ── Comment Schemas ────────────────────────────────────────────────


class CommentCreate(BaseModel):
    """Schema for creating a comment."""

    content: str = Field(..., min_length=1, max_length=5000)


class CommentResponse(BaseModel):
    """Schema for comment response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    user_id: str
    username: str
    content: str
    created_at: datetime
    updated_at: datetime


# ── Timeline Entry Schemas ─────────────────────────────────────────


class TimelineEntryResponse(BaseModel):
    """Schema for timeline entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    entry_type: str
    summary: str
    source_alert_id: int | None = None
    performed_by: str | None = None
    occurred_at: datetime
    metadata_json: str | None = None


# ── Case Schemas ───────────────────────────────────────────────────


class CaseBase(BaseModel):
    """Base case schema."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    severity: CaseSeverity = Field(default=CaseSeverity.medium)
    status: CaseStatus = Field(default=CaseStatus.new)


class CaseCreate(CaseBase):
    """Schema for creating a case."""

    assigned_to: str | None = None
    sla_due_at: datetime | None = None


class CaseUpdate(BaseModel):
    """Schema for updating a case."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    severity: CaseSeverity | None = None
    assigned_to: str | None = None
    sla_due_at: datetime | None = None
    resolution: str | None = None


class CaseStatusUpdate(BaseModel):
    """Schema for updating case status."""

    status: CaseStatus
    resolution: str | None = None


class CaseAssign(BaseModel):
    """Schema for assigning a case to an analyst."""

    assigned_to: str = Field(..., min_length=1)


class CaseAlertLink(BaseModel):
    """Schema for linking alert IDs to a case."""

    alert_ids: list[int] = Field(..., min_length=1, max_length=50)


class CaseResponse(BaseModel):
    """Schema for case response (without nested relations)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None = None
    severity: str
    status: str
    assigned_to: str | None = None
    sla_due_at: datetime | None = None
    resolution: str | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    # Counts (populated by service)
    alert_count: int = 0
    comment_count: int = 0


class CaseDetailResponse(CaseResponse):
    """Schema for detailed case response (includes nested relations)."""

    alerts: list[dict] = Field(default_factory=list)
    timeline_entries: list[TimelineEntryResponse] = Field(default_factory=list)
    comments: list[CommentResponse] = Field(default_factory=list)
    assignee: dict | None = None


class CaseListResponse(BaseModel):
    """Schema for case list response."""

    items: list[CaseResponse]
    total: int
    page: int = 1
    page_size: int = 20


class CaseStatsResponse(BaseModel):
    """Schema for case statistics."""

    total: int
    by_status: dict[str, int]
    by_severity: dict[str, int]
    open_cases: int
    overdue_cases: int
    resolved_today: int = 0
    avg_resolution_hours: float | None = None


# ── Batch Operations ──────────────────────────────────────────────


class BatchCaseStatusUpdate(BaseModel):
    """Schema for batch case status update."""

    case_ids: list[str] = Field(..., min_length=1, max_length=200)
    status: CaseStatus = Field(..., description="Target status for all cases")
    resolution: str | None = Field(
        None, description="Resolution note (for resolved/closed)"
    )


class BatchCaseAssign(BaseModel):
    """Schema for batch case assignment."""

    case_ids: list[str] = Field(..., min_length=1, max_length=200)
    assigned_to: str = Field(..., min_length=1)


class BatchCaseResult(BaseModel):
    """Schema for batch operation result per case."""

    case_id: str
    success: bool
    title: str | None = None
    error: str | None = None


class BatchCaseResponse(BaseModel):
    """Response for batch case operations."""

    total: int = Field(..., description="Total items submitted")
    success_count: int = Field(..., description="Number of successful operations")
    failed_count: int = Field(..., description="Number of failed operations")
    results: list[BatchCaseResult] = Field(
        default_factory=list, description="Per-case results"
    )
    errors: list[dict] = Field(
        default_factory=list,
        description="Error details for failed items [{case_id, error}]",
    )
