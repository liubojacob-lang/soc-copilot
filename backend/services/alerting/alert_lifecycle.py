"""
告警生命周期管理服务
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from schemas.alert_lifecycle import (
    AlertAssignee,
    AlertAssignment,
    AlertEscalation,
    AlertEscalationCreate,
    AlertLifecycleResponse,
    AlertNote,
    AlertNoteCreate,
    AlertResolution,
    AlertSeverity,
    AlertStatistics,
    AlertStatus,
    AlertTrend,
    ThreatIntelligenceStats,
    TopThreat,
)

logger = get_logger(__name__)


class AlertLifecycleService:
    """告警生命周期管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _normalize_status(raw_status: str | None) -> AlertStatus:
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

    async def get_alert_lifecycle(self, alert_id: str) -> AlertLifecycleResponse | None:
        """获取告警生命周期信息"""
        from models.alert_note import AlertNoteModel
        from models.security_alert import SecurityAlert

        result = await self.db.execute(
            select(SecurityAlert).where(SecurityAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        # 构建时间线
        timeline = await self._build_timeline(alert)

        # 获取告警备注
        notes_result = await self.db.execute(
            select(AlertNoteModel)
            .where(AlertNoteModel.alert_id == alert_id)
            .order_by(AlertNoteModel.created_at.desc())
        )
        note_models = notes_result.scalars().all()

        notes = [
            AlertNote(
                id=note.id,
                user_id=note.user_id,
                username=note.username,
                content=note.content,
                created_at=note.created_at,
            )
            for note in note_models
        ]

        escalated_info = None
        if getattr(alert, "escalated_to", None) or getattr(alert, "escalated_at", None):
            escalated_info = AlertEscalation(
                escalated_to=alert.escalated_to or "Unassigned",
                escalated_by=alert.assigned_to or "system",
                reason=getattr(alert, "escalation_reason", None) or "Escalated for higher-level investigation",
                escalated_at=alert.escalated_at or alert.updated_at or alert.created_at,
            )

        return AlertLifecycleResponse(
            alert_id=str(alert.id),
            status=self._normalize_status(alert.status),
            severity=AlertSeverity(alert.severity),
            assigned_to=(
                AlertAssignee(
                    user_id=alert.assigned_to or "",
                    username=alert.assigned_to or "Unassigned",
                    assigned_at=alert.assigned_at or alert.created_at,
                )
                if alert.assigned_to
                else None
            ),
            escalated=escalated_info,
            notes=notes,  # 从数据库加载备注
            created_at=alert.created_at,
            updated_at=alert.updated_at,
            first_seen=alert.created_at,
            last_seen=alert.updated_at,
            timeline=timeline,
        )

    async def _build_timeline(self, alert) -> list[dict[str, Any]]:
        """构建告警时间线"""
        timeline = []

        # 创建事件
        timeline.append(
            {
                "timestamp": alert.created_at,
                "event": "created",
                "description": f"Alert created by {alert.source}",
                "user": None,
            }
        )

        # 状态变更
        if alert.status and alert.status != "new":
            timeline.append(
                {
                    "timestamp": alert.updated_at,
                    "event": "status_changed",
                    "description": f"Status changed to {alert.status}",
                    "user": None,
                }
            )

        # 分配事件
        if alert.assigned_to:
            timeline.append(
                {
                    "timestamp": alert.assigned_at or alert.updated_at,
                    "event": "assigned",
                    "description": f"Assigned to {alert.assigned_to}",
                    "user": alert.assigned_to,
                }
            )

        # 丰富化事件
        if alert.enriched_at:
            timeline.append(
                {
                    "timestamp": alert.enriched_at,
                    "event": "enriched",
                    "description": "Threat intelligence enrichment completed",
                    "user": None,
                }
            )

        # 按时间排序
        timeline.sort(key=lambda x: x["timestamp"])

        return timeline

    async def update_status(
        self, alert_id: str, status: AlertStatus, user_id: str
    ) -> AlertLifecycleResponse | None:
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
        alert.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(
            f"Alert {alert_id} status updated: {old_status} -> {status.value} by {user_id}"
        )

        # 发送 WebSocket 通知（推送失败不影响状态更新本身）
        try:
            from routers.websocket import push_alert

            await push_alert(
                {
                    "id": alert.id,
                    "source": alert.source,
                    "event_type": alert.event_type,
                    "severity": alert.severity,
                    "title": alert.title,
                    "description": alert.description,
                    "source_ip": alert.source_ip,
                    "destination_ip": alert.destination_ip,
                    "status": alert.status,
                    "assigned_to": alert.assigned_to,
                    "updated_by": user_id,
                    "previous_status": old_status,
                    "created_at": (
                        alert.created_at.isoformat() if alert.created_at else None
                    ),
                    "updated_at": (
                        alert.updated_at.isoformat() if alert.updated_at else None
                    ),
                }
            )
        except Exception as e:
            logger.warning(f"Failed to push alert status update via WebSocket: {e}")

        return await self.get_alert_lifecycle(alert_id)

    async def assign_alert(
        self, alert_id: str, assignment: AlertAssignment, user_id: str
    ) -> AlertLifecycleResponse | None:
        """分配告警"""
        from models.security_alert import SecurityAlert

        result = await self.db.execute(
            select(SecurityAlert).where(SecurityAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            return None

        alert.assigned_to = assignment.assigned_to
        alert.assigned_at = datetime.now(UTC)
        alert.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(
            f"Alert {alert_id} assigned to {assignment.assigned_to} by {user_id}"
        )

        return await self.get_alert_lifecycle(alert_id)

    async def resolve_alert(
        self, alert_id: str, resolution: AlertResolution, user_id: str
    ) -> AlertLifecycleResponse | None:
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
        alert.resolved_at = datetime.now(UTC)
        alert.resolved_by = user_id
        alert.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(f"Alert {alert_id} resolved as {resolution.resolution_type.value}")

        return await self.get_alert_lifecycle(alert_id)

    async def escalate_alert(
        self, alert_id: str, escalation: AlertEscalationCreate, user_id: str
    ) -> AlertLifecycleResponse | None:
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
        alert.escalated_at = datetime.now(UTC)
        alert.escalation_reason = escalation.reason
        alert.updated_at = datetime.now(UTC)

        await self.db.commit()
        await self.db.refresh(alert)

        logger.info(f"Alert {alert_id} escalated to {escalation.escalated_to}")

        return await self.get_alert_lifecycle(alert_id)

    async def add_note(
        self, alert_id: str, note: AlertNoteCreate, user_id: str, username: str
    ) -> AlertNote:
        """添加告警备注"""
        from models.alert_note import AlertNoteModel
        from models.security_alert import SecurityAlert

        # Verify alert exists
        result = await self.db.execute(
            select(SecurityAlert).where(SecurityAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            raise ValueError(f"Alert {alert_id} not found")

        # Create note in database
        note_model = AlertNoteModel(
            alert_id=alert_id,
            user_id=user_id,
            username=username,
            content=note.content,
        )

        self.db.add(note_model)
        await self.db.commit()
        await self.db.refresh(note_model)

        logger.info(f"Note added to alert {alert_id} by {user_id}: {note_model.id}")

        return AlertNote(
            id=note_model.id,
            user_id=note_model.user_id,
            username=note_model.username,
            content=note_model.content,
            created_at=note_model.created_at,
        )

    async def get_statistics(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> AlertStatistics:
        """获取告警统计"""
        from models.security_alert import SecurityAlert

        if not end_date:
            end_date = datetime.now(UTC)
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
        by_severity = dict(severity_result.all())

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
        by_source = dict(source_result.all())

        # 计算平均解决时间
        mttr_result = await self.db.execute(
            select(
                func.avg(SecurityAlert.resolved_at - SecurityAlert.created_at)
            ).where(
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
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        interval: str = "hour",  # hour, day, week
    ) -> list[AlertTrend]:
        """获取告警趋势 - 时间序列聚合

        Args:
            start_date: 开始时间（默认7天前）
            end_date: 结束时间（默认当前时间）
            interval: 时间间隔 (hour/day/week)

        Returns:
            按时间间隔分组的告警趋势数据
        """

        if not end_date:
            end_date = datetime.now(UTC)
        if not start_date:
            start_date = end_date - timedelta(days=7)

        if interval not in ("hour", "day", "week"):
            raise ValueError(
                f"Invalid interval: {interval}. Must be 'hour', 'day', or 'week'"
            )

        # 时间分组表达式：按数据库方言选择函数，输出统一为文本供下游解析
        # （SQLite: strftime；PostgreSQL: date_trunc + TO_CHAR）
        if self.db.get_bind().dialect.name == "sqlite":
            period_expr = {
                "hour": "strftime('%Y-%m-%d %H:00:00', created_at)",
                "day": "strftime('%Y-%m-%d', created_at)",
                # 先回退 6 天再推进到最近的周一 => 归到所在周的周一
                "week": "strftime('%Y-%m-%d', created_at, '-6 days', 'weekday 1')",
            }[interval]
        else:
            period_expr = {
                "hour": "TO_CHAR(date_trunc('hour', created_at), 'YYYY-MM-DD HH24:00:00')",
                "day": "TO_CHAR(date_trunc('day', created_at), 'YYYY-MM-DD')",
                "week": "TO_CHAR(date_trunc('week', created_at), 'YYYY-MM-DD')",
            }[interval]

        # 使用原生 SQL 进行时间序列聚合
        # period 表达式来自上方按 interval 白名单构建的映射；
        # 其余为常量 SQL，值通过绑定参数传入
        query = "\n".join(
            [
                "SELECT",
                f"    {period_expr} as period,",
                "    COUNT(*) as total,",
                "    SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as critical,",
                "    SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as high,",
                "    SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END) as medium,",
                "    SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END) as low,",
                "    SUM(CASE WHEN severity = 'info' THEN 1 ELSE 0 END) as info",
                "FROM security_alerts",
                "WHERE created_at >= :start_date AND created_at <= :end_date",
                "GROUP BY period",
                "ORDER BY period",
            ]
        )

        from sqlalchemy import text

        result = await self.db.execute(
            text(query), {"start_date": start_date, "end_date": end_date}
        )

        trends = []
        for row in result:
            # 解析时间戳：各方言输出统一为文本
            # hour => 小时起点；day => 日期；week => 该周周一的日期
            period = str(row.period)
            if interval == "hour":
                timestamp = datetime.strptime(period, "%Y-%m-%d %H:%M:%S")
            else:  # day / week
                timestamp = datetime.strptime(period, "%Y-%m-%d")

            # 构建严重性统计
            by_severity = {
                "critical": row.critical or 0,
                "high": row.high or 0,
                "medium": row.medium or 0,
                "low": row.low or 0,
                "info": row.info or 0,
            }

            trends.append(
                AlertTrend(
                    timestamp=timestamp,
                    count=row.total,
                    by_severity=by_severity,
                )
            )

        logger.info(
            f"Generated {len(trends)} trend points for interval '{interval}' "
            f"from {start_date} to {end_date}"
        )

        return trends

    async def get_top_threats(
        self,
        threat_type: str = "ip",  # ip or domain
        limit: int = 10,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[TopThreat]:
        """获取Top威胁源"""
        from models.security_alert import SecurityAlert

        if not end_date:
            end_date = datetime.now(UTC)
        if not start_date:
            start_date = end_date - timedelta(days=7)

        threats = []

        if threat_type == "ip":
            query = (
                select(
                    SecurityAlert.source_ip,
                    func.count(SecurityAlert.id).label("count"),
                    func.min(SecurityAlert.created_at).label("first_seen"),
                    func.max(SecurityAlert.created_at).label("last_seen"),
                    SecurityAlert.severity,
                )
                .where(
                    and_(
                        SecurityAlert.source_ip.isnot(None),
                        SecurityAlert.source_ip != "",
                        SecurityAlert.created_at >= start_date,
                        SecurityAlert.created_at <= end_date,
                    )
                )
                .group_by(SecurityAlert.source_ip, SecurityAlert.severity)
                .order_by(desc("count"))
                .limit(limit)
            )

            result = await self.db.execute(query)
            rows = result.all()

            for row in rows:
                if row.source_ip:
                    threats.append(
                        TopThreat(
                            type="ip",
                            value=row.source_ip,
                            count=row.count,
                            severity=(
                                AlertSeverity(row.severity.lower())
                                if row.severity
                                else AlertSeverity.MEDIUM
                            ),
                            first_seen=row.first_seen,
                            last_seen=row.last_seen,
                        )
                    )

        return threats

    async def get_threat_intel_stats(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> ThreatIntelligenceStats:
        """获取威胁情报统计"""
        from models.security_alert import SecurityAlert

        if not end_date:
            end_date = datetime.now(UTC)
        if not start_date:
            start_date = end_date - timedelta(days=7)

        total_iocs_query = select(func.count(SecurityAlert.id)).where(
            and_(
                SecurityAlert.iocs.isnot(None),
                SecurityAlert.created_at >= start_date,
                SecurityAlert.created_at <= end_date,
            )
        )
        total_iocs_result = await self.db.execute(total_iocs_query)
        total_iocs = total_iocs_result.scalar() or 0

        malicious_ips_query = select(func.count(SecurityAlert.id)).where(
            and_(
                SecurityAlert.source_ip.isnot(None),
                SecurityAlert.threat_score >= 70,
                SecurityAlert.created_at >= start_date,
                SecurityAlert.created_at <= end_date,
            )
        )
        malicious_ips_result = await self.db.execute(malicious_ips_query)
        malicious_ips = malicious_ips_result.scalar() or 0

        suspicious_ips_query = select(func.count(SecurityAlert.id)).where(
            and_(
                SecurityAlert.source_ip.isnot(None),
                SecurityAlert.threat_score >= 30,
                SecurityAlert.threat_score < 70,
                SecurityAlert.created_at >= start_date,
                SecurityAlert.created_at <= end_date,
            )
        )
        suspicious_ips_result = await self.db.execute(suspicious_ips_query)
        suspicious_ips = suspicious_ips_result.scalar() or 0

        malicious_domains_query = select(func.count(SecurityAlert.id)).where(
            and_(
                SecurityAlert.iocs.isnot(None),
                SecurityAlert.threat_score >= 70,
                SecurityAlert.created_at >= start_date,
                SecurityAlert.created_at <= end_date,
            )
        )
        malicious_domains_result = await self.db.execute(malicious_domains_query)
        malicious_domains = malicious_domains_result.scalar() or 0

        top_ips = await self.get_top_threats("ip", 10, start_date, end_date)
        top_domains = []

        mitre_tactics_query = select(SecurityAlert.mitre_tactics).where(
            and_(
                SecurityAlert.mitre_tactics.isnot(None),
                SecurityAlert.created_at >= start_date,
                SecurityAlert.created_at <= end_date,
            )
        )
        mitre_result = await self.db.execute(mitre_tactics_query)
        mitre_rows = mitre_result.all()

        mitre_tactics: dict[str, int] = {}
        for row in mitre_rows:
            if row.mitre_tactics:
                for tactic in row.mitre_tactics:
                    if tactic:
                        mitre_tactics[tactic] = mitre_tactics.get(tactic, 0) + 1

        return ThreatIntelligenceStats(
            total_iocs=total_iocs,
            malicious_ips=malicious_ips,
            suspicious_ips=suspicious_ips,
            malicious_domains=malicious_domains,
            top_ips=top_ips,
            top_domains=top_domains,
            mitre_tactics=mitre_tactics,
        )
