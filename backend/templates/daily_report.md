# SOC 安全运营日报

## 报告期间

**日期**: {{report_date}}  
**分析师**: {{analyst_name}}

---

## 告警概况

| 指标     | 数量                |
| -------- | ------------------- |
| 告警总数 | {{total_alerts}}    |
| 真正威胁 | {{true_positives}}  |
| 误报     | {{false_positives}} |
| 待处理   | {{pending}}         |

### 告警分布

| 等级        | 数量               | 占比              |
| ----------- | ------------------ | ----------------- |
| 🔴 Critical | {{critical_count}} | {{critical_pct}}% |
| 🟠 High     | {{high_count}}     | {{high_pct}}%     |
| 🟡 Medium   | {{medium_count}}   | {{medium_pct}}%   |
| 🟢 Low      | {{low_count}}      | {{low_pct}}%      |

---

## 重点事件

{% for incident in top_incidents %}

### {{incident.severity}} {{incident.title}}

**摘要**: {{incident.summary}}

**IOC**: {{incident.iocs}}

**状态**: {{incident.status}}

---

{% endfor %}

---

## 响应处置

| 指标         | 数值                  |
| ------------ | --------------------- |
| 剧本执行     | {{playbook_runs}}     |
| 自动化处置   | {{automated_runs}}    |
| 平均响应时间 | {{avg_response_time}} |

---

## 待处理清单

{% for alert in pending_alerts %}

- **{{alert.priority}}** {{alert.name}} ({{alert.age}})
  {% endfor %}

---

## 运营建议

{% for rec in recommendations %}

### {{rec.priority}} {{rec.title}}

{{rec.description}}
{% endfor %}

---

_报告生成时间: {{generated_at}}_
