# API 总览

## 适用对象

后端开发人员、需要调用 API 的集成方。

## 目标

掌握 SOC Copilot API 的模块划分、调用方式、认证机制。

## API 模块列表

| 模块 | 前缀 | 主要端点 |
|------|------|----------|
| **AI 助手** | `/api/ai/` | `chat`, `query`, `analyze-alert` |
| **告警** | `/api/alerts/` | `list`, `detail`, `analyze` |
| **剧本** | `/api/playbook*/` | `definitions`, `runs`, `execute` |
| **资产管理** | `/api/assets/` | `list`, `create`, `import` |
| **触发器** | `/api/triggers/` | `list`, `webhook`, `cron` |
| **威胁情报** | `/api/threat-intel/` | `lookup`, `batch` |
| **审计** | `/api/audit/` | `logs`, `export` |

## 认证方式

### JWT Token 认证

```bash
# 登录获取 Token
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}

# 响应
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

后续请求携带 Token：

```bash
curl -X GET http://localhost:8000/api/alerts \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### API Key 认证

```bash
curl -X GET http://localhost:8000/api/assets \
  -H "X-API-Key: your-api-key-here"
```

## 错误返回规范

```json
{
  "detail": "错误描述信息",
  "code": "ERROR_CODE",
  "status_code": 400,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

| HTTP 状态码 | 说明 |
|------------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 关键接口示例

### 告警分析

```bash
POST /api/ai/analyze-alert
Content-Type: application/json

{
  "raw_log": "2024-01-15 10:30:00 firewall DENY TCP 192.168.1.100:54321 -> 203.0.113.50:443"
}

# 响应
{
  "event_type": "initial_access",
  "severity": "high",
  "iocs": {
    "ips": ["203.0.113.50"],
    "domains": [],
    "urls": [],
    "hashes": []
  },
  "summary": "检测到可疑出站连接"
}
```

### 剧本执行

```bash
POST /api/playbook-definitions/{id}/run
{
  "mode": "dry_run",
  "input_context": {
    "alert_id": "ALT-001",
    "ioc": "203.0.113.50"
  }
}

# 响应
{
  "run_id": "RUN-001",
  "status": "pending"
}
```

### 威胁情报查询

```bash
GET /api/threat-intel/lookup?ioc=8.8.8.8&type=ip

# 响应
{
  "verdict": "malicious",
  "confidence": 0.95,
  "tags": ["botnet", "c2"],
  "provider": "otx"
}
```
