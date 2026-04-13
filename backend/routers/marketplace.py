"""Marketplace Router - Playbook Marketplace API with DB persistence."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from dependencies.authorization import require_admin
from models.user import UserModel
from repositories.marketplace_repository import MarketplaceRepository
from repositories.playbook_definition_repository import PlaybookDefinitionRepository
from schemas.marketplace import (
    MarketplaceApprovalRequest,
    MarketplacePlaybookCreate,
    MarketplacePlaybookDetail,
    MarketplacePlaybookResponse,
    MarketplaceReviewCreate,
    MarketplaceReviewResponse,
    MarketplaceStats,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/marketplace", tags=["marketplace", "community"])


def get_marketplace_repo(db: AsyncSession = Depends(get_session)) -> MarketplaceRepository:
    return MarketplaceRepository(db)


def get_playbook_repo(db: AsyncSession = Depends(get_session)) -> PlaybookDefinitionRepository:
    return PlaybookDefinitionRepository(db)


@router.get("/playbooks", response_model=dict)
async def search_playbooks(
    query: str | None = None,
    category: str | None = None,
    difficulty: str | None = None,
    min_rating: float | None = Query(None, ge=0, le=5),
    verified_only: bool = False,
    sort_by: str = Query(default="rating", pattern="^(rating|downloads|newest)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    current_user: UserModel = Depends(get_current_user),
):
    """Search playbooks in marketplace."""
    playbooks, total = await repo.get_playbooks(
        query=query,
        category=category,
        difficulty=difficulty,
        min_rating=min_rating,
        verified_only=verified_only,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )
    return {
        "playbooks": [MarketplacePlaybookResponse.model_validate(p) for p in playbooks],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/playbooks/{playbook_id}", response_model=MarketplacePlaybookDetail)
async def get_playbook(
    playbook_id: str,
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    current_user: UserModel = Depends(get_current_user),
):
    """Get detailed playbook information."""
    playbook = await repo.get_playbook(playbook_id)
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return MarketplacePlaybookDetail.model_validate(playbook)


@router.post("/publish", response_model=MarketplacePlaybookResponse, status_code=201)
async def publish_playbook(
    request: MarketplacePlaybookCreate,
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    playbook_repo: PlaybookDefinitionRepository = Depends(get_playbook_repo),
    current_user: UserModel = Depends(get_current_user),
):
    """Publish a local playbook to marketplace (pending approval)."""
    definition = await playbook_repo.get_by_id(request.source_definition_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Playbook definition not found")

    if definition.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="You can only publish your own playbooks")

    playbook = await repo.create_playbook(
        definition=definition,
        data=request,
        author_id=current_user.id,
        author_name=current_user.username or current_user.email,
    )
    logger.info(f"User {current_user.id} published playbook {playbook.id} for review")
    return MarketplacePlaybookResponse.model_validate(playbook)


@router.post("/playbooks/{playbook_id}/download", response_model=dict)
async def download_playbook(
    playbook_id: str,
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    playbook_repo: PlaybookDefinitionRepository = Depends(get_playbook_repo),
    current_user: UserModel = Depends(get_current_user),
):
    """Download and import a marketplace playbook to local definitions."""
    playbook = await repo.get_playbook(playbook_id)
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    if not playbook.is_visible:
        raise HTTPException(status_code=404, detail="Playbook not found")

    await repo.increment_download(playbook_id)

    imported = await playbook_repo.create(
        name=f"[Marketplace] {playbook.name}",
        description=playbook.description,
        version=playbook.version,
        dag_json=playbook.dag_json,
        created_by_user_id=current_user.id,
    )

    logger.info(f"User {current_user.id} downloaded playbook {playbook_id} as {imported.id}")

    return {
        "success": True,
        "message": "Playbook imported successfully",
        "local_definition_id": imported.id,
        "playbook_name": imported.name,
    }


@router.get("/playbooks/{playbook_id}/reviews", response_model=dict)
async def get_reviews(
    playbook_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    current_user: UserModel = Depends(get_current_user),
):
    """Get reviews for a playbook."""
    playbook = await repo.get_playbook(playbook_id)
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    reviews = await repo.get_reviews(playbook_id, page=page_size, page_size=page_size)
    return {
        "reviews": [MarketplaceReviewResponse.model_validate(r) for r in reviews],
        "page": page,
        "page_size": page_size,
    }


@router.post(
    "/playbooks/{playbook_id}/reviews", response_model=MarketplaceReviewResponse, status_code=201
)
async def submit_review(
    playbook_id: str,
    request: MarketplaceReviewCreate,
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    current_user: UserModel = Depends(get_current_user),
):
    """Submit a review for a playbook."""
    review = await repo.create_review(
        playbook_id=playbook_id,
        user_id=current_user.id,
        username=current_user.username or current_user.email,
        data=request,
    )
    if not review:
        raise HTTPException(
            status_code=400, detail="Cannot submit review (playbook not found or already reviewed)"
        )
    return MarketplaceReviewResponse.model_validate(review)


@router.get("/categories", response_model=list[dict])
async def get_categories(
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    current_user: UserModel = Depends(get_current_user),
):
    """Get playbook categories with counts."""
    return await repo.get_categories()


@router.get("/featured", response_model=list[MarketplacePlaybookResponse])
async def get_featured(
    limit: int = Query(5, ge=1, le=20),
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    current_user: UserModel = Depends(get_current_user),
):
    """Get featured playbooks."""
    playbooks = await repo.get_featured(limit=limit)
    return [MarketplacePlaybookResponse.model_validate(p) for p in playbooks]


@router.get("/trending", response_model=list[MarketplacePlaybookResponse])
async def get_trending(
    limit: int = Query(5, ge=1, le=20),
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    current_user: UserModel = Depends(get_current_user),
):
    """Get trending playbooks."""
    playbooks = await repo.get_trending(limit=limit)
    return [MarketplacePlaybookResponse.model_validate(p) for p in playbooks]


@router.get("/dashboard", response_model=MarketplaceStats)
async def get_dashboard(
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    current_user: UserModel = Depends(get_current_user),
):
    """Get marketplace statistics."""
    stats = await repo.get_stats()
    return MarketplaceStats(**stats)


# Admin endpoints


@router.get("/admin/pending", response_model=dict)
async def get_pending_playbooks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    current_user: UserModel = Depends(require_admin),
):
    """Get playbooks pending review (admin only)."""
    playbooks, total = await repo.get_playbooks(
        status="pending",
        sort_by="newest",
        page=page,
        page_size=page_size,
    )
    return {
        "playbooks": [MarketplacePlaybookResponse.model_validate(p) for p in playbooks],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/admin/playbooks/{playbook_id}/review", response_model=MarketplacePlaybookResponse)
async def review_playbook(
    playbook_id: str,
    request: MarketplaceApprovalRequest,
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    current_user: UserModel = Depends(require_admin),
):
    """Approve or reject a playbook (admin only)."""
    playbook = await repo.approve_playbook(
        playbook_id=playbook_id,
        reviewer_id=current_user.id,
        approved=request.approved,
        review_note=request.review_note,
        featured=request.featured,
        verified=request.verified,
    )
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    action = "approved" if request.approved else "rejected"
    logger.info(f"Admin {current_user.id} {action} playbook {playbook_id}")

    return MarketplacePlaybookResponse.model_validate(playbook)


@router.get("/admin/stats", response_model=MarketplaceStats)
async def get_admin_stats(
    repo: MarketplaceRepository = Depends(get_marketplace_repo),
    current_user: UserModel = Depends(require_admin),
):
    """Get full marketplace statistics including pending (admin only)."""
    stats = await repo.get_stats()
    return MarketplaceStats(**stats)
