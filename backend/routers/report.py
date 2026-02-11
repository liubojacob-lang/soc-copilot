"""Report generation API endpoint."""

from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from schemas.report import ReportGenerationRequest, ReportGenerationResponse
from services.report_service import ReportService
from core.logger import get_logger
import uuid

logger = get_logger(__name__)
router = APIRouter(tags=["report"])


@router.post("/api/generate-report", response_model=ReportGenerationResponse)
async def generate_report(
    request: ReportGenerationRequest,
    session: AsyncSession = Depends(get_session),
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
        logger.error(f"Report generation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Report generation failed")
