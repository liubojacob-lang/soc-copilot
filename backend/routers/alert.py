"""Alert analysis API endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from middleware.rate_limiter import rate_limit
from models.user import UserModel
from schemas.alert import AlertAnalysisRequest, AlertAnalysisResponse
from services.alerting.alert_service import AlertService

logger = get_logger(__name__)
router = APIRouter(tags=["alert"])


@router.post("/api/v1/analyze-alert", response_model=AlertAnalysisResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def analyze_alert(
    payload: AlertAnalysisRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> AlertAnalysisResponse:
    """Analyze a security alert/log.

    Args:
        payload: Alert analysis request with raw log or alert attributes
        request: HTTP request for rate limiting and tracing
        session: Database session

    Returns:
        Alert analysis response
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"Received alert analysis request: {request_id}")

    # Build raw_log if omitted or too brief
    raw_log = payload.raw_log
    if not raw_log or len(raw_log.strip()) < 10:
        parts = []
        if payload.title:
            parts.append(f"Alert Title: {payload.title}")
        if payload.severity:
            parts.append(f"Severity: {payload.severity}")
        if payload.source:
            parts.append(f"Source: {payload.source}")
        if payload.description:
            parts.append(f"Description: {payload.description}")
        raw_log = "\n".join(parts)
        if len(raw_log.strip()) < 10:
            raw_log = (
                f"Security Alert Event: {payload.title or 'Unknown alert'} "
                f"detected by {payload.source or 'Security Monitoring System'}."
            )

    try:
        service = AlertService(session=session)
        result = await service.analyze(raw_log)
        if not result.attack_pattern and result.event_type:
            result.attack_pattern = f"{result.event_type.value.upper()} detection pattern"
        return result
    except ValueError as e:
        logger.error(f"Validation error: {e!s}")
        raise HTTPException(status_code=422, detail="Invalid request")
    except Exception as e:
        logger.error(f"Analysis error: {e!s}")
        raise HTTPException(status_code=500, detail="Analysis failed")
