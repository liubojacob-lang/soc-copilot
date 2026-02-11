"""IOC Hits router for IOC hit management API."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from schemas.ioc_hit import (
    IOCHitCreate,
    IOCHitResponse,
    IOCHitListResponse,
)
from services.ioc_hits_service import IOCHitsService

router = APIRouter(prefix="/api/ioc-hits", tags=["ioc_hits"])
logger = get_logger(__name__)


@router.get("", response_model=IOCHitListResponse)
async def list_ioc_hits(
    ioc: Optional[str] = Query(None, description="Filter by IOC value"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    session: AsyncSession = Depends(get_session),
) -> IOCHitListResponse:
    """List IOC hits with optional IOC filter."""
    if not ioc:
        raise HTTPException(status_code=400, detail="IOC parameter is required")

    service = IOCHitsService(session)
    hits, total = await service.list_by_ioc(ioc, limit)
    return IOCHitListResponse(items=hits, total=total)


@router.get("/by-asset/{asset_id}", response_model=IOCHitListResponse)
async def list_ioc_hits_by_asset(
    asset_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    session: AsyncSession = Depends(get_session),
) -> IOCHitListResponse:
    """List IOC hits by asset ID."""
    service = IOCHitsService(session)
    hits, total = await service.list_by_asset(asset_id, limit)
    return IOCHitListResponse(items=hits, total=total)


@router.get("/by-history/{history_id}", response_model=list[IOCHitResponse])
async def list_ioc_hits_by_history(
    history_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    session: AsyncSession = Depends(get_session),
) -> list[IOCHitResponse]:
    """List IOC hits by history ID."""
    service = IOCHitsService(session)
    return await service.list_by_history(history_id, limit)


@router.post("/manual", response_model=IOCHitResponse, status_code=201)
async def create_manual_ioc_hit(
    data: IOCHitCreate,
    session: AsyncSession = Depends(get_session),
) -> IOCHitResponse:
    """Manually create an IOC hit.

    For manual annotation of IOC associations.
    """
    try:
        service = IOCHitsService(session)
        return await service.create(data)
    except Exception as e:
        logger.error(f"Failed to create IOC hit: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
