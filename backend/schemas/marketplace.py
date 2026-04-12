"""Marketplace schemas for API request/response."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from models.marketplace import MarketplacePlaybookStatus


class MarketplacePlaybookCreate(BaseModel):
    """Request to publish a playbook to marketplace."""

    source_definition_id: str = Field(..., description="Local playbook definition ID to publish")
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
    comment: str = Field(..., min_length=10, max_length=1000, description="Review comment")


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
    featured: bool = Field(default=False, description="Mark as featured (only if approved)")
    verified: bool = Field(default=False, description="Mark as verified (only if approved)")


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
