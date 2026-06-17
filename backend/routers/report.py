"""Report generation API endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel
from schemas.report import ReportGenerationRequest, ReportGenerationResponse
from services.report_service import ReportService

logger = get_logger(__name__)
router = APIRouter(tags=["report"])


@router.post("/api/generate-report", response_model=ReportGenerationResponse)
async def generate_report(
    request: ReportGenerationRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ReportGenerationResponse:
    """Generate report templates from alert analysis.

    Args:
        request: Report generation request
        session: Database session

    Returns:
        Report generation response with three templates
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"Received report generation request: {request_id}")

    try:
        service = ReportService(session=session)
        result = await service.generate(
            request.alert_json,
            request.additional_notes,
        )
        return result
    except Exception as e:
        logger.error(f"Report generation error: {e!s}")
        raise HTTPException(status_code=500, detail="Report generation failed")
