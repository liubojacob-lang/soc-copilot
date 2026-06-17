"""
告警生命周期管理 API 路由
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies import get_current_user
from models.user import UserModel
from schemas.alert_lifecycle import (
    AlertAssignment,
    AlertBatchResponse,
    AlertBatchUpdate,
    AlertEscalationCreate,
    AlertLifecycleResponse,
    AlertNote,
    AlertNoteCreate,
    AlertResolution,
    AlertStatistics,
    AlertStatus,
    AlertTrend,
    ThreatIntelligenceStats,
    TopThreat,
)
from services.alerting.alert_lifecycle import AlertLifecycleService
from services.security.security_alert_schema import ensure_security_alerts_schema

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts Lifecycle"])


@router.get("/{alert_id}/lifecycle", response_model=AlertLifecycleResponse)
async def get_alert_lifecycle(
    alert_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """获取告警生命周期信息"""
    await ensure_security_alerts_schema(db)
    service = AlertLifecycleService(db)
    lifecycle = await service.get_alert_lifecycle(alert_id)

    if not lifecycle:
        raise HTTPException(status_code=404, detail="Alert not found")

    return lifecycle


@router.patch("/{alert_id}/status", response_model=AlertLifecycleResponse)
async def update_alert_status(
    alert_id: str,
    status: AlertStatus,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """更新告警状态"""
    await ensure_security_alerts_schema(db)
    service = AlertLifecycleService(db)
    lifecycle = await service.update_status(alert_id, status, current_user.id)

    if not lifecycle:
        raise HTTPException(status_code=404, detail="Alert not found")

    return lifecycle


@router.post("/{alert_id}/assign", response_model=AlertLifecycleResponse)
async def assign_alert(
    alert_id: str,
    assignment: AlertAssignment,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """分配告警"""
    await ensure_security_alerts_schema(db)
    service = AlertLifecycleService(db)
    lifecycle = await service.assign_alert(alert_id, assignment, current_user.id)

    if not lifecycle:
        raise HTTPException(status_code=404, detail="Alert not found")

    return lifecycle


@router.post("/{alert_id}/resolve", response_model=AlertLifecycleResponse)
async def resolve_alert(
    alert_id: str,
    resolution: AlertResolution,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """解决告警"""
    await ensure_security_alerts_schema(db)
    service = AlertLifecycleService(db)
    lifecycle = await service.resolve_alert(alert_id, resolution, current_user.id)

    if not lifecycle:
        raise HTTPException(status_code=404, detail="Alert not found")

    return lifecycle


@router.post("/{alert_id}/escalate", response_model=AlertLifecycleResponse)
async def escalate_alert(
    alert_id: str,
    escalation: AlertEscalationCreate,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """升级告警"""
    await ensure_security_alerts_schema(db)
    service = AlertLifecycleService(db)
    lifecycle = await service.escalate_alert(alert_id, escalation, current_user.id)

    if not lifecycle:
        raise HTTPException(status_code=404, detail="Alert not found")

    return lifecycle


@router.post("/{alert_id}/notes", response_model=AlertNote)
async def add_alert_note(
    alert_id: str,
    note: AlertNoteCreate,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """添加告警备注"""
    await ensure_security_alerts_schema(db)
    service = AlertLifecycleService(db)

    # 检查告警是否存在
    lifecycle = await service.get_alert_lifecycle(alert_id)
    if not lifecycle:
        raise HTTPException(status_code=404, detail="Alert not found")

    return await service.add_note(alert_id, note, current_user.id, current_user.username)


@router.get("/statistics/summary", response_model=AlertStatistics)
async def get_alert_statistics(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """获取告警统计摘要"""
    service = AlertLifecycleService(db)
    return await service.get_statistics(start_date, end_date)


@router.get("/statistics/trends", response_model=list[AlertTrend])
async def get_alert_trends(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    interval: str = Query("hour", pattern="^(hour|day|week)$"),
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """获取告警趋势"""
    service = AlertLifecycleService(db)
    return await service.get_trends(start_date, end_date, interval)


@router.get("/statistics/top-threats", response_model=list[TopThreat])
async def get_top_threats(
    threat_type: str = Query("ip", pattern="^(ip|domain)$"),
    limit: int = Query(10, ge=1, le=100),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """获取Top威胁源"""
    service = AlertLifecycleService(db)
    return await service.get_top_threats(threat_type, limit, start_date, end_date)


@router.get("/statistics/threat-intel", response_model=ThreatIntelligenceStats)
async def get_threat_intel_statistics(
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """获取威胁情报统计"""
    service = AlertLifecycleService(db)
    return await service.get_threat_intel_stats(start_date, end_date)


@router.post("/batch/update", response_model=AlertBatchResponse)
async def batch_update_alerts(
    batch: AlertBatchUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """批量更新告警"""
    await ensure_security_alerts_schema(db)
    from models.security_alert import SecurityAlert

    updated_count = 0
    failed_count = 0
    errors = []

    for alert_id in batch.alert_ids:
        try:
            result = await db.execute(select(SecurityAlert).where(SecurityAlert.id == alert_id))
            alert = result.scalar_one_or_none()

            if not alert:
                failed_count += 1
                errors.append({"alert_id": alert_id, "error": "Alert not found"})
                continue

            if batch.status:
                alert.status = batch.status.value

            if batch.assigned_to:
                alert.assigned_to = batch.assigned_to
                alert.assigned_at = datetime.now(UTC)

            if batch.tags:
                current_tags = alert.tags or []
                if batch.tags_operation == "add":
                    # Order-preserving dedup: existing tags first, then new unique tags
                    existing_set = set(current_tags)
                    alert.tags = current_tags + [t for t in batch.tags if t not in existing_set]
                elif batch.tags_operation == "remove":
                    remove_set = set(batch.tags)
                    alert.tags = [tag for tag in current_tags if tag not in remove_set]
                else:
                    # Default: replace
                    alert.tags = batch.tags

            alert.updated_at = datetime.now(UTC)
            updated_count += 1

        except Exception as e:
            failed_count += 1
            errors.append({"alert_id": alert_id, "error": str(e)})

    await db.commit()

    return AlertBatchResponse(
        updated_count=updated_count,
        failed_count=failed_count,
        errors=errors,
    )
