"""
Security Alert Ingestion Router
Receives and manages alerts from external security monitoring tools (Wazuh, Snort, OSQuery, etc).
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.security_alert import SecurityAlert
from models.user import UserModel
from schemas.security_alert import (
    SecurityAlertIngest,
    SecurityAlertListResponse,
    SecurityAlertResponse,
    SecurityAlertStats,
    SecurityAlertUpdate,
)

# Message Queue Integration
from services.message_queue_manager import get_message_queue_manager
from services.query_cache import cached, invalidate_cache
from services.security.security_alert_schema import ensure_security_alerts_schema

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/security-alerts", tags=["security-alerts"])


@router.post("/ingest", response_model=dict)
async def ingest_alert(
    alert_data: SecurityAlertIngest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """
    Ingest an alert from an external security monitoring tool.

    This endpoint receives alerts from:
    - Wazuh SIEM
    - Snort IDS
    - OSQuery
    - Other security tools

    Features:
    - Automatic deduplication based on source + event_id
    - Parses timestamps in ISO 8601 format
    - Stores MITRE ATT&CK tactics
    - Preserves raw alert data
    """
    try:
        await ensure_security_alerts_schema(session)

        # Parse timestamp
        try:
            event_timestamp = datetime.fromisoformat(alert_data.timestamp.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid timestamp format: {alert_data.timestamp}. Use ISO 8601 format.",
            )

        # Check for duplicate alert
        duplicate_query = select(SecurityAlert).where(
            and_(
                SecurityAlert.source == alert_data.source,
                SecurityAlert.external_event_id == alert_data.event_id,
            )
        )
        duplicate_result = await session.execute(duplicate_query)
        existing_alert = duplicate_result.scalar_one_or_none()

        if existing_alert:
            logger.info(
                f"Duplicate alert received: source={alert_data.source}, "
                f"event_id={alert_data.event_id}"
            )
            return {
                "status": "duplicate",
                "message": "Alert already exists",
                "alert_id": existing_alert.id,
            }

        # Create new alert
        new_alert = SecurityAlert(
            source=alert_data.source,
            external_event_id=alert_data.event_id,
            event_type=alert_data.event_type,
            severity=alert_data.severity.lower(),
            title=alert_data.title,
            description=alert_data.description,
            source_ip=alert_data.source_ip,
            destination_ip=alert_data.destination_ip,
            protocol=alert_data.protocol,
            agent_name=alert_data.agent_name,
            agent_id=alert_data.agent_id,
            agent_ip=alert_data.agent_ip,
            rule_id=alert_data.rule_id,
            rule_level=alert_data.rule_level,
            rule_groups=(",".join(alert_data.rule_groups) if alert_data.rule_groups else None),
            rule_mitre=(",".join(alert_data.rule_mitre) if alert_data.rule_mitre else None),
            full_log=alert_data.full_log,
            location=alert_data.location,
            geoip=alert_data.geoip,
            raw_data=alert_data.raw_data,
            event_timestamp=event_timestamp,
            status="new",
        )

        session.add(new_alert)
        await session.commit()
        await session.refresh(new_alert)

        logger.info(
            f"New alert ingested: id={new_alert.id}, source={alert_data.source}, "
            f"severity={alert_data.severity}, title={alert_data.title}"
        )

        invalidate_cache("alert_stats")

        # Publish to message queue for async processing
        try:
            mq_manager = get_message_queue_manager()
            queue_severity = _map_severity_to_queue(alert_data.severity)

            # Convert alert to dict for queue
            alert_dict = {
                "id": new_alert.id,
                "source": new_alert.source,
                "event_type": new_alert.event_type,
                "severity": new_alert.severity,
                "title": new_alert.title,
                "description": new_alert.description,
                "source_ip": new_alert.source_ip,
                "destination_ip": new_alert.destination_ip,
                "agent_name": new_alert.agent_name,
                "rule_id": new_alert.rule_id,
                "rule_level": new_alert.rule_level,
                "created_at": (new_alert.created_at.isoformat() if new_alert.created_at else None),
                "event_timestamp": (
                    new_alert.event_timestamp.isoformat() if new_alert.event_timestamp else None
                ),
            }

            message_id = await mq_manager.publish_alert_async(
                alert=alert_dict, severity=queue_severity
            )

            if message_id:
                logger.info(f"  ✓ Published to message queue: {message_id}")
            else:
                logger.warning("  ⚠ Failed to publish to message queue")

        except Exception as e:
            logger.error(f"  ✗ Error publishing to message queue: {e}")
            # Don't fail the request if queue publish fails

        return {
            "status": "success",
            "message": "Alert ingested successfully",
            "alert_id": new_alert.id,
        }

    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"Validation error: {e!s}")
        raise HTTPException(status_code=422, detail="Invalid request")
    except Exception as e:
        logger.error(f"Error ingesting alert: {e!s}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to ingest alert: {e!s}")


@router.get("/", response_model=SecurityAlertListResponse)
async def list_alerts(
    source: str | None = Query(None, description="Filter by source"),
    severity: str | None = Query(None, description="Filter by severity"),
    status: str | None = Query(None, description="Filter by status"),
    agent_name: str | None = Query(None, description="Filter by agent name"),
    source_ip: str | None = Query(None, description="Filter by source IP"),
    event_type: str | None = Query(None, description="Filter by event type"),
    search: str | None = Query(None, description="Search in title and description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> SecurityAlertListResponse:
    """
    List security alerts with filtering and pagination.

    Supports filtering by:
    - Source (wazuh, snort, osquery, etc)
    - Severity (critical, high, medium, low, info)
    - Status (open, investigating, closed, false_positive)
    - Agent name
    - Source IP
    - Event type
    - Full-text search in title and description
    """
    try:
        await ensure_security_alerts_schema(session)
        query = select(SecurityAlert)

        # Apply filters
        if source:
            query = query.where(SecurityAlert.source == source)
        if severity:
            query = query.where(SecurityAlert.severity == severity.lower())
        if status:
            query = query.where(SecurityAlert.status == status.lower())
        if agent_name:
            query = query.where(SecurityAlert.agent_name == agent_name)
        if source_ip:
            query = query.where(SecurityAlert.source_ip == source_ip)
        if event_type:
            query = query.where(SecurityAlert.event_type == event_type)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    SecurityAlert.title.ilike(search_pattern),
                    SecurityAlert.description.ilike(search_pattern),
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply sorting and pagination
        query = query.order_by(SecurityAlert.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await session.execute(query)
        alerts = result.scalars().all()

        return SecurityAlertListResponse(
            total=total,
            alerts=alerts,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        logger.error(f"Error listing alerts: {e!s}")
        raise HTTPException(status_code=500, detail=f"Failed to list alerts: {e!s}")


@router.get("/{alert_id}", response_model=SecurityAlertResponse)
async def get_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> SecurityAlertResponse:
    """Get detailed information about a specific alert."""
    try:
        await ensure_security_alerts_schema(session)
        query = select(SecurityAlert).where(SecurityAlert.id == alert_id)
        result = await session.execute(query)
        alert = result.scalar_one_or_none()

        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        return alert

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert {alert_id}: {e!s}")
        raise HTTPException(status_code=500, detail=f"Failed to get alert: {e!s}")


@router.patch("/{alert_id}", response_model=SecurityAlertResponse)
async def update_alert(
    alert_id: int,
    update_data: SecurityAlertUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> SecurityAlertResponse:
    """
    Update alert status and metadata.

    Allows updating:
    - Status (open, investigating, closed, false_positive)
    - Assigned user
    - Resolution notes

    When closing an alert, closed_at is automatically set.
    """
    try:
        await ensure_security_alerts_schema(session)
        query = select(SecurityAlert).where(SecurityAlert.id == alert_id)
        result = await session.execute(query)
        alert = result.scalar_one_or_none()

        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        # Update fields
        if update_data.status:
            alert.status = update_data.status.lower()
            # Set closed_at if status is closed or false_positive
            if alert.status in ["closed", "false_positive"] and not alert.closed_at:
                alert.closed_at = datetime.now(datetime.UTC)

        if update_data.assigned_to:
            alert.assigned_to = update_data.assigned_to

        if update_data.resolution:
            alert.resolution = update_data.resolution

        await session.commit()
        await session.refresh(alert)

        logger.info(f"Alert {alert_id} updated: status={alert.status}")

        invalidate_cache("alert_stats")

        return alert

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert {alert_id}: {e!s}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update alert: {e!s}")


@router.get("/stats/summary", response_model=SecurityAlertStats)
@cached(ttl=60, prefix="alert_stats")
async def get_alert_statistics(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> SecurityAlertStats:
    """
    Get alert statistics summary.

    Returns:
    - Total alert count
    - Breakdown by severity
    - Breakdown by status
    - Breakdown by source
    - Counts for last 24h, 7d, 30d
    """
    try:
        # Total count
        total_query = select(func.count()).select_from(SecurityAlert)
        total_result = await session.execute(total_query)
        total = total_result.scalar() or 0

        # By severity
        severity_query = select(SecurityAlert.severity, func.count(SecurityAlert.id)).group_by(
            SecurityAlert.severity
        )
        severity_result = await session.execute(severity_query)
        by_severity = {row[0]: row[1] for row in severity_result.all()}

        # By status
        status_query = select(SecurityAlert.status, func.count(SecurityAlert.id)).group_by(
            SecurityAlert.status
        )
        status_result = await session.execute(status_query)
        by_status = {row[0]: row[1] for row in status_result.all()}

        # By source
        source_query = select(SecurityAlert.source, func.count(SecurityAlert.id)).group_by(
            SecurityAlert.source
        )
        source_result = await session.execute(source_query)
        by_source = {row[0]: row[1] for row in source_result.all()}

        # Time-based counts
        now = datetime.now(datetime.UTC)

        last_24h_query = (
            select(func.count())
            .select_from(SecurityAlert)
            .where(SecurityAlert.created_at >= now - timedelta(hours=24))
        )
        last_24h = (await session.execute(last_24h_query)).scalar() or 0

        last_7d_query = (
            select(func.count())
            .select_from(SecurityAlert)
            .where(SecurityAlert.created_at >= now - timedelta(days=7))
        )
        last_7d = (await session.execute(last_7d_query)).scalar() or 0

        last_30d_query = (
            select(func.count())
            .select_from(SecurityAlert)
            .where(SecurityAlert.created_at >= now - timedelta(days=30))
        )
        last_30d = (await session.execute(last_30d_query)).scalar() or 0

        return SecurityAlertStats(
            total=total,
            by_severity=by_severity,
            by_status=by_status,
            by_source=by_source,
            last_24h=last_24h,
            last_7d=last_7d,
            last_30d=last_30d,
        )

    except Exception as e:
        logger.error(f"Error getting alert statistics: {e!s}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {e!s}")


@router.delete("/{alert_id}", response_model=dict)
async def delete_alert(
    alert_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """
    Delete an alert.

    WARNING: This is a permanent deletion. Consider updating status to 'false_positive' instead.
    """
    try:
        query = select(SecurityAlert).where(SecurityAlert.id == alert_id)
        result = await session.execute(query)
        alert = result.scalar_one_or_none()

        if not alert:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        await session.delete(alert)
        await session.commit()

        logger.info(f"Alert {alert_id} deleted")

        invalidate_cache("alert_stats")

        return {
            "status": "success",
            "message": f"Alert {alert_id} deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert {alert_id}: {e!s}")
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete alert: {e!s}")


def _map_severity_to_queue(severity: str) -> str:
    """
    Map alert severity to message queue priority

    Args:
        severity: Alert severity (critical/high/medium/low/info)

    Returns:
        Queue severity level (critical/high/medium/low)
    """
    mapping = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "info": "low",
    }
    return mapping.get(severity.lower(), "medium")
