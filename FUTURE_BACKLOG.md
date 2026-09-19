# FUTURE BACKLOG

> 由 PROJECT_FINAL_AUDIT.md（🟡 CONDITIONAL CLOSE）派生。收尾后按序消化，不阻塞当前版本。

## 上线前置（P1，与 PROJECT_FINAL_AUDIT.md 第五节对应）
- [ ] P1-1 修复 lint 门禁：后端 `ruff check --fix --unsafe-fixes` 逐项复核 94 处存量风格错误；前端 `npm run i18n:sync` 同步 cloudNative.demoNotice
- [ ] P1-2 数据库备份：pg_dump cron（compose/k8s CronJob）+ 恢复演练一次，写入 Makefile
- [ ] P1-3 生产部署演练：干净机器 `docker compose -f docker-compose.prod.yml up`（先补 JWT_SECRET/SECRET_ENCRYPTION_KEY/CORS_ORIGINS/HTTP_ALLOWED_HOSTS/DOCKERHUB_USERNAME/API_URL），TLS 走 certbot，修复 Scripts/deploy/deploy.sh 的 cd 路径 bug
- [ ] P1-4 git 历史清理决策：外发/开源前用 git filter-repo 清除 768d84a 的 env 文件与 docs 中旧密钥 blob
- [ ] P1-5 轮换 NVIDIA API key（NVIDIA 控制台手动操作）
- [ ] P1-6 重写 docs/09-ops-deploy.md 为 PostgreSQL 现实；补 CHANGELOG（v0.9.0 → 当前）

## P2（上线后第一个迭代）
- [ ] threat-hunting / ueba / correlation 页面补错误态与空态
- [ ] admin/settings 前端实现（后端 API 已完整）或从导航移除
- [ ] 死代码清理：workers/alert_consumer.py、QuickActions、lib/api/ai.ts 断链函数、websocket 死组件、/test 页面
- [ ] /metrics 与详细健康探针加认证或网络隔离
- [ ] JWT access 有效期 12h → 60min
- [ ] k8s 补 alert-worker 清单
- [ ] 监控栈补齐：prometheus rules/面板挂载、target 改为服务名、alertmanager
- [ ] cases 列表 count 查询合并（轻 N+1）
- [ ] 多副本部署时审计归档改为共享存储/对象存储
- [ ] correlated_events.created_at 改 DateTime + 迁移
- [ ] audit 页面放行 auditor 角色
- [ ] HeroPrompts 等 116 处硬编码中文接入 next-intl

## P3（Future）
- [ ] AI 真实 SSE 流式输出（替换前端打字机模拟）
- [ ] 移除 OpenRouter 假 provider（指向 NVIDIA 端点的遗留）
- [ ] SIEM / UEBA / monitoring-alerts / alert-stream / prompt-registry / ai-tasks 前端化（或明确裁剪）
- [ ] 移动端 + 无障碍（对比度/focus/tab 序）系统审计
- [ ] 大列表虚拟化、bundle 分析、首屏优化
- [ ] 用户级 AI 配额与成本看板
- [ ] 修复 test_websocket_pubsub_bridge 环境依赖型失败（加 Redis 前置条件）
- [ ] chat 路径接入熔断器（与结构化生成一致）
- [ ] 真实 K8s/容器数据源接入：替换 cloud-native 模块中的示例连接器，对接生产环境集群 API 与真实事件流

