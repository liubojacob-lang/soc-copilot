# 安全设计

## 适用对象

安全工程师、审计人员、需要理解权限模型的管理员。

## 目标

理解 SOC Copilot 的安全设计，包括 RBAC、审计日志、数据脱敏。

## RBAC 角色权限模型

| 角色 | 权限 | 说明 |
|------|------|------|
| **admin** | 全部 | 系统管理员 |
| **soc_manager** | 查看+操作+审批 | SOC 团队负责人 |
| **analyst** | 查看+分析+响应 | 安全分析师 |
| **viewer** | 只读 | 只读用户 |

### 权限矩阵

| 功能 | admin | soc_manager | analyst | viewer |
|------|-------|-------------|---------|--------|
| 查看告警 | ✅ | ✅ | ✅ | ✅ |
| 分析告警 | ✅ | ✅ | ✅ | ❌ |
| 执行剧本 | ✅ | ✅ (dry_run) | ❌ | ❌ |
| 审批剧本 | ✅ | ✅ | ❌ | ❌ |
| 资产管理 | ✅ | ✅ | ✅ | ❌ |
| 系统设置 | ✅ | ❌ | ❌ | ❌ |

## API Key 管理

```bash
# 创建 API Key
POST /api/api-keys
{
  "name": "Playbook Runner",
  "permissions": ["playbooks:execute"]
}

# 响应
{
  "key_id": "key_abc123",
  "secret": "sk_live_xyz789..."  # ⚠️ 只显示一次
}

# 使用
curl -H "X-API-Key: key_abc123" \
     -H "X-API-Secret: sk_live_xyz789..." \
     http://localhost:8000/api/alerts
```

## 操作审计

### 审计范围

| 类别 | 操作 | 记录内容 |
|------|------|----------|
| 认证 | 登录/登出 | 用户、IP、时间、结果 |
| 告警 | 查看/分析 | 告警ID、操作人、时间 |
| 剧本 | 创建/修改/执行 | 剧本ID、模式、输入/输出 |
| 资产 | 创建/修改/删除 | 资产ID、操作人、变更 |

### 审计日志 Schema

```json
{
  "id": "AUD-001",
  "timestamp": "2024-01-15T10:30:00Z",
  "user_id": "user_001",
  "user_name": "admin",
  "action": "playbook.execute",
  "resource_id": "run_001",
  "result": "success",
  "ip_address": "192.168.1.100"
}
```

## 日志策略

### 敏感信息脱敏

```python
SENSITIVE_PATTERNS = [
    (r'password["\s:]+[^\s"]+', 'password: ***'),
    (r'api_key["\s:]+[^\s"]+', 'api_key: ***'),
    (r'token["\s:]+[^\s"]+', 'token: ***'),
]

def sanitize_log(message: str) -> str:
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = re.sub(pattern, replacement, message)
    return message
```

### 日志级别

| 级别 | 场景 | 示例 |
|------|------|------|
| **DEBUG** | 详细调试信息 | API 请求/响应 |
| **INFO** | 业务操作 | 登录，分析、执行 |
| **WARNING** | 异常但可处理 | OTX 查询失败降级 |
| **ERROR** | 错误 | API 异常、任务失败 |

## 外部接口调用限制

### CORS 配置

```python
origins = [
    "http://localhost:3003",
    "https://soc.company.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 速率限制

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/ai/analyze-alert")
@limiter.limit("10/minute")  # 10 次/分钟
async def analyze_alert(request: Request):
```
