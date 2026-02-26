"""
告警触发器配置
Playbook Engine - SOC Copilot v0.7.4

提供告警分析结果与剧本自动化的联动配置
"""

from typing import Dict, List, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


class TriggerOperator(str, Enum):
    """触发器操作符"""

    EQ = "eq"  # 等于
    NE = "ne"  # 不等于
    IN = "in"  # 在列表中
    NOT_IN = "not_in"  # 不在列表中
    GT = "gt"  # 大于
    GTE = "gte"  # 大于等于
    LT = "lt"  # 小于
    LTE = "lte"  # 小于等于
    CONTAINS = "contains"  # 包含
    STARTS_WITH = "starts_with"  # 开头匹配


class TriggerCondition(BaseModel):
    """触发器条件"""

    field: str = Field(..., description="字段路径: alert.severity")
    operator: TriggerOperator = TriggerOperator.EQ
    value: Any = Field(..., description="比较值")


class AlertTriggerConfig(BaseModel):
    """告警触发器配置"""

    trigger_id: str
    name: str
    conditions: List[TriggerCondition]
    playbook_id: str
    enabled: bool = True
    execution_mode: str = "manual"  # manual/auto/dry_run
    priority: int = 5  # 1-10, 1为最高优先级


# ============ 预定义触发器 ============

ALERT_TRIGGERS = {
    "critical_auto_contain": AlertTriggerConfig(
        trigger_id="critical_auto_contain",
        name="高危告警自动遏制",
        conditions=[
            TriggerCondition(
                field="alert.severity",
                operator=TriggerOperator.IN,
                value=["critical", "high"],
            ),
            TriggerCondition(
                field="alert.verdict",
                operator=TriggerOperator.EQ,
                value="true_positive",
            ),
            TriggerCondition(
                field="alert.confidence_score", operator=TriggerOperator.GTE, value=0.7
            ),
        ],
        playbook_id="PB-ALERT-AUTO-CONTAIN",
        execution_mode="auto",
        priority=1,
    ),
    "malware_response": AlertTriggerConfig(
        trigger_id="malware_response",
        name="恶意软件响应",
        conditions=[
            TriggerCondition(
                field="alert.event_category",
                operator=TriggerOperator.EQ,
                value="malware",
            ),
        ],
        playbook_id="PB-MALWARE-RESPONSE",
        execution_mode="dry_run",
        priority=2,
    ),
    "phishing_response": AlertTriggerConfig(
        trigger_id="phishing_response",
        name="钓鱼邮件响应",
        conditions=[
            TriggerCondition(
                field="alert.event_category",
                operator=TriggerOperator.EQ,
                value="phishing",
            ),
        ],
        playbook_id="PB-PHISHING-RESPONSE",
        execution_mode="auto",
        priority=2,
    ),
    "lateral_movement": AlertTriggerConfig(
        trigger_id="lateral_movement",
        name="横向移动检测响应",
        conditions=[
            TriggerCondition(
                field="alert.event_category",
                operator=TriggerOperator.EQ,
                value="lateral_movement",
            ),
        ],
        playbook_id="PB-LATERAL-MOVEMENT",
        execution_mode="dry_run",
        priority=1,
    ),
    "data_exfiltration": AlertTriggerConfig(
        trigger_id="data_exfiltration",
        name="数据外泄防护",
        conditions=[
            TriggerCondition(
                field="alert.event_category",
                operator=TriggerOperator.EQ,
                value="exfiltration",
            ),
        ],
        playbook_id="PB-DATA-EXFIL",
        execution_mode="auto",
        priority=1,
    ),
    "c2_detection": AlertTriggerConfig(
        trigger_id="c2_detection",
        name="C2通信检测响应",
        conditions=[
            TriggerCondition(
                field="alert.event_category",
                operator=TriggerOperator.EQ,
                value="command_and_control",
            ),
        ],
        playbook_id="PB-C2-RESPONSE",
        execution_mode="auto",
        priority=1,
    ),
    "pii_exposure": AlertTriggerConfig(
        trigger_id="pii_exposure",
        name="个人信息泄露响应",
        conditions=[
            TriggerCondition(
                field="alert.impact.contains_pii",
                operator=TriggerOperator.EQ,
                value=True,
            ),
        ],
        playbook_id="PB-PII-RESPONSE",
        execution_mode="dry_run",
        priority=2,
    ),
    "escalation_required": AlertTriggerConfig(
        trigger_id="escalation_required",
        name="自动升级",
        conditions=[
            TriggerCondition(
                field="alert.escalation_required",
                operator=TriggerOperator.EQ,
                value=True,
            ),
        ],
        playbook_id="PB-ESCALATION",
        execution_mode="manual",
        priority=3,
    ),
}


# ============ 触发器执行配置 ============

TRIGGER_EXECUTION_CONFIG = {
    "enabled": True,
    "rate_limit": {
        "per_alert": 3,  # 每个告警最多触发3次
        "per_hour": 50,  # 每小时最多50次
        "cooldown": 300,  # 冷却时间5分钟
    },
    "notification": {
        "on_trigger": True,
        "on_complete": True,
        "on_failure": True,
    },
    "auto_approve": [
        {"severity": "critical", "verdict": "true_positive"},
        {"event_category": "malware", "confidence_score": 0.9},
    ],
}


# ============ 上下文映射 ============

ALERT_CONTEXT_MAPPING = {
    # 告警基本信息
    "alert.id": "alert.id",
    "alert.name": "alert.name",
    "alert.source": "alert.source",
    "alert.severity": "alert.severity",
    "alert.verdict": "alert.verdict",
    "alert.confidence_score": "alert.confidence_score",
    "alert.summary": "alert.summary",
    # 事件分类
    "alert.event_category": "alert.event_category",
    "alert.event_subcategory": "alert.event_subcategory",
    "alert.attack_techniques": "alert.attack_technique_ids",
    # IOC
    "alert.iocs.ips": "context.ioc.ips",
    "alert.iocs.domains": "context.ioc.domains",
    "alert.iocs.hashes": "context.ioc.hashes",
    "alert.iocs.urls": "context.ioc.urls",
    # 实体
    "alert.entities.hosts": "context.entity.hosts",
    "alert.entities.users": "context.entity.users",
    "alert.entities.accounts": "context.entity.accounts",
    # 影响
    "alert.impact.risk_score": "context.impact.risk_score",
    "alert.impact.contains_pii": "context.impact.contains_pii",
    "alert.impact.affected_assets": "context.asset.list",
    # 根因
    "alert.root_cause.attack_phase": "context.attack.phase",
    "alert.root_cause.attack_vector": "context.attack.vector",
    "alert.root_cause.data_exfiltrated": "context.data.exfiltrated",
    # 响应
    "alert.recommended_actions": "response.actions",
    "alert.suggested_playbooks": "response.suggested_playbooks",
}


def evaluate_condition(condition: TriggerCondition, alert_data: Dict) -> bool:
    """评估触发器条件

    Args:
        condition: 条件配置
        alert_data: 告警分析数据

    Returns:
        是否满足条件
    """
    # 获取字段值
    field_path = condition.field.split(".")
    value = alert_data
    for key in field_path:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return False

    # 比较
    op = condition.operator
    cmp_value = condition.value

    if op == TriggerOperator.EQ:
        return value == cmp_value
    elif op == TriggerOperator.NE:
        return value != cmp_value
    elif op == TriggerOperator.IN:
        return value in cmp_value
    elif op == TriggerOperator.NOT_IN:
        return value not in cmp_value
    elif op == TriggerOperator.GT:
        return value > cmp_value
    elif op == TriggerOperator.GTE:
        return value >= cmp_value
    elif op == TriggerOperator.LT:
        return value < cmp_value
    elif op == TriggerOperator.LTE:
        return value <= cmp_value
    elif op == TriggerOperator.CONTAINS:
        return cmp_value in value
    elif op == TriggerOperator.STARTS_WITH:
        return str(value).startswith(cmp_value)

    return False


def evaluate_trigger(trigger: AlertTriggerConfig, alert_data: Dict) -> bool:
    """评估触发器

    Args:
        trigger: 触发器配置
        alert_data: 告警分析数据

    Returns:
        是否触发
    """
    if not trigger.enabled:
        return False

    return all(evaluate_condition(c, alert_data) for c in trigger.conditions)


def get_matching_triggers(alert_data: Dict) -> List[AlertTriggerConfig]:
    """获取匹配的触发器列表

    Args:
        alert_data: 告警分析数据

    Returns:
        匹配的触发器列表
    """
    matches = []
    for trigger in ALERT_TRIGGERS.values():
        if evaluate_trigger(trigger, alert_data):
            matches.append(trigger)

    # 按优先级排序
    matches.sort(key=lambda x: x.priority)
    return matches
