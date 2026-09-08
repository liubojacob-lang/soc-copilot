# 管理员手册（Admin）

## 1. 引导管理员
- 首次启动由 `BOOTSTRAP_ADMIN_USERNAME/PASSWORD` 创建 admin 账户，`must_change_password=true`——首次登录会被强制改密。请立即改为强密码（≥12 字符，禁用历史最近 5 个密码复用）。

## 2. 用户与角色（/admin/users）
- 角色：admin（全部）、analyst（业务操作）、auditor（审计只读）。
- 审计日志可见性：admin/auditor 看全部；analyst 仅看自己的操作记录。
- 登录保护：5 次/分钟限流；连续 5 次失败锁定 30 分钟，可在 `/admin` 解锁。
- API Key（/settings/api-keys）：用于程序化访问，仅创建时可见。

## 3. Secrets（/admin/secrets）
- Playbook 变量引用的加密凭据（Fernet，密钥为 `SECRET_ENCRYPTION_KEY`）。
- **该密钥丢失 = 所有已存 secret 无法解密**，务必离线备份。
- 值仅创建时可见，之后只显示掩码。

## 4. AI 模型管理（/settings/ai-models）
- 目录默认 4 个模型（Auto + 3 个具体模型），启动时自动播种（upsert，不删除自建模型）。
- `/ai/models/refresh`（admin-only）会按推荐列表重建目录。
- 模型连通性测试走真实 LLM 调用（限流 10/分钟）。

## 5. 系统设置 API（/api/v1/admin/settings）
- 超时等运行参数支持动态 CRUD 与热加载（当前无前端页面，使用 REST）。

## 6. 备份与恢复
- `make db-backup` / `make db-restore FILE=...`；k8s 用 `k8s/10-backup-cronjob.yaml`。
- 详见 `docs/09-ops-deploy.md` 第 4 节。**每季度至少演练一次恢复。**

## 7. 审计
- /admin/audit 查询全部操作日志（支持 action 前缀、状态码类别、时间范围过滤）。
- 90 天后自动归档至 `data/audit_archives/`（gzip）；归档目录需纳入备份。

## 8. 安全基线核查清单
- [ ] `JWT_SECRET`/`SECRET_ENCRYPTION_KEY`/`DB_PASSWORD`/`REDIS_PASSWORD` 均为独立强随机值
- [ ] bootstrap admin 已改密
- [ ] CORS_ORIGINS 收敛到真实域名
- [ ] 证书自动续期可用（certbot 容器）
- [ ] 备份恢复演练记录在案
