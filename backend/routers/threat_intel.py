"""Threat Intelligence router for OTX API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from schemas.threat_intel import (
    ThreatIntelResponse,
    BulkThreatIntelRequest,
    BulkThreatIntelRequestItem,
    BulkThreatIntelResponse,
)
from services.threat_intel_service import ThreatIntelService

router = APIRouter(prefix="/api/ti", tags=["threat_intel"])
logger = get_logger(__name__)


@router.get("/otx", response_model=ThreatIntelResponse)
async def lookup_otx_single(
    ioc_type: str = Query(..., description="IOC type (ip/domain/url/hash)"),
    ioc_value: str = Query(..., description="IOC value"),
    session: AsyncSession = Depends(get_session),
) -> ThreatIntelResponse:
    """Lookup single IOC threat intelligence from OTX.

    Returns cached results if available and not expired.
    """
    try:
        service = ThreatIntelService(session)
        return await service.lookup(ioc_type=ioc_type, ioc_value=ioc_value)
    except Exception as e:
        logger.error(f"OTX lookup error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/otx/bulk", response_model=BulkThreatIntelResponse)
async def lookup_otx_bulk(
    data: BulkThreatIntelRequest,
    session: AsyncSession = Depends(get_session),
) -> BulkThreatIntelResponse:
    """Bulk lookup threat intelligence from OTX.

    Enforces rate limiting: only processes TI_MAX_IOCS_PER_REQUEST
    IOCs per request. Remaining IOCs are marked as skipped.
    """
    try:
        service = ThreatIntelService(session)

        # Convert items to list of dicts
        items = [
            {"ioc_type": item.ioc_type, "ioc_value": item.ioc_value}
            for item in data.items  # Now uses BulkThreatIntelRequestItem
        ]

        return await service.bulk_lookup(items)
    except Exception as e:
        logger.error(f"OTX bulk lookup error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_threat_intel_stats(
    session: AsyncSession = Depends(get_session),
):
    """Get threat intelligence cache statistics.

    Returns cache size, hit rates, and provider breakdown.
    """
    try:
        from services.threat_intel_service import ThreatIntelService

        service = ThreatIntelService(session)
        stats = await service.repository.get_stats(session)
        return {
            "cache_stats": stats,
            "config": {
                "provider": "otx",
                "enabled": service._get_otx_client() is not None,
                "cache_ttl_hours": service.repository.__class__.__dict__,
            },
        }
    except Exception as e:
        logger.error(f"Threat intel stats error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
