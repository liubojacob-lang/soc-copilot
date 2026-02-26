# 告警分析器

## 适用对象

安全分析师（使用告警分析功能）、开发人员（维护/扩展分析逻辑）。

## 目标

掌握告警分析的输入/输出规范，理解与剧本引擎的联动方式。

## 输入 Schema

```json
{
  "raw_log": "原始告警/日志内容（必填）",
  "alert_id": "告警 ID（可选）",
  "alert_name": "告警名称（可选）",
  "alert_source": "告警来源（可选）：siem/edr/nta/waf"
}
```

### 示例输入

```json
{
  "raw_log": "2024-01-15 10:30:00 firewall DENY TCP 192.168.1.100:54321 -> 203.0.113.50:443\nEvent: Suspicious outbound connection detected",
  "alert_name": "Suspicious Outbound Connection",
  "alert_source": "firewall"
}
```

## 输出 Schema

```json
{
  "analysis_version": "1.0",
  "analysis_timestamp": "2024-01-15T10:30:00Z",
  "model_used": "nvidia/kimi-k2.5",
  
  "event_category": "initial_access",
  "event_subcategory": "connection_to_indicator",
  "attack_technique_ids": ["T1071"],
  
  "verdict": "true_positive",
  "severity": "high",
  "confidence": "high",
  "confidence_score": 0.85,
  
  "iocs": {
    "ips": ["203.0.113.50"],
    "domains": ["evil.com"],
    "urls": [],
    "hashes": []
  },
  
  "impact": {
    "affected_assets": [
      {"hostname": "workstation-001", "criticality": "medium", "is_compromised": true}
    ],
    "business_impact_level": "medium",
    "contains_pii": false
  },
  
  "summary": "检测到工作站到恶意IP的可疑出站连接",
  "escalation_required": false,
  "suggested_playbooks": ["PB-PHISHING-RESPONSE"]
}
```

## 事件分类（MITRE ATT&CK）

| category | subcategory | ATT&CK Techniques |
|----------|-------------|-------------------|
| `initial_access` | `phishing_campaign` | T1566 |
| `initial_access` | `brute_force` | T1110 |
| `execution` | `malicious_file` | T1204 |
| `persistence` | `scheduled_task` | T1053 |
| `credential_access` | `credential_dumping` | T1003 |
| `lateral_movement` | `pass_the_hash` | T1550.002 |
| `command_and_control` | `dns_tunneling` | T1071.004 |
| `exfiltration` | `exfil_over_c2` | T1041 |

## 与 Playbook 联动字段

| 字段路径 | 可触发剧本 |
|----------|------------|
| `severity = critical/high` | `critical_auto_contain` |
| `event_category = malware` | `malware_response` |
| `event_category = phishing` | `phishing_response` |
| `impact.contains_pii = true` | `pii_breach_response` |
