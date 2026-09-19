"""Root cause analysis API endpoints (T2.4).

POST /api/v1/alerts/{alert_id}/root-cause-analysis   → run analysis
GET  /api/v1/alerts/{alert_id}/root-cause-analyses   → history for the alert
POST /api/v1/root-cause-analyses/{rca_id}/feedback   → analyst feedback
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from middleware.rate_limiter import rate_limit
from models.user import UserModel
from schemas.root_cause import (
    RootCauseAnalysisListResponse,
    RootCauseAnalysisResponse,
    RootCauseFeedbackRequest,
)
from services.rca_service import (
    AIServiceUnavailableError,
    RootCauseAlertNotFoundError,
    RootCauseAnalysisNotFoundError,
    RootCauseAnalysisService,
    _to_response_dict,
)

logger = get_logger(__name__)
router = APIRouter(tags=["root-cause"])


@router.post(
    "/api/v1/alerts/{alert_id}/root-cause-analysis",
    response_model=RootCauseAnalysisResponse,
)
@rate_limit(max_requests=5, window_seconds=60)
async def run_root_cause_analysis(
    alert_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> RootCauseAnalysisResponse:
    """Run an AI root cause analysis for an alert and persist the result."""
    service = RootCauseAnalysisService(session)
    try:
        row = await service.analyze(alert_id)
    except RootCauseAlertNotFoundError:
        raise HTTPException(status_code=404, detail="Alert not found") from None
    except AIServiceUnavailableError as e:
        # LLM degraded: refuse rather than fabricate (T1.1 principle)
        raise HTTPException(
            status_code=503,
            detail="AI service is currently unavailable; root cause analysis "
            "was not performed. Please retry later.",
        ) from None
    return RootCauseAnalysisResponse(**_to_response_dict(row))


@router.get(
    "/api/v1/alerts/{alert_id}/root-cause-analyses",
    response_model=RootCauseAnalysisListResponse,
)
async def list_root_cause_analyses(
    alert_id: int,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> RootCauseAnalysisListResponse:
    """List historical root cause analyses for an alert (newest first)."""
    service = RootCauseAnalysisService(session)
    rows = await service.list_for_alert(alert_id, limit=limit)
    return RootCauseAnalysisListResponse(
        items=[RootCauseAnalysisResponse(**_to_response_dict(r)) for r in rows],
        total=len(rows),
    )


@router.post(
    "/api/v1/root-cause-analyses/{rca_id}/feedback",
    response_model=RootCauseAnalysisResponse,
)
async def submit_root_cause_feedback(
    rca_id: str,
    payload: RootCauseFeedbackRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> RootCauseAnalysisResponse:
    """Record an analyst verdict on a root cause analysis."""
    service = RootCauseAnalysisService(session)
    try:
        row = await service.submit_feedback(rca_id, payload)
    except RootCauseAnalysisNotFoundError:
        raise HTTPException(
            status_code=404, detail="Root cause analysis not found"
        ) from None
    return RootCauseAnalysisResponse(**_to_response_dict(row))
