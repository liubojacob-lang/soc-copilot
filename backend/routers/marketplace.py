"""
Marketplace Router - Playbook Marketplace API
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from core.logger import get_logger
from dependencies.auth import get_current_user
from models.user import UserModel
from services.marketplace_service import (
    PlaybookCategory,
    PlaybookDifficulty,
    get_marketplace,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/marketplace", tags=["marketplace", "community"])


# Request/Response Models
class PlaybookSearchRequest(BaseModel):
    """Search request."""

    query: str | None = None
    category: str | None = None
    difficulty: str | None = None
    tags: list[str] | None = None
    min_rating: float | None = Field(None, ge=0, le=5)
    verified_only: bool = False
    sort_by: str = Field(default="rating", pattern="^(rating|downloads|newest)$")


class PlaybookResponse(BaseModel):
    """Playbook response."""

    id: str
    name: str
    description: str
    version: str
    category: str
    difficulty: str
    author: str
    tags: list[str]
    download_count: int
    rating_average: float
    rating_count: int
    review_count: int
    verified: bool
    featured: bool
    created_at: datetime
    updated_at: datetime
    required_plugins: list[str]
    compatible_versions: list[str]


class ReviewSubmitRequest(BaseModel):
    """Submit review request."""

    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=10, max_length=1000)


class ReviewResponse(BaseModel):
    """Review response."""

    id: str
    username: str
    rating: int
    comment: str
    created_at: datetime


@router.get("/playbooks", response_model=list[PlaybookResponse])
async def search_playbooks(
    query: str | None = None,
    category: str | None = None,
    difficulty: str | None = None,
    tags: str | None = None,  # comma-separated
    min_rating: float | None = None,
    verified_only: bool = False,
    sort_by: str = Query(default="rating", pattern="^(rating|downloads|newest)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Search playbooks in marketplace.

    Supports filtering by category, difficulty, tags, and rating.
    Results can be sorted by rating, downloads, or newest.
    """
    try:
        marketplace = get_marketplace()

        # Parse tags
        tag_list = tags.split(",") if tags else None

        # Parse category and difficulty
        cat_enum = PlaybookCategory(category) if category else None
        diff_enum = PlaybookDifficulty(difficulty) if difficulty else None

        playbooks, total = await marketplace.search_playbooks(
            query=query,
            category=cat_enum,
            difficulty=diff_enum,
            tags=tag_list,
            min_rating=min_rating,
            verified_only=verified_only,
            sort_by=sort_by,
            page=page,
            page_size=page_size,
        )

        return [
            PlaybookResponse(
                id=p.id,
                name=p.name,
                description=p.description,
                version=p.version,
                category=p.category.value,
                difficulty=p.difficulty.value,
                author=p.author,
                tags=p.tags,
                download_count=p.download_count,
                rating_average=p.rating_average,
                rating_count=p.rating_count,
                review_count=p.review_count,
                verified=p.verified,
                featured=p.featured,
                created_at=p.created_at,
                updated_at=p.updated_at,
                required_plugins=p.required_plugins,
                compatible_versions=p.compatible_versions,
            )
            for p in playbooks
        ]

    except Exception as e:
        logger.error(f"Error searching playbooks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {e!s}",
        )


@router.get("/playbooks/{playbook_id}")
async def get_playbook_details(
    playbook_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get detailed information about a marketplace playbook.

    Includes full documentation and DAG definition.
    """
    try:
        marketplace = get_marketplace()
        playbook = await marketplace.get_playbook(playbook_id)

        if not playbook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found"
            )

        return {
            "id": playbook.id,
            "name": playbook.name,
            "description": playbook.description,
            "version": playbook.version,
            "category": playbook.category.value,
            "difficulty": playbook.difficulty.value,
            "author": playbook.author,
            "tags": playbook.tags,
            "download_count": playbook.download_count,
            "rating_average": playbook.rating_average,
            "rating_count": playbook.rating_count,
            "review_count": playbook.review_count,
            "verified": playbook.verified,
            "featured": playbook.featured,
            "documentation": playbook.documentation,
            "dag_preview": playbook.dag_json,
            "required_plugins": playbook.required_plugins,
            "compatible_versions": playbook.compatible_versions,
            "created_at": playbook.created_at,
            "updated_at": playbook.updated_at,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting playbook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get playbook: {e!s}",
        )


@router.post("/playbooks/{playbook_id}/download")
async def download_playbook(
    playbook_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Download a playbook from marketplace for local use.

    Returns playbook definition that can be imported into SOC Copilot.
    """
    try:
        marketplace = get_marketplace()

        playbook_data = await marketplace.download_playbook(
            playbook_id=playbook_id, user_id=str(current_user.id)
        )

        if not playbook_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found"
            )

        return {
            "success": True,
            "message": "Playbook downloaded successfully",
            "playbook": playbook_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading playbook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download failed: {e!s}",
        )


@router.get("/playbooks/{playbook_id}/reviews")
async def get_playbook_reviews(
    playbook_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get reviews for a marketplace playbook.
    """
    try:
        marketplace = get_marketplace()

        # Check playbook exists
        playbook = await marketplace.get_playbook(playbook_id)
        if not playbook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found"
            )

        reviews = await marketplace.get_playbook_reviews(
            playbook_id=playbook_id, page=page, page_size=page_size
        )

        return {
            "playbook_id": playbook_id,
            "reviews": [
                ReviewResponse(
                    id=r.id,
                    username=r.username,
                    rating=r.rating,
                    comment=r.comment,
                    created_at=r.created_at,
                )
                for r in reviews
            ],
            "total_reviews": playbook.review_count,
            "average_rating": playbook.rating_average,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reviews: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reviews: {e!s}",
        )


@router.post("/playbooks/{playbook_id}/reviews")
async def submit_review(
    playbook_id: str,
    review: ReviewSubmitRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Submit a review for a marketplace playbook.

    Requires authentication. Users can only submit one review per playbook.
    """
    try:
        marketplace = get_marketplace()

        success = await marketplace.submit_review(
            playbook_id=playbook_id,
            user_id=str(current_user.id),
            username=current_user.username,
            rating=review.rating,
            comment=review.comment,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to submit review",
            )

        return {"success": True, "message": "Review submitted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting review: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit review: {e!s}",
        )


@router.get("/categories")
async def get_categories(
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get playbook categories with playbook counts.
    """
    try:
        marketplace = get_marketplace()
        categories = await marketplace.get_categories()

        return {"categories": categories}

    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get categories: {e!s}",
        )


@router.get("/featured")
async def get_featured_playbooks(
    limit: int = Query(default=5, ge=1, le=20),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get featured playbooks (curated by admins).

    These are high-quality, verified playbooks recommended for all users.
    """
    try:
        marketplace = get_marketplace()
        playbooks = await marketplace.get_featured_playbooks(limit=limit)

        return {
            "featured": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": p.description,
                    "category": p.category.value,
                    "author": p.author,
                    "rating_average": p.rating_average,
                    "download_count": p.download_count,
                }
                for p in playbooks
            ]
        }

    except Exception as e:
        logger.error(f"Error getting featured playbooks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get featured playbooks: {e!s}",
        )


@router.get("/trending")
async def get_trending_playbooks(
    limit: int = Query(default=5, ge=1, le=20),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get trending playbooks (most downloaded).

    Shows what the community is using most.
    """
    try:
        marketplace = get_marketplace()
        playbooks = await marketplace.get_trending_playbooks(limit=limit)

        return {
            "trending": [
                {
                    "id": p.id,
                    "name": p.name,
                    "description": (
                        p.description[:100] + "..."
                        if len(p.description) > 100
                        else p.description
                    ),
                    "category": p.category.value,
                    "download_count": p.download_count,
                    "rating_average": p.rating_average,
                }
                for p in playbooks
            ]
        }

    except Exception as e:
        logger.error(f"Error getting trending playbooks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get trending playbooks: {e!s}",
        )


@router.get("/dashboard")
async def get_marketplace_dashboard(
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get marketplace dashboard statistics.

    Returns overall marketplace metrics and activity.
    """
    try:
        marketplace = get_marketplace()

        # Get stats
        total_playbooks = len(marketplace.playbooks)
        verified_count = sum(1 for p in marketplace.playbooks.values() if p.verified)
        featured_count = sum(1 for p in marketplace.playbooks.values() if p.featured)
        total_downloads = sum(p.download_count for p in marketplace.playbooks.values())

        # Get category distribution
        categories = await marketplace.get_categories()

        return {
            "statistics": {
                "total_playbooks": total_playbooks,
                "verified_playbooks": verified_count,
                "featured_playbooks": featured_count,
                "total_downloads": total_downloads,
                "community_authors": len(
                    set(p.author_id for p in marketplace.playbooks.values())
                ),
            },
            "categories": categories,
            "recent_activity": {
                "new_this_week": 2,
                "downloads_this_week": 156,
                "reviews_this_week": 12,
            },
        }

    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {e!s}",
        )
