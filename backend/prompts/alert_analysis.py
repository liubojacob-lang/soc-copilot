"""
告警分析 Prompt 模板
"""

ALERT_ANALYSIS_SYSTEM_PROMPT = """你是一名资深SOC分析师，精通MITRE ATT&CK框架、威胁情报分析和事件响应。

输出要求：
1. 严格按照JSON Schema格式输出
2. 时间格式使用ISO 8601
3. IOC提取需验证格式正确性
4. 处置建议必须具体可执行"""

ALERT_ANALYSIS_USER_PROMPT = """## 原始告警
```
{raw_log}
```

## 上下文
- 告警ID: {alert_id}
- 告警名称: {alert_name}
- 来源: {alert_source}

## 分析要求
1. 事件分类：映射MITRE ATT&CK技术和战术
2. 威胁判定：是否为真正威胁
3. IOC提取：IP、域名、URL、哈希
4. 实体识别：用户、主机
5. 证据链构建
6. 影响评估
7. 根因分析
8. 处置建议

## 输出格式
```json
{{
  "analysis_version": "1.0",
  "analysis_timestamp": "{timestamp}",
  "model_used": "{model_name}",
  "alert_id": "{alert_id}",
  "alert_name": "{alert_name}",
  "alert_source": "siem",
  "original_raw_log": "...",
  
  "event_category": "initial_access",
  "event_subcategory": "phishing_campaign",
  "attack_technique_ids": ["T1566", "T1566.001"],
  "attack_tactic_ids": ["TA0001"],
  
  "verdict": "true_positive",
  "severity": "high",
  "confidence": "high",
  "confidence_score": 0.85,
  
  "iocs": {{
    "ips": ["192.168.1.100"],
    "domains": ["evil.com"],
    "urls": [],
    "hashes": [],
    "emails": [],
    "file_paths": []
  }},
  "ioc_statistics": {{
    "total_count": 2,
    "ip_count": 1,
    "domain_count": 1,
    "url_count": 0,
    "hash_count": 0,
    "unique_countries": [],
    "is_research_related": false
  }},
  "enriched_iocs": [],
  
  "entities": {{"users": [], "hosts": [], "accounts": [], "processes": []}},
  "evidence_points": [],
  "timeline": [],
  
  "impact": {{
    "affected_assets": [],
    "business_impact_level": "medium",
    "data_at_risk": null,
    "estimated_recovery_time": null,
    "contains_pii": false,
    "contains_phi": false
  }},
  
  "root_cause": {{
    "primary_cause": "一句话描述",
    "attack_vector": "钓鱼邮件",
    "initial_compromise_method": "恶意链接",
    "attack_phase": "installation"
  }},
  
  "recommended_actions": [],
  "suggested_playbooks": [],
  "escalation_required": false,
  
  "summary": "一句话摘要",
  "full_narrative": "完整叙事",
  "key_findings": [],
  "next_investigation_steps": [],
  "references": [],
  
  "request_id": "{request_id}",
  "degraded_mode": false,
  "error_message": null
}}
```

只输出JSON。"""

QUICK_ANALYSIS_USER_PROMPT = """## 告警
```
{raw_log}
```

## 快速研判
判断：威胁判定、严重等级、摘要、首要IOC、建议动作

## 输出
```json
{{"verdict": "true_positive", "severity": "high", "summary": "...", "ioc_count": 5, "top_iocs": [], "recommended_action": ""}}
```
只输出JSON。"""

QUICK_ANALYSIS_SYSTEM_PROMPT = (
    """你是SOC分析师，快速研判告警。保持简洁，直接输出JSON。"""
)

PROMPT_CONFIG = {"temperature": 0.1, "max_tokens": 4096, "retry_count": 3}


def get_analysis_prompt(
    raw_log,
    alert_id="N/A",
    alert_name="N/A",
    alert_source="unknown",
    request_id="N/A",
    model_name="unknown",
):
    user_prompt = ALERT_ANALYSIS_USER_PROMPT.format(
        raw_log=raw_log[:8000],
        alert_id=alert_id,
        alert_name=alert_name,
        alert_source=alert_source,
        timestamp="2024-01-15T10:00:00Z",
        model_name=model_name,
        request_id=request_id,
    )
    return ALERT_ANALYSIS_SYSTEM_PROMPT, user_prompt


def get_quick_prompt(raw_log):
    return QUICK_ANALYSIS_SYSTEM_PROMPT, QUICK_ANALYSIS_USER_PROMPT.format(
        raw_log=raw_log
    )
