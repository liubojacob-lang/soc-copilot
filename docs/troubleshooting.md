# Troubleshooting

按症状排查。每条给出原因与处置。

## 前端

### 页面 502 / 打不开（本地开发）
- dev server 监听 `[::1]:3003`（IPv6）。用浏览器访问 `http://localhost:3003` 通常自动回退；
  curl 测试请用 `http://[::1]:3003`。
- 执行过 `npm run build` 会使运行中的 dev server 失效（.next 被替换）——重启
  `npm run dev` 即可。
- 端口被占用时 Next 会自动换端口，以启动日志为准。

### 登录后立即跳回 /login
- 后端刚重启（开发模式每次重启自动生成新 `JWT_SECRET`），旧 cookie 全部失效——重新登录。
- 检查浏览器是否禁用了 cookie（会话依赖 HttpOnly cookie）。

### 页面数据为空但有网络请求记录
- 看响应状态：401 → 会话过期；403 → 角色不足；500 → 看后端日志 trace_id。

## 后端

### 启动失败：ENVIRONMENT 校验报错
- 生产模式（`STRICT_PRODUCTION_CHECKS=true`）要求 `JWT_SECRET` ≥32 字符、禁止默认口令。
  用 `openssl rand -base64 64` 生成。
- `SECRET_KEY` 已废弃：应用读取的是 `JWT_SECRET`。

### 启动失败：compose 变量缺失
- `required variable X is missing`：按 `.env.production.example` 补齐并通过
  `docker compose --env-file ... config -q` 验证。

### 迁移失败
- `alembic upgrade head` 在 FK 创建失败：按报错清理孤儿数据后重试
  （0003 迁移的失败模式是显式失败，不产生静默损坏）。
- 开发库升级到 0004 前先跑
  `python scripts/normalize_correlated_event_timestamps.py`（仅 SQLite 旧库需要）。

### 429 Too Many Requests
- 命中限流。矩阵见 `docs/api-retry-policy.md`；等窗口过去即可。
- 登录连续失败 5 次会锁账户 30 分钟（admin 可在用户页解锁）。

### AI 相关
- 报告内容出现 "Automated generation failed"：上游 LLM 失败或熔断器打开
  （30 秒冷却），稍后重试；检查对应 provider 的 API key。
- chat 响应是规则引擎文案：同上，响应中带降级标记。
- `AI_PROVIDER` 应指向有有效 key 的 provider（推荐 `nvidia`）。

## 数据

### 资产/案例数据"消失"
- v0.9.2 之前的版本存在 flush-不-commit 的缺陷（提交后丢弃）。升级后新写入正常；
- 旧损坏数据：assets.tags 非法 JSON 已由读取端容错；如需修复存储值运行
  v0.9.2+ 的 seed 或手工 UPDATE 为 JSON 数组。

### 磁盘增长
- retention 每 6 小时清理告警/案例时间线/SIEM 日志等（保留天数见 .env）。
- 审计日志 90 天归档到 `backend/data/audit_archives/`。
