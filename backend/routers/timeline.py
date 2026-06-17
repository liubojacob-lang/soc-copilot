"""Timeline building API endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel
from schemas.timeline import TimelineRequest, TimelineResponse
from services.timeline_service import TimelineService

logger = get_logger(__name__)
router = APIRouter(tags=["timeline"])


@router.post("/api/build-timeline", response_model=TimelineResponse)
async def build_timeline(
    request: TimelineRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> TimelineResponse:
    """Build a security timeline from logs.

    Args:
        request: Timeline build request with raw log and optional log type
        session: Database session

    Returns:
        Timeline response with events and suspicious events
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"Received timeline request: {request_id}")

    try:
        service = TimelineService(session=session)
        result = await service.build(request.raw_log, request.log_type)
        return result
    except Exception as e:
        logger.error(f"Timeline build error: {e!s}")
        raise HTTPException(status_code=500, detail="Timeline build failed")


@router.get("/api/timeline/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "soc-copilot"}
