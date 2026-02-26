"""Threat Intelligence router for OTX API endpoints."""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, and_

from core.logger import get_logger
from db.session import get_session
from schemas.threat_intel import (
    ThreatIntelResponse,
    BulkThreatIntelRequest,
    BulkThreatIntelRequestItem,
    BulkThreatIntelResponse,
)
from services.threat_intel_service import ThreatIntelService
from models.threat_intel_cache import ThreatIntelCacheDB

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


# v0.8.3: TI Cache Refresh API endpoints

@router.delete("/cache/{ioc_type}/{ioc_value}")
async def refresh_single_ioc(
    ioc_type: str,
    ioc_value: str,
    session: AsyncSession = Depends(get_session),
):
    """Invalidate single IOC cache entry, forcing fresh lookup.
    
    Use case: IOC data updated in OTX, need fresh data.
    
    Args:
        ioc_type: IOC type (ip/domain/url/hash)
        ioc_value: IOC value to invalidate
    """
    from repositories.threat_intel_repository import ThreatIntelRepository
    
    repo = ThreatIntelRepository()
    deleted = await repo.delete_by_ioc(session, "otx", ioc_type, ioc_value)
    await session.commit()
    
    return {
        "action": "cache_invalidated",
        "ioc_type": ioc_type,
        "ioc_value": ioc_value,
        "deleted": deleted > 0,
    }


@router.post("/cache/refresh")
async def refresh_bulk_iocs(
    iocs: List[dict] = Body(..., description="List of {ioc_type, ioc_value} to refresh"),
    session: AsyncSession = Depends(get_session),
):
    """Bulk invalidate IOC cache entries.
    
    Use case: Daily refresh of high-value IOCs.
    Maximum 100 IOCs per request.
    
    Args:
        iocs: List of dicts with ioc_type and ioc_value
    """
    from repositories.threat_intel_repository import ThreatIntelRepository
    
    repo = ThreatIntelRepository()
    deleted_count = 0
    
    for ioc in iocs[:100]:  # Limit to 100 per request
        deleted = await repo.delete_by_ioc(
            session, "otx", ioc.get("ioc_type"), ioc.get("ioc_value")
        )
        deleted_count += deleted
    
    await session.commit()
    
    return {
        "action": "bulk_cache_invalidated",
        "requested": len(iocs),
        "processed": min(len(iocs), 100),
        "deleted": deleted_count,
    }


@router.delete("/cache/expired")
async def clear_expired_cache(
    session: AsyncSession = Depends(get_session),
):
    """Clear all expired cache entries.
    
    Use case: Manual cleanup before TTL-based auto-cleanup.
    """
    from repositories.threat_intel_repository import ThreatIntelRepository
    
    repo = ThreatIntelRepository()
    deleted = await repo.delete_expired(session)
    await session.commit()
    
    return {
        "action": "expired_cache_cleared",
        "deleted_count": deleted,
    }


@router.delete("/cache/all")
async def clear_all_cache(
    confirm: bool = Query(..., description="Must be true to confirm action"),
    session: AsyncSession = Depends(get_session),
):
    """Clear entire TI cache (dangerous operation).
    
    Use case: Complete cache reset after configuration change.
    
    Args:
        confirm: Must be true to confirm the dangerous operation
    """
    if not confirm:
        raise HTTPException(status_code=400, detail="Confirmation required")
    
    result = await session.execute(delete(ThreatIntelCacheDB))
    await session.commit()
    
    return {
        "action": "all_cache_cleared",
        "deleted_count": result.rowcount,
    }
