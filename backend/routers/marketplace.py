"""Marketplace Router - Playbook Marketplace API with DB persistence."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user, require_admin
from models.marketplace import (
    MarketplacePlaybookModel,
    MarketplacePlaybookStatus,
)
from models.user import UserModel
from repositories.marketplace_repository import MarketplaceRepository
from repositories.playbook_definition_repository import PlaybookDefinitionRepository
from schemas.marketplace import (
    ExternalPlaybookAdaptRequest,
    ExternalPlaybookImportRequest,
    ExternalPlaybookSearchItem,
    MarketplaceApprovalRequest,
    MarketplacePlaybookCreate,
    MarketplacePlaybookDetail,
    MarketplacePlaybookResponse,
    MarketplaceReviewCreate,
    MarketplaceReviewResponse,
    MarketplaceStats,
)
from services.external_playbook_service import (
    adapt_playbook_with_ai,
    fetch_source_content,
    search_online_playbooks,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/marketplace", tags=["marketplace", "community"])


def get_marketplace_repo(
    db: AsyncSession = Depends(get_session),
) -> MarketplaceRepository:
    return MarketplaceRepository(db)


def get_playbook_repo(
    db: AsyncSession = Depends(get_session),
) -> PlaybookDefinitionRepository:
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
        raise HTTPException(
            status_code=403, detail="You can only publish your own playbooks"
        )

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
    await playbook_repo.session.commit()

    logger.info(
        f"User {current_user.id} downloaded playbook {playbook_id} as {imported.id}"
    )

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
    "/playbooks/{playbook_id}/reviews",
    response_model=MarketplaceReviewResponse,
    status_code=201,
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
            status_code=400,
            detail="Cannot submit review (playbook not found or already reviewed)",
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


# External Playbook Integration Endpoints


@router.get("/external/search", response_model=list[ExternalPlaybookSearchItem])
async def search_external(
    query: str = Query(default=""),
    limit: int = Query(default=12, ge=1, le=50),
    current_user: UserModel = Depends(get_current_user),
):
    """Search external open-source SOAR playbook repositories."""
    return await search_online_playbooks(query=query, limit=limit)


@router.post("/external/adapt", response_model=dict)
async def adapt_external(
    req: ExternalPlaybookAdaptRequest,
    current_user: UserModel = Depends(require_admin),
):
    """Fetch external playbook content and adapt it into standard DAG using AI (admin only)."""
    if not req.url and not req.content:
        raise HTTPException(
            status_code=400, detail="Either 'url' or 'content' must be provided"
        )

    raw_content = req.content
    if req.url:
        try:
            raw_content = await fetch_source_content(req.url, title_hint=req.title_hint)
        except ValueError as ssrf_exc:
            raise HTTPException(
                status_code=400, detail=f"URL blocked by security policy: {ssrf_exc}"
            )
        except Exception as e:
            logger.warning(
                f"Error fetching external URL {req.url}: {e}, using synthesized fallback"
            )
            raw_content = f"# Playbook: {req.title_hint or 'External Playbook'}\n# Source: {req.url}"

    if not raw_content or not raw_content.strip():
        raw_content = (
            f"# Playbook: {req.title_hint or 'Security Incident Response Playbook'}"
        )

    adapted = await adapt_playbook_with_ai(
        raw_content=raw_content,
        title_hint=req.title_hint,
        source_platform=req.source_platform,
    )
    return adapted


@router.post("/external/import", response_model=dict)
async def import_external(
    req: ExternalPlaybookImportRequest,
    playbook_repo: PlaybookDefinitionRepository = Depends(get_playbook_repo),
    marketplace_repo: MarketplaceRepository = Depends(get_marketplace_repo),
    current_user: UserModel = Depends(require_admin),
):
    """Import adapted playbook into local definitions or community marketplace (admin only).

    Security (G7): When target is 'marketplace', the entry is created with
    status=PENDING and verified=False so it must pass admin review before
    becoming publicly visible.
    """
    data = req.playbook_data
    name = data.get("name") or "Adapted Playbook"
    description = data.get("description")
    version = data.get("version") or "1.0.0"

    # Validate DAG structure before persisting
    dag_json = data.get("dag_json") or {}
    if not isinstance(dag_json, dict):
        raise HTTPException(
            status_code=400, detail="playbook_data.dag_json must be an object"
        )
    nodes = dag_json.get("nodes")
    edges = dag_json.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise HTTPException(
            status_code=400,
            detail="playbook_data.dag_json must contain 'nodes' and 'edges' lists",
        )
    # Guard against suspiciously large payloads
    if len(nodes) > 200 or len(edges) > 500:
        raise HTTPException(
            status_code=400, detail="DAG exceeds allowed node/edge limits"
        )

    # 1. Always save to local definitions so user can immediately view, edit, and run
    imported_def = await playbook_repo.create(
        name=f"[External] {name}",
        description=description,
        version=version,
        dag_json=dag_json,
        created_by_user_id=current_user.id,
        is_active=True,
    )
    await playbook_repo.session.commit()

    # 2. If target is marketplace, publish as PENDING (requires admin review)
    marketplace_id = None
    if req.target == "marketplace":
        mp_playbook = MarketplacePlaybookModel(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            version=version,
            category=data.get("category", "custom"),
            difficulty=data.get("difficulty", "intermediate"),
            tags=data.get("tags", []),
            author_id=current_user.id,
            author_name=data.get("author_name") or current_user.username or "Community",
            source_definition_id=imported_def.id,
            dag_json=dag_json,
            documentation=data.get("documentation"),
            # G7: Force PENDING + unverified — admin review required before public visibility
            status=MarketplacePlaybookStatus.PENDING,
            verified=False,
            required_plugins=data.get("required_plugins", []),
            compatible_versions=["1.0.0"],
        )
        marketplace_repo.session.add(mp_playbook)
        await marketplace_repo.session.commit()
        marketplace_id = mp_playbook.id
        logger.info(
            f"Admin {current_user.id} imported external playbook {marketplace_id} "
            f"into marketplace as PENDING (requires review)"
        )

    return {
        "success": True,
        "message": "Playbook imported successfully",
        "local_definition_id": imported_def.id,
        "marketplace_id": marketplace_id,
        "marketplace_status": "pending_review" if marketplace_id else None,
        "playbook_name": imported_def.name,
    }


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


@router.post(
    "/admin/playbooks/{playbook_id}/review", response_model=MarketplacePlaybookResponse
)
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
