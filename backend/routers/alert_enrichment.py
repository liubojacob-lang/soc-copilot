"""
Alert Enrichment API
Manually trigger or manage threat intelligence enrichment
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies import get_current_user
from models.user import UserModel
from services.alerting.alert_enrichment import AlertEnrichmentService
from services.query_cache import cached

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/alert-enrichment", tags=["alert-enrichment"])


@router.post("/process/{alert_id}")
async def process_single_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Manually trigger enrichment for a specific alert

    Useful for:
    - Re-enriching old alerts
    - Testing enrichment logic
    - On-demand enrichment after adding new TI sources
    """
    try:
        service = AlertEnrichmentService()
        success = await service.process_alert(alert_id)

        if success:
            return {
                "status": "success",
                "message": f"Alert {alert_id} enriched successfully",
            }
        else:
            return {
                "status": "skipped",
                "message": f"Alert {alert_id} was not enriched (may not exist or already enriched)",
            }

    except Exception as e:
        logger.error(f"Error processing alert {alert_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/process-recent")
async def process_recent_alerts(
    hours: int = 1,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Manually trigger enrichment for recent alerts

    Processes all alerts from the last N hours.
    Useful for backfilling enrichment data.
    """
    try:
        if hours < 1 or hours > 24:
            raise HTTPException(
                status_code=400, detail="Hours must be between 1 and 24"
            )

        service = AlertEnrichmentService()
        count = await service.process_recent_alerts(hours=hours)

        return {
            "status": "success",
            "message": f"Processed alerts from last {hours} hours",
            "alerts_enriched": count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing recent alerts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_enrichment_stats(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Get statistics about alert enrichment

    Returns:
    - Total alerts
    - Enriched alerts count
    - Enrichment rate
    - Alerts by threat score
    """
    return await _compute_enrichment_stats()


@cached(ttl=60, prefix="enrichment_stats")
async def _compute_enrichment_stats() -> dict[str, Any]:
    """Compute enrichment statistics.

    Streams only the raw_data column in bounded chunks so memory stays flat
    on large alert tables (full_log and other heavy columns are never
    loaded), and serves the result from a 60s cache.
    """
    from sqlalchemy import func, select

    from db.session import AsyncSessionLocal
    from models.security_alert import SecurityAlert

    enriched_count = 0
    threat_scores = {"clean": 0, "suspicious": 0, "malicious": 0, "unknown": 0}

    try:
        async with AsyncSessionLocal() as session:
            total = (
                await session.execute(select(func.count()).select_from(SecurityAlert))
            ).scalar() or 0

            # SQLite/PG both support chunked streaming via yield_per; only the
            # raw_data column is fetched, one JSON blob at a time.
            stream = await session.stream(select(SecurityAlert.raw_data).yield_per(500))
            async for (raw_data,) in stream:
                if not raw_data:
                    continue
                ti = raw_data.get("threat_intel")
                if not ti:
                    continue

                enriched_count += 1
                indicators = ti.get("indicators", {}) or {}

                has_malicious = False
                has_suspicious = False

                for indicator_data in indicators.values():
                    if isinstance(indicator_data, dict):
                        reputation = indicator_data.get("reputation", "unknown")
                        if reputation == "malicious":
                            has_malicious = True
                        elif reputation in ("suspicious", "unknown"):
                            has_suspicious = True

                if has_malicious:
                    threat_scores["malicious"] += 1
                elif has_suspicious:
                    threat_scores["suspicious"] += 1
                else:
                    threat_scores["clean"] += 1

        threat_scores["unknown"] = total - enriched_count
        enrichment_rate = (enriched_count / total * 100) if total > 0 else 0

        return {
            "total_alerts": total,
            "enriched_alerts": enriched_count,
            "unenriched_alerts": total - enriched_count,
            "enrichment_rate": f"{enrichment_rate:.1f}%",
            "threat_score_distribution": threat_scores,
        }

    except Exception as e:
        logger.error(f"Error getting enrichment stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
