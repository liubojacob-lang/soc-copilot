---
## 安全告警工单

### 基本信息
| 字段 | 值 |
|------|-----|
| **工单编号** | `{{alert_id}}` |
| **告警名称** | `{{alert_name}}` |
| **告警来源** | `{{alert_source}}` |
| **分析时间** | `{{analysis_timestamp}}` |
| **模型** | `{{model_used}}` |

---

### 事件分类

| 分类             | 值                          |
| ---------------- | --------------------------- |
| **事件类别**     | {{event_category}}          |
| **子类别**       | `{{event_subcategory}}`     |
| **MITRE ATT&CK** | {{attack_technique_ids}}    |
| **攻击链阶段**   | {{root_cause.attack_phase}} |

---

### 判定结果

| 指标         | 结果                                   |
| ------------ | -------------------------------------- |
| **威胁判定** | {{verdict_icon}} {{verdict}}           |
| **严重等级** | {{severity_icon}} {{severity}}         |
| **置信度**   | {{confidence}} ({{confidence_score}}%) |

---

### 威胁指标 (IOC)

| 类型 | 数量             | 详情        |
| ---- | ---------------- | ----------- |
| IP   | {{ip_count}}     | {{ips}}     |
| 域名 | {{domain_count}} | {{domains}} |
| URL  | {{url_count}}    | {{urls}}    |
| 哈希 | {{hash_count}}   | {{hashes}}  |

---

### 受影响资产

{% for asset in affected_assets %}

- {{asset.hostname}} ({{asset.ip_addresses}}) - {{asset.criticality}} {% if asset.is_compromised %}**已失陷**{% endif %}
  {% endfor %}

**业务影响**: {{impact.business_impact_level}}

{% if impact.contains_pii %}**⚠️ 包含个人信息**{% endif %}

---

### 根因分析

**主要根因**: {{root_cause.primary_cause}}

**攻击向量**: {{root_cause.attack_vector}}
**入侵方式**: {{root_cause.initial_compromise_method}}

---

### 处置建议

{% for action in recommended_actions %}

#### {{action.priority}} {{action.title}} ({{action.category}})

{{action.description}}

{% if action.commands %}
**执行命令**:
{% for cmd in action.commands %}

```bash
{{cmd}}
```

{% endfor %}
{% endif %}

{% endfor %}

{% if escalation_required %}

> 🚨 **需要升级**: {{escalation_rationale}}
> {% endif %}

---

### 分析摘要

{{summary}}

### 完整叙事

{{full_narrative}}

### 关键发现

{% for finding in key_findings %}

- {{finding}}
  {% endfor %}

### 后续步骤

{% for step in next_investigation_steps %}

- [ ] {{step}}
      {% endfor %}

---

_生成时间: {{analysis_timestamp}}_
