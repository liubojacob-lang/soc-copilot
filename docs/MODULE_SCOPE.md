# 模块范围声明（Module Scope）

> 目的：明确「后端有 API、前端无界面」模块的产品定位，消除验收中的范围歧义。
> 决策日期：2026-09-08。

## API-First 模块（保留，无计划 UI）

以下模块提供 REST API 供程序化集成（SIEM/SOAR 对接、脚本自动化），按设计不设界面：

| 模块 | 前缀 | 定位 |
| -- | -- | -- |
| SIEM 日志存储/搜索 | /api/v1/siem | 上游 SIEM 写入与检索接口 |
| 告警富化 | /api/v1/alert-enrichment | 管道式调用（摄取流程内部使用） |
| 告警推送 Loki | /api/v1/alerts/send | 转发到外部 Loki |
| Wazuh 流管理 | /api/v1/wazuh/stream | 流订阅生命周期管理 |
| 监控告警规则 | /api/v1/monitoring/alerts | 告警规则 CRUD（供告警管道消费） |
| Prompt Registry | /api/v1/prompt-registry | 提示词版本管理（集成方使用） |
| AI 后台任务 | /api/v1/ai-tasks | 异步任务提交/轮询（脚本/集成） |
| 剧本导出子能力 | /api/v1/export/* | 合规导出（脚本化） |

这些模块纳入 API 测试与文档范围；UI 需求若出现，走 roadmap 评审。

## 有界面的核心模块

dashboard、alerts（列表/详情/导入）、cases、assets、playbooks（定义/执行/审批/版本）、
threat-intel、threat-hunting、marketplace、triggers、reports、ai-assistant、
settings（api-keys/notifications/ai-models）、admin（users/dashboard/health/secrets/audit）。

## 演示/受限能力（明示标签）

- 云原生页（/cloud-native）：容器扫描（Trivy）与 Falco 为真实集成；K8s 资源/扫描、
  云事件 4 个端点返回标注 `simulated: true` 的演示数据，页面有琥珀色演示横幅。
  正式启用需配置集群凭证或接入 Trivy/Clair。
- 资产云发现（/api/v1/assets/discover）：未配置云凭证时返回样本数据；
  生产使用前必须配置凭证，否则不要调用。

## 已裁剪/待决策

- Kafka message broker：`MESSAGE_BROKER=kafka` 会抛 NotImplementedError（默认 redis 不受影响）；
  待决策：实现或移除（P3）。
- OpenRouterProvider：历史遗留指向 NVIDIA 端点，无独立价值，v0.10 移除。
