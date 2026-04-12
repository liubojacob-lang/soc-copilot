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
    try:
        from sqlalchemy import func, select

        from models.security_alert import SecurityAlert

        # Total alerts
        total_query = select(func.count()).select_from(SecurityAlert)
        total = (await session.execute(total_query)).scalar() or 0

        # Enriched alerts (have threat_intel in raw_data)
        # SQLite doesn't support JSON extraction well, so we'll count manually
        query = select(SecurityAlert)
        result = await session.execute(query)
        all_alerts = result.scalars().all()

        enriched_count = 0
        threat_scores = {"clean": 0, "suspicious": 0, "malicious": 0, "unknown": 0}

        for alert in all_alerts:
            if alert.raw_data and alert.raw_data.get("threat_intel"):
                enriched_count += 1

                # Check threat scores
                ti = alert.raw_data["threat_intel"]
                indicators = ti.get("indicators", {})

                has_malicious = False
                has_suspicious = False

                for indicator_type, indicator_data in indicators.items():
                    if isinstance(indicator_data, dict):
                        reputation = indicator_data.get("reputation", "unknown")
                        if reputation == "malicious":
                            has_malicious = True
                        elif reputation in ["suspicious", "unknown"]:
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
