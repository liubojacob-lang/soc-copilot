"""
告警生命周期管理 Schema
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AlertStatus(str, Enum):
    """告警状态"""
    NEW = "new"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"
    ESCALATED = "escalated"


class AlertSeverity(str, Enum):
    """告警严重程度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertAssignee(BaseModel):
    """告警分配人"""
    user_id: str
    username: str
    email: Optional[str] = None
    assigned_at: datetime


class AlertEscalation(BaseModel):
    """告警升级"""
    escalated_to: str
    escalated_by: str
    reason: str
    escalated_at: datetime


class AlertNote(BaseModel):
    """告警备注"""
    id: str
    user_id: str
    username: str
    content: str
    created_at: datetime


class AlertLifecycleUpdate(BaseModel):
    """告警生命周期更新"""
    status: Optional[AlertStatus] = None
    assigned_to: Optional[str] = None
    note: Optional[str] = None


class AlertAssignment(BaseModel):
    """告警分配"""
    assigned_to: str = Field(..., description="分配给的用户ID")
    note: Optional[str] = Field(None, description="分配备注")


class AlertEscalationCreate(BaseModel):
    """创建告警升级"""
    escalated_to: str = Field(..., description="升级给的用户ID或角色")
    reason: str = Field(..., description="升级原因")
    priority: bool = Field(False, description="是否优先处理")


class AlertResolution(BaseModel):
    """告警解决"""
    resolution_type: AlertStatus = Field(
        ...,
        description="解决类型: resolved 或 false_positive"
    )
    resolution_note: str = Field(..., description="解决说明")
    root_cause: Optional[str] = Field(None, description="根因分析")
    remediation: Optional[str] = Field(None, description="补救措施")


class AlertNoteCreate(BaseModel):
    """创建告警备注"""
    content: str = Field(..., min_length=1, max_length=5000)


class AlertLifecycleResponse(BaseModel):
    """告警生命周期响应"""
    alert_id: str
    status: AlertStatus
    severity: AlertSeverity
    assigned_to: Optional[AlertAssignee] = None
    escalated: Optional[AlertEscalation] = None
    notes: List[AlertNote] = []
    created_at: datetime
    updated_at: datetime
    first_seen: datetime
    last_seen: datetime
    timeline: List[Dict[str, Any]] = []

    class Config:
        from_attributes = True


class AlertBatchUpdate(BaseModel):
    """批量更新告警"""
    alert_ids: List[str] = Field(..., min_items=1, max_items=100)
    status: Optional[AlertStatus] = None
    assigned_to: Optional[str] = None
    tags: Optional[List[str]] = None


class AlertBatchResponse(BaseModel):
    """批量更新响应"""
    updated_count: int
    failed_count: int
    errors: List[Dict[str, str]] = []


class AlertStatistics(BaseModel):
    """告警统计"""
    total: int
    by_status: Dict[str, int]
    by_severity: Dict[str, int]
    by_source: Dict[str, int]
    avg_resolution_time: Optional[float] = None
    mttr: Optional[float] = None  # Mean Time To Resolve


class AlertTrend(BaseModel):
    """告警趋势"""
    timestamp: datetime
    count: int
    by_severity: Dict[str, int]


class TopThreat(BaseModel):
    """Top 威胁源"""
    type: str  # "ip" or "domain"
    value: str
    count: int
    severity: AlertSeverity
    first_seen: datetime
    last_seen: datetime


class ThreatIntelligenceStats(BaseModel):
    """威胁情报统计"""
    total_iocs: int
    malicious_ips: int
    suspicious_ips: int
    malicious_domains: int
    top_ips: List[TopThreat]
    top_domains: List[TopThreat]
    mitre_tactics: Dict[str, int]
