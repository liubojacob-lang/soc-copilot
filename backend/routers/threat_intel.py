import uuid

"""Threat Intelligence router for OTX API endpoints."""

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.threat_intel_cache import ThreatIntelCacheDB
from models.user import UserModel
from schemas.threat_intel import (
    BulkThreatIntelRequest,
    BulkThreatIntelResponse,
    ThreatIntelResponse,
)
from services.threat_intel_service import ThreatIntelService

router = APIRouter(prefix="/api/v1/ti", tags=["threat_intel"])
logger = get_logger(__name__)


@router.get("/otx", response_model=ThreatIntelResponse)
async def lookup_otx_single(
    ioc_type: str = Query(..., description="IOC type (ip/domain/url/hash)"),
    ioc_value: str = Query(..., description="IOC value"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ThreatIntelResponse:
    """Lookup single IOC threat intelligence from OTX.

    Returns cached results if available and not expired.
    """
    try:
        service = ThreatIntelService(session)
        return await service.lookup(ioc_type=ioc_type, ioc_value=ioc_value)
    except Exception as e:
        logger.error(f"OTX lookup error: {e!s}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/otx/bulk", response_model=BulkThreatIntelResponse)
async def lookup_otx_bulk(
    data: BulkThreatIntelRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
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
        logger.error(f"OTX bulk lookup error: {e!s}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_threat_intel_stats(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
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
                "cache_ttl_hours": settings.ti_cache_ttl_hours,
            },
        }
    except Exception as e:
        logger.error(f"Threat intel stats error: {e!s}")
        raise HTTPException(status_code=500, detail="Internal server error")


# v0.8.3: TI Cache Refresh API endpoints


@router.delete("/cache/{ioc_type}/{ioc_value}")
async def refresh_single_ioc(
    ioc_type: str,
    ioc_value: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
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
    iocs: list[dict] = Body(
        ..., description="List of {ioc_type, ioc_value} to refresh"
    ),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
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
    current_user: UserModel = Depends(get_current_user),
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
    current_user: UserModel = Depends(get_current_user),
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


# ── Batch IOC Query  —  v0.9.0 ─────────────────────────────────────

from schemas.threat_intel import (
    IOCBatchRequest,
    IOCBatchResponse,
    IOCBatchResultItem,
    Verdict,
)


@router.post("/batch", response_model=IOCBatchResponse)
async def batch_ioc_query(
    data: IOCBatchRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> IOCBatchResponse:
    """Batch query IOCs for threat intelligence (max 50).

    Returns per-IOC results including source, score, tags, references,
    and details. Results are cached where available.

    Args:
        data: Batch IOC request with list of {ioc_type, ioc_value}

    Returns:
        IOCBatchResponse with per-IOC results and error details
    """
    request_id = str(uuid.uuid4())[:8]
    try:
        service = ThreatIntelService(session)
        results: list[IOCBatchResultItem] = []
        errors: list[dict] = []
        skipped_count = 0

        for item in data.items:
            try:
                result = await service.lookup(
                    ioc_type=item.ioc_type,
                    ioc_value=item.ioc_value,
                )

                results.append(
                    IOCBatchResultItem(
                        ioc_type=result.ioc_type,
                        ioc_value=result.ioc_value,
                        verdict=result.verdict,
                        score=result.score,
                        source=result.provider,
                        pulse_count=result.pulse_count,
                        tags=result.tags,
                        references=result.references,
                        details=result.raw if hasattr(result, "raw") else {},
                        cached=result.cached,
                        error=result.error_reason,
                    )
                )
            except ValueError as e:
                errors.append(
                    {
                        "ioc_type": item.ioc_type,
                        "ioc_value": item.ioc_value,
                        "error": str(e),
                    }
                )
                results.append(
                    IOCBatchResultItem(
                        ioc_type=item.ioc_type,
                        ioc_value=item.ioc_value,
                        verdict=Verdict.unknown,
                        score=0,
                        source="none",
                        error=str(e),
                    )
                )
            except Exception as e:
                logger.warning(
                    "Batch IOC query failed for %s:%s: %s",
                    item.ioc_type,
                    item.ioc_value,
                    e,
                )
                errors.append(
                    {
                        "ioc_type": item.ioc_type,
                        "ioc_value": item.ioc_value,
                        "error": str(e),
                    }
                )
                results.append(
                    IOCBatchResultItem(
                        ioc_type=item.ioc_type,
                        ioc_value=item.ioc_value,
                        verdict=Verdict.unknown,
                        score=0,
                        source="none",
                        error=str(e),
                    )
                )

        return IOCBatchResponse(
            request_id=request_id,
            provider="otx",
            total=len(data.items),
            results=results,
            skipped_count=skipped_count,
            errors=errors,
        )
    except Exception as e:
        logger.error(f"Batch IOC query error: {e!s}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Add uuid import if not already present at module top
