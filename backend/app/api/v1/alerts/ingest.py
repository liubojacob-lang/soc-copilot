"""
告警接收 API
集成 Wazuh 等安全监控工具的告警
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.auth import get_current_user
from app.models.user import User


router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


class AlertIngest(BaseModel):
    """告警接收模型"""
    source: str = Field(..., description="告警来源 (wazuh, snort, osquery, etc)")
    event_id: str = Field(..., description="事件ID")
    timestamp: str = Field(..., description="时间戳 (ISO 8601)")
    event_type: str = Field(..., description="事件类型")
    severity: str = Field(..., description="严重级别 (critical, high, medium, low, info)")
    title: str = Field(..., description="告警标题")
    description: Optional[str] = Field(None, description="告警描述")
    source_ip: Optional[str] = Field(None, description="源IP")
    destination_ip: Optional[str] = Field(None, description="目标IP")
    protocol: Optional[str] = Field(None, description="协议")
    agent_name: Optional[str] = Field(None, description="主机名")
    agent_id: Optional[str] = Field(None, description="主机ID")
    agent_ip: Optional[str] = Field(None, description="主机IP")
    rule_id: Optional[str] = Field(None, description="规则ID")
    rule_level: Optional[int] = Field(None, description="规则级别")
    rule_groups: List[str] = Field(default_factory=list, description="规则组")
    rule_mitre: List[str] = Field(default_factory=list, description="MITRE ATT&CK战术")
    full_log: Optional[str] = Field(None, description="完整日志")
    location: Optional[str] = Field(None, description="位置")
    geoip: Optional[Dict] = Field(None, description="地理位置信息")
    raw_data: Optional[Dict] = Field(None, description="原始数据")


class AlertResponse(BaseModel):
    """告警响应模型"""
    id: int
    source: str
    external_event_id: str
    event_type: str
    severity: str
    title: str
    description: Optional[str]
    source_ip: Optional[str]
    destination_ip: Optional[str]
    status: str
    created_at: datetime


@router.post("/ingest", response_model=Dict[str, Any])
async def ingest_alert(
    alert: AlertIngest,
    db: AsyncSession = Depends(get_db)
):
    """
    接收外部告警
    从 Wazuh、Snort 等安全工具接收告警
    """
    try:
        from sqlalchemy import select
        from app.models.alert import Alert

        # 检查是否已存在（基于 source + event_id 去重）
        existing_stmt = select(Alert).where(
            Alert.source == alert.source,
            Alert.external_event_id == alert.event_id
        )

        existing_alert = await db.execute(existing_stmt.scalar())

        if existing_alert:
            return {
                "status": "duplicate",
                "message": "Alert already exists",
                "alert_id": existing_alert
            }

        # 创建新告警
        new_alert = Alert(
            source=alert.source,
            external_event_id=alert.event_id,
            event_type=alert.event_type,
            severity=alert.severity,
            title=alert.title,
            description=alert.description,
            source_ip=alert.source_ip,
            destination_ip=alert.destination_ip,
            protocol=alert.protocol,
            agent_name=alert.agent_name,
            agent_id=alert.agent_id,
            agent_ip=alert.agent_ip,
            rule_id=alert.rule_id,
            rule_level=alert.rule_level,
            rule_groups=','.join(alert.rule_groups) if alert.rule_groups else None,
            rule_mitre=','.join(alert.rule_mitre) if alert.rule_mitre else None,
            full_log=alert.full_log,
            location=alert.location,
            geoip=alert.geoip,
            raw_data=alert.raw_data,
            status='open',
            created_at=datetime.now()
        )

        db.add(new_alert)
        await db.commit()
        await db.refresh(new_alert)

        # TODO: 触发后续处理
        # - 威胁情报丰富
        # - 自动创建案例
        # - 触发 Playbook

        return {
            "status": "success",
            "message": "Alert ingested successfully",
            "alert_id": new_alert.id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    source: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """查询告警列表"""
    try:
        from sqlalchemy import select
        from app.models.alert import Alert

        query = select(Alert)

        # 过滤条件
        if source:
            query = query.where(Alert.source == source)
        if severity:
            query = query.where(Alert.severity == severity)
        if status:
            query = query.where(Alert.status == status)

        # 排序和分页
        query = query.order_by(Alert.created_at.desc())
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        alerts = result.scalars().all()

        return alerts

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取告警详情"""
    try:
        from sqlalchemy import select
        from app.models.alert import Alert

        query = select(Alert).where(Alert.id == alert_id)
        result = await db.execute(query)
        alert = result.scalar_one_or_none()

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        return alert

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_alerts_summary(
    db: AsyncSession = Depends(get_db)
):
    """获取告警统计摘要"""
    try:
        from sqlalchemy import func, select
        from app.models.alert import Alert

        # 总数
        total = await db.execute(select(func.count()).select_from(Alert))

        # 按严重级别统计
        severity_stats = await db.execute(
            select(Alert.severity, func.count(Alert.id))
            .group_by(Alert.severity)
        )

        # 按状态统计
        status_stats = await db.execute(
            select(Alert.status, func.count(Alert.id))
            .group_by(Alert.status)
        )

        # 按来源统计
        source_stats = await db.execute(
            select(Alert.source, func.count(Alert.id))
            .group_by(Alert.source)
        )

        # 最近24小时趋势
        from datetime import timedelta
        last_24h = datetime.now() - timedelta(days=1)

        recent = await db.execute(
            select(func.count()).select_from(Alert).where(
                Alert.created_at >= last_24h
            )
        )

        return {
            "total": total.scalar(),
            "by_severity": {row[0]: row[1] for row in severity_stats.all()},
            "by_status": {row[0]: row[1] for row in status_stats.all()},
            "by_source": {row[0]: row[1] for row in source_stats.all()},
            "last_24h": recent.scalar()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
