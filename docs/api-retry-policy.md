# API 重试与限流策略

## 限流矩阵

| 端点 | 限流 | 窗口 | 说明 |
| -- | -- | -- | -- |
| POST /api/v1/auth/login | 5 | 60s | 防暴力破解；另有 5 次失败锁定 30 分钟 |
| POST /api/v1/ai/chat | 30 | 60s | LLM 成本防护 |
| POST /api/v1/ai/query | 60 | 60s | LLM 成本防护 |
| POST /api/v1/ai/analyze-alert | 30 | 60s | LLM 成本防护 |
| POST /api/v1/ai/recommend-playbooks | 30 | 60s | LLM 成本防护 |
| POST /api/v1/ai/generate-report、/api/v1/generate-report | 10 | 60s | 单次成本最高的端点 |
| POST /api/v1/ai/models/test | 10 | 60s | 触发真实 LLM 调用 |
| POST /api/v1/ai/models/refresh | 2 | 60s | admin-only；触发全目录重建 |

- 限流按客户端 IP（经反代取真实 IP），Redis 计数，生产 Redis 不可用时 fail-closed。
- 超限返回 `429`，前端应提示用户稍后重试。
- 测试环境（`ENVIRONMENT=test`）自动跳过限流。

## 重试策略

**客户端**：仅 401 时自动刷新令牌并重放一次；其余错误不自动重试（避免放大故障）。

**LLM 调用**（服务端）：
- `generate_structured`：JSON 解析失败重试最多 2 次，带指数退避；
- 熔断器：连续 5 次失败熔断 30 秒，期间快速失败并降级；
- chat 路径失败直接降级为本地规则引擎文案（HTTP 200 + `degraded` 标记）。

**其他业务 API**：默认不重试。写操作通过幂等键（playbook 提交）与唯一约束（告警摄取）保证重复请求安全。

## 409 语义

`POST /api/v1/assets`、`PATCH /api/v1/assets/{id}` 在 hostname/IP 已存在时返回 **409 Conflict**（detail 含冲突字段与值）；其余参数错误仍为 400。
