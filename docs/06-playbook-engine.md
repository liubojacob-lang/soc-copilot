# Playbook 引擎（DAG 工作流）

## 适用对象

自动化工程师（编写/维护剧本）、安全运营（设计响应流程）。

## 目标

掌握 DAG 剧本定义、节点类型，执行机制、安全限制。

## Playbook 定义 Schema

```yaml
name: "钓鱼邮件响应剧本"
version: "1.0.0"
description: "处理钓鱼邮件告警的自动响应"

trigger:
  type: "alert"
  conditions:
    - field: "alert.event_category"
      operator: "eq"
      value: "phishing"

nodes:
  - id: "extract_iocs"
    name: "提取威胁指标"
    type: "extract_iocs"
    inputs:
      raw_log: "{{alert.raw_log}}"

  - id: "ti_lookup"
    name: "威胁情报查询"
    type: "ti_lookup_otx"
    inputs:
      iocs: "{{context.extract_iocs}}"

  - id: "isolate_host"
    name: "隔离主机"
    type: "http_request"
    config:
      url: "https://edr.company.com/isolate"
      method: "POST"
    inputs:
      hostname: "{{alert.hostname}}"

edges:
  - source: "extract_iocs"
    target: "ti_lookup"
  - source: "ti_lookup"
    target: "isolate_host"
```

## 节点类型

| 类型 | 说明 |
|------|------|
| `extract_iocs` | 从日志提取 IOC |
| `ti_lookup_otx` | 查询 OTX |
| `http_request` | HTTP 请求 |
| `decision` | 条件分支 |
| `send_email` | 发送邮件 |
| `slack_notify` | Slack 通知 |
| `human_approval` | 人工审批 |
| `generate_report` | 生成报告 |

## 状态机

```
PENDING → RUNNING → SUCCESS / FAILED / SKIPPED
                 ↑
                 └── WAITING_APPROVAL（人工审批）
```

## dry_run vs run

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| `dry_run` | 模拟执行，不发外部请求 | 测试剧本、验证逻辑 |
| `run` | 实际执行 | 生产环境响应 |

## 队列管理器

```python
class RunQueueManager:
    def __init__(self, max_concurrent: int = 3):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def submit(self, run_id: str):
        async with self.semaphore:
            await execute_playbook(run_id)
```

## 手动审批节点

```yaml
- id: "approval"
  name: "人工审批隔离"
  type: "human_approval"
  config:
    approvers: ["soc-manager@company.com"]
    timeout_hours: 24
    auto_approve: false
```

## Slack 通知节点

```yaml
- id: "slack_alert"
  name: "Slack 通知"
  type: "slack_notify"
  config:
    channel: "#soc-alerts"
    message: |
      🚨 告警: {{alert.name}}
      🏷️ 严重: {{alert.severity}}
```

## 安全限制

### 网络访问限制

```python
ALLOWED_DOMAINS = [
    "edr.company.com",
    "firewall.company.com",
    "otx.alienvault.com"
]

BLOCKED_IP_RANGES = [
    "127.0.0.0/8",
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16"
]
```

### 敏感数据脱敏

```python
SENSITIVE_FIELDS = ["password", "api_key", "secret", "token"]

def sanitize_context(context: dict) -> dict:
    sanitized = {}
    for key, value in context.items():
        if any(s in key.lower() for s in SENSITIVE_FIELDS):
            sanitized[key] = "***REDACTED***"
    return sanitized
```
