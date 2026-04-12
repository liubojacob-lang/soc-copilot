"""Alert analysis API endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from schemas.alert import AlertAnalysisRequest, AlertAnalysisResponse
from services.alerting.alert_service import AlertService

logger = get_logger(__name__)
router = APIRouter(tags=["alert"])


@router.post("/api/analyze-alert", response_model=AlertAnalysisResponse)
async def analyze_alert(
    request: AlertAnalysisRequest,
    session: AsyncSession = Depends(get_session),
) -> AlertAnalysisResponse:
    """Analyze a security alert/log.

    Args:
        request: Alert analysis request with raw log
        session: Database session

    Returns:
        Alert analysis response
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"Received alert analysis request: {request_id}")

    try:
        service = AlertService(session=session)
        result = await service.analyze(request.raw_log)
        return result
    except ValueError as e:
        logger.error(f"Validation error: {e!s}")
        raise HTTPException(status_code=422, detail="Invalid request")
    except Exception as e:
        logger.error(f"Analysis error: {e!s}")
        raise HTTPException(status_code=500, detail="Analysis failed")
