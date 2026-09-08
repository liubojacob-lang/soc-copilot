# Roadmap

> 来源：PROJECT_FINAL_AUDIT.md 的 P2/P3 项 + 范围决策。当前版本 v0.9.2（🟡 CONDITIONAL CLOSE）。

## v0.9.3（上线后第一个迭代）
- [ ] admin/settings 前端实现（后端 /api/v1/admin/settings CRUD 已完整）
- [ ] SIEM / UEBA 深度页等 API-only 模块的界面化（或正式裁剪，见 docs/MODULE_SCOPE.md）
- [ ] cases 列表 count 批量查询（受扫描器误报暂缓，见 Backlog 记录）
- [ ] 多副本部署下审计归档迁移到共享/对象存储
- [ ] chat 路径接入熔断器（与结构化生成一致）
- [ ] 修复 tests/test_websocket_pubsub_bridge 的环境依赖失败（Redis 前置条件）

## v0.10.0
- [ ] k8s Secret 模板化（外部 secrets operator 接入）
- [ ] Prometheus 告警规则启用 alertmanager 通知链路
- [ ] 用户级 AI 配额与成本看板
- [ ] 通知渠道管理 UI（飞书/Slack/SMTP）
- [ ] Wazuh 实时流管理界面（/api/v1/wazuh/stream 已有 API）

## v1.0.0（对外发布门槛）
- [ ] git 历史密钥清理（filter-repo）+ 全量凭据轮换记录
- [ ] 移动端与无障碍完整审计（WCAG AA 抽检）
- [ ] 性能压测报告（k6：登录/列表/导入/chat 四场景）
- [ ] 真实流式覆盖 generate-report（当前仅 chat）
- [ ] 正式裁剪或实现演示模块（cloud-native K8s/云事件）
