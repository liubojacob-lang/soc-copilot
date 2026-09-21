"""Marketplace schemas for API request/response."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MarketplacePlaybookCreate(BaseModel):
    """Request to publish a playbook to marketplace."""

    source_definition_id: str = Field(
        ..., description="Local playbook definition ID to publish"
    )
    category: str = Field(..., description="Playbook category")
    difficulty: str = Field(default="intermediate", description="Difficulty level")
    tags: list[str] = Field(default_factory=list, description="Tags for search")
    required_plugins: list[str] = Field(default_factory=list)
    compatible_versions: list[str] = Field(default_factory=list)


class MarketplacePlaybookResponse(BaseModel):
    """Marketplace playbook response."""

    id: str
    name: str
    description: str | None
    version: str
    category: str
    difficulty: str
    tags: list[str]
    author_id: str | None
    author_name: str

    status: str
    verified: bool
    featured: bool

    download_count: int
    rating_average: float
    rating_count: int
    review_count: int

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MarketplacePlaybookDetail(MarketplacePlaybookResponse):
    """Detailed playbook with DAG and documentation."""

    dag_json: dict[str, Any]
    documentation: str | None
    required_plugins: list[str]
    compatible_versions: list[str]
    source_definition_id: str | None


class MarketplaceReviewCreate(BaseModel):
    """Request to submit a review."""

    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    comment: str = Field(
        ..., min_length=10, max_length=1000, description="Review comment"
    )


class MarketplaceReviewResponse(BaseModel):
    """Review response."""

    id: str
    playbook_id: str
    user_id: str | None
    username: str
    rating: int
    comment: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketplaceApprovalRequest(BaseModel):
    """Admin approval request."""

    approved: bool = Field(..., description="Approve or reject")
    review_note: str | None = Field(None, description="Optional review note")
    featured: bool = Field(
        default=False, description="Mark as featured (only if approved)"
    )
    verified: bool = Field(
        default=False, description="Mark as verified (only if approved)"
    )


class MarketplaceStats(BaseModel):
    """Marketplace statistics."""

    total_playbooks: int
    pending_review: int
    approved: int
    rejected: int
    featured: int
    verified: int
    total_downloads: int
    total_reviews: int


class ExternalPlaybookSearchItem(BaseModel):
    """External playbook search result item from online sources."""

    id: str
    title: str
    repository: str
    source_platform: str  # "Cortex XSOAR", "Splunk SOAR", "Shuffle SOAR", "Microsoft Sentinel", "CISA"
    description: str
    stars: int = 0
    url: str
    raw_url: str | None = None
    category: str = "malware_response"
    difficulty: str = "intermediate"
    tags: list[str] = Field(default_factory=list)
    standard: str | None = None


class ExternalPlaybookAdaptRequest(BaseModel):
    """Request to adapt an external playbook by URL or raw content."""

    url: str | None = None
    content: str | None = None
    title_hint: str | None = None
    source_platform: str | None = None


class ExternalPlaybookImportRequest(BaseModel):
    """Request to import an adapted playbook into local definitions or marketplace."""

    playbook_data: dict[str, Any]
    target: str = "local"  # "local" | "marketplace"
