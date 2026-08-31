"""
告警分析器验收测试
SOC Copilot v1.0

功能测试和验收标准
"""

import pytest

from schemas.alert_analysis import (
    AlertAnalysisRequest,
    AlertAnalysisResult,
    EventCategory,
    SeverityLevel,
    Verdict,
    get_matching_triggers,
)

# ============ 测试数据 ============

PHISHING_ALERT = {
    "analysis_version": "1.0",
    "analysis_timestamp": "2024-01-15T10:00:00Z",
    "model_used": "nvidia/kimi-k2.5",
    "alert_id": "ALT-001",
    "alert_name": "Suspicious Phishing Email",
    "alert_source": "siem",
    "original_raw_log": "User clicked suspicious link in email from attacker@evil.com",
    "event_category": "phishing",
    "event_subcategory": "phishing_campaign",
    "attack_technique_ids": ["T1566", "T1566.001"],
    "attack_tactic_ids": ["TA0001"],
    "verdict": "true_positive",
    "severity": "high",
    "confidence": "high",
    "confidence_score": 0.85,
    "iocs": {
        "ips": ["192.168.1.100", "10.0.0.50"],
        "domains": ["evil.com", "phishing-site.net"],
        "urls": ["https://evil.com/login"],
        "hashes": [],
        "emails": ["attacker@evil.com"],
        "file_paths": [],
    },
    "ioc_statistics": {
        "total_count": 5,
        "ip_count": 2,
        "domain_count": 2,
        "url_count": 1,
        "hash_count": 0,
        "unique_countries": ["China"],
        "is_research_related": False,
    },
    "entities": {
        "users": [{"value": "john.doe", "type": "user", "count": 1}],
        "hosts": [{"value": "workstation-001", "type": "host", "count": 1}],
        "accounts": [],
        "processes": [],
    },
    "impact": {
        "affected_assets": [
            {
                "asset_id": "ASSET-001",
                "hostname": "workstation-001",
                "ip_addresses": ["192.168.1.100"],
                "criticality": "medium",
                "is_compromised": True,
            }
        ],
        "business_impact_level": "medium",
        "data_at_risk": "用户凭证",
        "estimated_recovery_time": "2小时",
        "contains_pii": False,
        "contains_phi": False,
    },
    "root_cause": {
        "primary_cause": "用户点击钓鱼邮件中的恶意链接",
        "contributing_factors": ["安全意识不足"],
        "attack_vector": "钓鱼邮件",
        "initial_compromise_method": "恶意链接",
        "attack_phase": "installation",
    },
    "summary": "用户点击钓鱼链接，导致凭证可能泄露",
    "full_narrative": "2024年1月15日...",
    "key_findings": ["用户点击钓鱼链接", "目标域名在威胁情报库中"],
    "next_investigation_steps": ["检查其他用户", "分析邮件来源"],
    "references": [],
    "request_id": "REQ-001",
    "degraded_mode": False,
}


MALWARE_ALERT = {
    "analysis_version": "1.0",
    "analysis_timestamp": "2024-01-15T11:00:00Z",
    "model_used": "nvidia/kimi-k2.5",
    "alert_id": "ALT-002",
    "alert_name": "Ransomware Detection",
    "alert_source": "edr",
    "original_raw_log": "Ransomware behavior detected on server-001",
    "event_category": "malware",
    "event_subcategory": "ransomware",
    "attack_technique_ids": ["T1486"],
    "attack_tactic_ids": ["TA0040"],
    "verdict": "true_positive",
    "severity": "critical",
    "confidence": "certain",
    "confidence_score": 0.95,
    "iocs": {
        "ips": [],
        "domains": ["ransom-site.com"],
        "urls": [],
        "hashes": ["a1b2c3d4e5f6"],
        "emails": [],
        "file_paths": ["C:\\ransomware.exe"],
    },
    "ioc_statistics": {
        "total_count": 2,
        "ip_count": 0,
        "domain_count": 1,
        "url_count": 0,
        "hash_count": 1,
        "unique_countries": [],
        "is_research_related": False,
    },
    "entities": {
        "users": [],
        "hosts": [{"value": "server-001", "type": "host", "count": 1}],
        "accounts": [],
        "processes": [{"value": "ransomware.exe", "type": "process", "count": 1}],
    },
    "impact": {
        "affected_assets": [
            {
                "asset_id": "ASSET-002",
                "hostname": "server-001",
                "ip_addresses": ["10.0.1.100"],
                "criticality": "critical",
                "is_compromised": True,
            }
        ],
        "business_impact_level": "critical",
        "data_at_risk": "业务数据",
        "estimated_recovery_time": "24小时",
        "contains_pii": True,
        "contains_phi": False,
    },
    "root_cause": {
        "primary_cause": "勒索软件加密业务数据",
        "attack_vector": "未知",
        "initial_compromise_method": "未知",
        "attack_phase": "actions_on_objectives",
    },
    "summary": "检测到勒索软件正在加密服务器数据",
    "full_narrative": "EDR检测到...",
    "key_findings": ["检测到文件加密行为", "勒索软件进程运行中"],
    "next_investigation_steps": ["立即隔离主机", "检查备份状态"],
    "references": [],
    "request_id": "REQ-002",
    "degraded_mode": False,
}


# ============ Schema 验证测试 ============


class TestAlertAnalysisSchema:
    """告警分析 Schema 测试"""

    def test_valid_phishing_alert(self):
        """测试有效钓鱼告警"""
        result = AlertAnalysisResult(**PHISHING_ALERT)
        assert result.event_category == EventCategory.PHISHING
        assert result.severity == SeverityLevel.HIGH
        assert result.verdict == Verdict.TRUE_POSITIVE
        assert len(result.iocs.ips) == 2

    def test_valid_malware_alert(self):
        """测试有效恶意软件告警"""
        result = AlertAnalysisResult(**MALWARE_ALERT)
        assert result.event_category == EventCategory.MALWARE
        assert result.severity == SeverityLevel.CRITICAL
        assert result.confidence_score == 0.95

    def test_ioc_count(self):
        """测试 IOC 统计"""
        result = AlertAnalysisResult(**PHISHING_ALERT)
        assert result.ioc_statistics.total_count == 5
        assert result.ioc_statistics.ip_count == 2

    def test_severity_icon(self):
        """测试严重等级图标"""
        result = AlertAnalysisResult(**MALWARE_ALERT)
        assert result.get_severity_icon() == "🔴"

        result.severity = SeverityLevel.LOW
        assert result.get_severity_icon() == "🟢"

    def test_is_critical(self):
        """测试关键告警判断"""
        phishing = AlertAnalysisResult(**PHISHING_ALERT)
        assert phishing.is_critical() == True

        malware = AlertAnalysisResult(**MALWARE_ALERT)
        assert malware.is_critical() == True

        # 创建低危告警
        low_alert = {**PHISHING_ALERT, "severity": "low"}
        result = AlertAnalysisResult(**low_alert)
        assert result.is_critical() == False

    def test_request_validation(self):
        """测试请求验证"""
        # 有效请求
        request = AlertAnalysisRequest(
            raw_log="Test log content is long enough",
            alert_id="ALT-001",
            alert_name="Test",
        )
        assert request.raw_log == "Test log content is long enough"

        # 无效请求（太短）
        with pytest.raises(ValueError):
            AlertAnalysisRequest(raw_log="short")


# ============ Playbook 触发器测试 ============


class TestAlertTriggers:
    """告警触发器测试"""

    def test_critical_auto_contain_trigger(self):
        """测试高危自动遏制触发器"""
        result = AlertAnalysisResult(**MALWARE_ALERT)
        trigger_ids = get_matching_triggers(result)

        assert "critical_auto_contain" in trigger_ids
        assert "malware_response" in trigger_ids

    def test_phishing_trigger(self):
        """测试钓鱼邮件触发器"""
        result = AlertAnalysisResult(**PHISHING_ALERT)
        trigger_ids = get_matching_triggers(result)

        assert "phishing_investigation" in trigger_ids
        assert "critical_auto_contain" in trigger_ids

    def test_no_trigger_for_low_confidence(self):
        """测试低置信度不触发自动响应"""
        low_confidence_alert = {
            **PHISHING_ALERT,
            "confidence_score": 0.3,
            "verdict": "needs_investigation",
        }
        result = AlertAnalysisResult(**low_confidence_alert)
        trigger_ids = get_matching_triggers(result)

        assert "high_confidence_positive" not in trigger_ids

    def test_priority_ordering(self):
        """测试优先级排序"""
        result = AlertAnalysisResult(**MALWARE_ALERT)
        matches = get_matching_triggers(result)
        assert isinstance(matches, list)
        assert "critical_auto_contain" in matches


# ============ 性能测试 ============


class TestPerformance:
    """性能测试"""

    def test_schema_creation_speed(self):
        """测试 Schema 创建速度"""
        result = AlertAnalysisResult(**PHISHING_ALERT)
        assert result is not None

    def test_ioc_extraction_speed(self):
        """测试 IOC 提取"""
        result = AlertAnalysisResult(**PHISHING_ALERT)

        ips = result.iocs.ips
        domains = result.iocs.domains

        assert len(ips) == 2
        assert len(domains) == 2


# ============ 验收标准清单 ============

ACCEPTANCE_CRITERIA = """
# 告警分析器验收标准

## P0 - 核心功能

### Schema 验证
- [ ] 所有枚举值正确
- [ ] 数值范围约束生效
- [ ] 必需字段有值
- [ ] 时间格式正确

### IOC 提取
- [ ] IP 地址格式正确
- [ ] 域名格式正确
- [ ] URL 格式正确
- [ ] 哈希格式正确
- [ ] 统计计算正确

### 事件分类
- [ ] MITRE ATT&CK ID 格式正确
- [ ] 分类枚举覆盖完整
- [ ] 置信度计算合理

## P1 - 重要功能

### Playbook 联动
- [ ] 触发器条件评估正确
- [ ] 优先级排序正确
- [ ] 上下文映射正确

### 报告生成
- [ ] 工单模板渲染正确
- [ ] 日报模板渲染正确
- [ ] 事后分析模板正确

## P2 - 增强功能

### 性能
- [ ] Schema 创建 < 10ms
- [ ] 触发器评估 < 5ms
- [ ] 支持并发处理

## 测试用例

### 钓鱼邮件测试
- 输入: 钓鱼邮件日志
- 期望: event_category = "phishing"
- 验证: triggers = ["phishing_response"]

### 恶意软件测试
- 输入: 勒索软件告警
- 期望: severity = "critical"
- 验证: triggers = ["critical_auto_contain", "malware_response"]

### 误报测试
- 输入: 正常用户行为日志
- 期望: verdict = "false_positive"
- 验证: 无自动触发
"""


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])

    # 打印验收标准
    print(ACCEPTANCE_CRITERIA)
