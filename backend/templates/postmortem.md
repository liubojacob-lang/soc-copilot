# 安全事件事后分析报告

## 文档信息

| 字段         | 值                 |
| ------------ | ------------------ |
| **报告编号** | {{report_id}}      |
| **事件名称** | {{incident_name}}  |
| **事件级别** | {{incident_level}} |
| **发现时间** | {{discovery_time}} |
| **响应时间** | {{response_time}}  |
| **主分析师** | {{lead_analyst}}   |

---

## 执行摘要

{{executive_summary}}

### 关键指标

| 指标       | 数值                  |
| ---------- | --------------------- |
| 影响范围   | {{impact_scope}}      |
| 受影响系统 | {{affected_systems}}  |
| 数据泄露   | {{data_exfiltration}} |

---

## 时间线摘要

| 阶段     | 时间                   | 时长    |
| -------- | ---------------------- | ------- |
| 初始入侵 | {{initial_compromise}} | -       |
| 发现     | {{discovery}}          | {{ttd}} |
| 响应     | {{response}}           | {{ttr}} |

---

## 攻击链分析

{% for stage in kill_chain %}
| {{stage.phase}} | {{stage.activity}} | {{stage.timestamp}} |
{% endfor %}

---

## 根因分析

**主要根因**: {{primary_cause}}

**攻击向量**: {{attack_vector}}

**横向移动**: {% for path in lateral_movement %}{{path}} {% endfor %}

**数据外泄**: {% for data in exfiltrated_data %}{{data}} {% endfor %}

---

## 影响评估

### 业务影响

| 维度       | 评估                    |
| ---------- | ----------------------- |
| 业务连续性 | {{business_impact}}     |
| 财务影响   | {{financial_impact}}    |
| 声誉影响   | {{reputational_impact}} |

### 受影响实体

{% for entity in affected_entities %}

- **{{entity.type}}**: {{entity.name}} ({{entity.status}})
  {% endfor %}

---

## 处置措施

### 遏制

{% for action in containment_actions %}

- {{action}}
  {% endfor %}

### 根除

{% for action in eradication_actions %}

- {{action}}
  {% endfor %}

### 恢复

{% for action in recovery_actions %}

- {{action}}
  {% endfor %}

---

## 经验教训

### 做得好

{% for item in what_went_well %}

- {{item}}
  {% endfor %}

### 需要改进

{% for item in improvements %}

- {{item}}
  {% endfor %}

---

## 改进建议

### 立即行动 (0-30天)

{% for action in immediate_actions %}

- **{{action.priority}}** {{action.description}} (负责人: {{action.owner}})
  {% endfor %}

### 长期改进 (90天+)

{% for action in long_term_actions %}

- **{{action.priority}}** {{action.description}} (负责人: {{action.owner}})
  {% endfor %}

---

## 签署

| 角色     | 姓名 | 日期 |
| -------- | ---- | ---- |
| 主分析师 |      |      |
| SOC经理  |      |      |
| 安全总监 |      |      |

---

_报告生成时间: {{generated_at}}_
