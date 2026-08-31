"""Cases router for case management API.

Provides endpoints for creating, listing, updating, and managing
security investigation cases with alert linking, comments, and
status transitions.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user, require_admin, require_analyst_or_admin
from models.user import UserModel
from schemas.case import (
    CaseAlertLink,
    CaseAssign,
    CaseCreate,
    CaseDetailResponse,
    CaseListResponse,
    CaseResponse,
    CaseStatsResponse,
    CaseStatusUpdate,
    CaseUpdate,
    CommentCreate,
    CommentResponse,
)
from services.case_service import CaseService

router = APIRouter(prefix="/api/v1/cases", tags=["Cases"])
logger = get_logger(__name__)


# ── CRUD ───────────────────────────────────────────────────────────


@router.post("", response_model=CaseDetailResponse, status_code=201)
async def create_case(
    data: CaseCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_analyst_or_admin),
) -> CaseDetailResponse:
    """Create a new investigation case."""
    try:
        service = CaseService(session)
        return await service.create(data, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=CaseListResponse)
async def list_cases(
    status: str | None = Query(None, description="Filter by status"),
    severity: str | None = Query(None, description="Filter by severity"),
    assigned_to: str | None = Query(None, description="Filter by assignee"),
    search: str | None = Query(None, description="Search in title/description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_desc: bool = Query(True, description="Sort descending"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> CaseListResponse:
    """List cases with filtering and pagination."""
    service = CaseService(session)
    return await service.list_cases(
        status=status,
        severity=severity,
        assigned_to=assigned_to,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_desc=sort_desc,
    )


@router.get("/stats", response_model=CaseStatsResponse)
async def get_case_stats(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> CaseStatsResponse:
    """Get case statistics for dashboard."""
    service = CaseService(session)
    return await service.get_stats()


@router.get("/{case_id}", response_model=CaseDetailResponse)
async def get_case(
    case_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> CaseDetailResponse:
    """Get case detail with alerts, timeline, and comments."""
    service = CaseService(session)
    case = await service.get_by_id(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.put("/{case_id}", response_model=CaseDetailResponse)
async def update_case(
    case_id: str,
    data: CaseUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_analyst_or_admin),
) -> CaseDetailResponse:
    """Update a case."""
    try:
        service = CaseService(session)
        return await service.update(case_id, data, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{case_id}", status_code=204)
async def delete_case(
    case_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_admin),
) -> None:
    """Delete a case."""
    try:
        service = CaseService(session)
        await service.delete(case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Case not found")


# ── Status Management ──────────────────────────────────────────────


@router.patch("/{case_id}/status", response_model=CaseDetailResponse)
async def update_case_status(
    case_id: str,
    data: CaseStatusUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_analyst_or_admin),
) -> CaseDetailResponse:
    """Change case status with transition validation."""
    try:
        service = CaseService(session)
        return await service.update_status(case_id, data, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Assignment ─────────────────────────────────────────────────────


@router.patch("/{case_id}/assign", response_model=CaseDetailResponse)
async def assign_case(
    case_id: str,
    data: CaseAssign,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_analyst_or_admin),
) -> CaseDetailResponse:
    """Assign case to an analyst."""
    try:
        service = CaseService(session)
        return await service.assign(case_id, data, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Alert Linking ──────────────────────────────────────────────────


@router.post("/{case_id}/alerts", response_model=CaseDetailResponse)
async def link_alerts_to_case(
    case_id: str,
    data: CaseAlertLink,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_analyst_or_admin),
) -> CaseDetailResponse:
    """Link alerts to a case."""
    try:
        service = CaseService(session)
        return await service.link_alerts(case_id, data, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{case_id}/alerts/{alert_id}", response_model=CaseDetailResponse)
async def unlink_alert_from_case(
    case_id: str,
    alert_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_analyst_or_admin),
) -> CaseDetailResponse:
    """Unlink an alert from a case."""
    try:
        service = CaseService(session)
        return await service.unlink_alert(case_id, alert_id, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Comments ───────────────────────────────────────────────────────


@router.post("/{case_id}/comments", response_model=CommentResponse, status_code=201)
async def add_case_comment(
    case_id: str,
    data: CommentCreate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_analyst_or_admin),
) -> CommentResponse:
    """Add a comment to a case."""
    try:
        service = CaseService(session)
        return await service.add_comment(
            case_id,
            data,
            user_id=current_user.id,
            username=current_user.username,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Batch Operations  —  v0.9.0 ────────────────────────────────────

from schemas.case import (
    BatchCaseAssign,
    BatchCaseResponse,
    BatchCaseStatusUpdate,
)


@router.post("/batch-status", response_model=BatchCaseResponse)
async def batch_update_case_status(
    data: BatchCaseStatusUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_analyst_or_admin),
) -> BatchCaseResponse:
    """Batch update case statuses (max 200).

    Validates status transitions for each case.
    Returns per-case success/failure results.
    """
    try:
        service = CaseService(session)
        result = await service.batch_update_status(
            case_ids=data.case_ids,
            status=data.status,
            resolution=data.resolution,
            user_id=current_user.id,
        )

        # Convert results to BatchCaseResult
        batch_results = [
            {"case_id": r["case_id"], "success": r["success"], "title": r.get("title"), "error": r.get("error")}
            for r in result["results"]
        ]

        return BatchCaseResponse(
            total=result["total"],
            success_count=result["success_count"],
            failed_count=result["failed_count"],
            results=batch_results,
            errors=result["errors"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("batch_update_case_status failed")
        raise HTTPException(status_code=500, detail="Failed to batch-update case statuses")


@router.post("/batch-assign", response_model=BatchCaseResponse)
async def batch_assign_cases(
    data: BatchCaseAssign,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_analyst_or_admin),
) -> BatchCaseResponse:
    """Batch assign cases to an analyst (max 200).

    Assigns all specified cases to the given analyst.
    Returns per-case success/failure results.
    """
    try:
        service = CaseService(session)
        result = await service.batch_assign(
            case_ids=data.case_ids,
            assigned_to=data.assigned_to,
            user_id=current_user.id,
        )

        # Convert results
        batch_results = [
            {"case_id": r["case_id"], "success": r["success"], "title": r.get("title"), "error": r.get("error")}
            for r in result["results"]
        ]

        return BatchCaseResponse(
            total=result["total"],
            success_count=result["success_count"],
            failed_count=result["failed_count"],
            results=batch_results,
            errors=result["errors"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("batch_assign_cases failed")
        raise HTTPException(status_code=500, detail="Failed to batch-assign cases")
