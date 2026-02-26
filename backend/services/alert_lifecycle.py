"""
告警生命周期管理服务
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from core.logger import get_logger
from schemas.alert_lifecycle import (
    AlertStatus,
    AlertSeverity,
    AlertAssignee,
    AlertEscalation,
    AlertNote,
    AlertLifecycleResponse,
    AlertResolution,
    AlertAssignment,
    AlertEscalationCreate,
    AlertNoteCreate,
    AlertStatistics,
    AlertTrend,
    TopThreat,
    ThreatIntelligenceStats,
)

logger = get_logger(__name__)


class AlertLifecycleService:
    """告警生命周期管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _normalize_status(raw_status: Optional[str]) -> AlertStatus:
        """Map legacy status values to lifecycle enum."""
        mapping = {
            "open": AlertStatus.NEW,
            "new": AlertStatus.NEW,
            "closed": AlertStatus.RESOLVED,
            "resolved": AlertStatus.RESOLVED,
            "false_positive": AlertStatus.FALSE_POSITIVE,
            "investigating": AlertStatus.INVESTIGATING,
            "escalated": AlertStatus.ESCALATED,
        }
        return mapping.get((raw_status or "").lower(), AlertStatus.NEW)

    async def get_alert_lifecycle(
        self, alert_id: str
    ) -> Optional[AlertLifecycleResponse]:
        """获取告警生命周期信息"""
        from models.security_alert import SecurityAlert

        result = await self.db.execute(
            select(SecurityAlert).where(SecurityAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        # 构建时间线
        timeline = await self._build_timeline(alert)

        return AlertLifecycleResponse(
            alert_id=str(alert.id),
            status=self._normalize_status(alert.status),
            severity=AlertSeverity(alert.severity),
            assigned_to=AlertAssignee(
                user_id=alert.assigned_to or "",
                username=alert.assigned_to or "Unassigned",
                assigned_at=alert.assigned_at or alert.created_at,
            ) if alert.assigned_to else None,
            escalated=None,  # TODO: 从关联表获取
            notes=[],  # TODO: 从备注表获取
            created_at=alert.created_at,
            updated_at=alert.updated_at,
            first_seen=alert.created_at,
            last_seen=alert.updated_at,
            timeline=timeline,
        )

    async def _build_timeline(self, alert) -> List[Dict[str, Any]]:
        """构建告警时间线"""
        timeline = []

        # 创建事件
        timeline.append({
            "timestamp": alert.created_at,
            "event": "created",
            "description": f"Alert created by {alert.source}",
            "user": None,
        })

        # 状态变更
        if alert.status and alert.status != "new":
            timeline.append({
                "timestamp": alert.updated_at,
                "event": "status_changed",
                "description": f"Status changed to {alert.status}",
                "user": None,
            })

        # 分配事件
        if alert.assigned_to:
            timeline.append({
                "timestamp": alert.assigned_at or alert.updated_at,
                "event": "assigned",
                "description": f"Assigned to {alert.assigned_to}",
                "user": alert.assigned_to,
            })

        # 丰富化事件
        if alert.enriched_at:
            timeline.append({
                "timestamp": alert.enriched_at,
                "event": "enriched",
                "description": "Threat intelligence enrichment completed",
                "user": None,
            })

        # 按时间排序
        timeline.sort(key=lambda x: x["timestamp"])

        return timeline

    async def update_status(
        self, alert_id: str, status: AlertStatus, user_id: str
    ) -> Optional[AlertLifecycleResponse]:
        """更新告警状态"""
        from models.security_alert import SecurityAlert

        result = await self.db.execute(
            select(SecurityAlert).where(SecurityAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        old_status = alert.status
        alert.status = status.value
        alert.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(
            f"Alert {alert_id} status updated: {old_status} -> {status.value} by {user_id}"
        )

        # 发送 WebSocket 通知
        # await push_alert_update(alert)

        return await self.get_alert_lifecycle(alert_id)

    async def assign_alert(
        self, alert_id: str, assignment: AlertAssignment, user_id: str
    ) -> Optional[AlertLifecycleResponse]:
        """分配告警"""
        from models.security_alert import SecurityAlert

        result = await self.db.execute(
            select(SecurityAlert).where(SecurityAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.assigned_to = assignment.assigned_to
        alert.assigned_at = datetime.utcnow()
        alert.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(
            f"Alert {alert_id} assigned to {assignment.assigned_to} by {user_id}"
        )

        return await self.get_alert_lifecycle(alert_id)

    async def resolve_alert(
        self, alert_id: str, resolution: AlertResolution, user_id: str
    ) -> Optional[AlertLifecycleResponse]:
        """解决告警"""
        from models.security_alert import SecurityAlert

        result = await self.db.execute(
            select(SecurityAlert).where(SecurityAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.status = resolution.resolution_type.value
        alert.resolution_note = resolution.resolution_note
        alert.root_cause = resolution.root_cause
        alert.remediation = resolution.remediation
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = user_id
        alert.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(f"Alert {alert_id} resolved as {resolution.resolution_type.value}")

        return await self.get_alert_lifecycle(alert_id)

    async def escalate_alert(
        self, alert_id: str, escalation: AlertEscalationCreate, user_id: str
    ) -> Optional[AlertLifecycleResponse]:
        """升级告警"""
        from models.security_alert import SecurityAlert

        result = await self.db.execute(
            select(SecurityAlert).where(SecurityAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.status = AlertStatus.ESCALATED.value
        alert.escalated_to = escalation.escalated_to
        alert.escalated_at = datetime.utcnow()
        alert.escalation_reason = escalation.reason
        alert.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(f"Alert {alert_id} escalated to {escalation.escalated_to}")

        return await self.get_alert_lifecycle(alert_id)

    async def add_note(
        self, alert_id: str, note: AlertNoteCreate, user_id: str, username: str
    ) -> AlertNote:
        """添加告警备注"""
        # TODO: 实现备注存储
        note_obj = AlertNote(
            id=str(datetime.utcnow().timestamp()),
            user_id=user_id,
            username=username,
            content=note.content,
            created_at=datetime.utcnow(),
        )

        logger.info(f"Note added to alert {alert_id} by {user_id}")

        return note_obj

    async def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> AlertStatistics:
        """获取告警统计"""
        from models.security_alert import SecurityAlert

        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        # 总数
        total_result = await self.db.execute(
            select(func.count(SecurityAlert.id)).where(
                and_(
                    SecurityAlert.created_at >= start_date,
                    SecurityAlert.created_at <= end_date,
                )
            )
        )
        total = total_result.scalar() or 0

        # 按状态统计
        status_result = await self.db.execute(
            select(SecurityAlert.status, func.count(SecurityAlert.id))
            .where(
                and_(
                    SecurityAlert.created_at >= start_date,
                    SecurityAlert.created_at <= end_date,
                )
            )
            .group_by(SecurityAlert.status)
        )
        by_status = {status or "new": count for status, count in status_result.all()}

        # 按严重程度统计
        severity_result = await self.db.execute(
            select(SecurityAlert.severity, func.count(SecurityAlert.id))
            .where(
                and_(
                    SecurityAlert.created_at >= start_date,
                    SecurityAlert.created_at <= end_date,
                )
            )
            .group_by(SecurityAlert.severity)
        )
        by_severity = {severity: count for severity, count in severity_result.all()}

        # 按来源统计
        source_result = await self.db.execute(
            select(SecurityAlert.source, func.count(SecurityAlert.id))
            .where(
                and_(
                    SecurityAlert.created_at >= start_date,
                    SecurityAlert.created_at <= end_date,
                )
            )
            .group_by(SecurityAlert.source)
            .order_by(desc(func.count(SecurityAlert.id)))
            .limit(10)
        )
        by_source = {source: count for source, count in source_result.all()}

        # 计算平均解决时间
        mttr_result = await self.db.execute(
            select(func.avg(SecurityAlert.resolved_at - SecurityAlert.created_at)).where(
                and_(
                    SecurityAlert.created_at >= start_date,
                    SecurityAlert.created_at <= end_date,
                    SecurityAlert.resolved_at.isnot(None),
                )
            )
        )
        mttr = mttr_result.scalar()
        avg_resolution_time = mttr.total_seconds() / 3600 if mttr else None

        return AlertStatistics(
            total=total,
            by_status=by_status,
            by_severity=by_severity,
            by_source=by_source,
            avg_resolution_time=avg_resolution_time,
            mttr=avg_resolution_time,
        )

    async def get_trends(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        interval: str = "hour",  # hour, day, week
    ) -> List[AlertTrend]:
        """获取告警趋势"""
        from models.security_alert import SecurityAlert

        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        # TODO: 实现时间序列聚合
        trends = []

        return trends

    async def get_top_threats(
        self,
        threat_type: str = "ip",  # ip or domain
        limit: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[TopThreat]:
        """获取Top威胁源"""
        from models.security_alert import SecurityAlert

        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)

        # TODO: 实现威胁源统计
        threats = []

        return threats

    async def get_threat_intel_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> ThreatIntelligenceStats:
        """获取威胁情报统计"""
        # TODO: 实现威胁情报统计
        return ThreatIntelligenceStats(
            total_iocs=0,
            malicious_ips=0,
            suspicious_ips=0,
            malicious_domains=0,
            top_ips=[],
            top_domains=[],
            mitre_tactics={},
        )
