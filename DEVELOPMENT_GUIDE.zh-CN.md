# SOC Copilot — 开发指南

> 基于全代码库分析自动生成。这是一份活文档,架构变更时请同步更新。
> 项目:**SOC Copilot** v0.8.2 · 一个安全运营中心(SOC)平台,提供 AI 辅助告警分诊、基于 DAG 的自动化剧本(playbook)、威胁情报富化以及 Wazuh 集成。

---

## 目录
1. [项目扫描(概览)](#1-项目扫描概览)
2. [代码地图](#2-代码地图)
3. [架构](#3-架构)
4. [数据库分析](#4-数据库分析)
5. [API 分析](#5-api-分析)
6. [核心业务分析](#6-核心业务分析)
7. [关键模块](#7-关键模块)
8. [开发快速上手](#8-开发快速上手)

---

## 1. 项目扫描(概览)

**项目简介:** 一个全栈 SOC 平台,接入安全告警(主要来自 Wazuh),使用大语言模型(LLM)进行分析/分诊,结合威胁情报(OTX、AbuseIPDB)进行富化,关联事件,运行自动化响应剧本(DAG 引擎),并将结果实时推送到仪表盘。

**服务对象:** 从事告警分诊、威胁狩猎、应急响应和合规报告的安全分析师。

### 技术栈

| 层级 | 技术 | 版本 |
|-------|-----------|---------|
| **后端语言** | Python | 3.11+(异步) |
| **后端框架** | FastAPI | 0.135.1 |
| **ORM** | SQLAlchemy(异步) | 2.0+ |
| **数据库(开发)** | SQLite + aiosqlite | - |
| **数据库(生产)** | PostgreSQL(通过 `DATABASE_URL`) | - |
| **缓存/队列/消息代理** | Redis | 7.2.1 |
| **向量库(RAG)** | ChromaDB | 1.5.2 |
| **机器学习** | scikit-learn | 1.4.0(UEBA / 关联) |
| **数据库迁移** | Alembic | 1.14.0 |
| **前端语言** | TypeScript | 5(严格模式) |
| **前端框架** | Next.js(App Router) | 16.2.3 |
| **UI 运行时** | React | 19 |
| **样式** | Tailwind CSS | 3.4 |
| **数据获取** | TanStack Query | 5.90 |
| **国际化** | next-intl | 4.8 |
| **状态管理** | Zustand + 自定义 `useSyncExternalStore` | - |
| **图谱可视化** | ReactFlow | 11.11 |
| **图表** | Recharts | 3.7 |
| **测试(前端)** | Vitest + Playwright | 4 / 1.40 |
| **测试(后端)** | pytest(+ 覆盖率) | - |
| **Lint/格式化** | Ruff + Black + isort(后端);ESLint + Prettier(前端) | - |
| **可观测性** | OpenTelemetry + Prometheus + Sentry | - |
| **部署** | Docker / docker-compose / Kubernetes(`k8s/`) | - |
| **CI/CD** | GitHub Actions(`.github/workflows/`:ci-cd、security、pre-commit) | - |

### LLM 提供商(6 个,通过 `LLMFactory`)
`zhipu`(GLM-4,**默认**) · `claude`(Anthropic) · `openai` · `nvidia`(Llama-3.1-405b) · `moonshot`(Kimi) · `openrouter`。均为通过共享 `httpx.AsyncClient` 的远程 HTTP API。

---

## 2. 代码地图

### 顶层目录结构

```
sec/
├── backend/                  # FastAPI API 服务端(Python)
├── frontend/                 # Next.js App Router 单页应用(TypeScript)
├── ai-assistant-release/     # 独立可嵌入的 AI 助手组件
├── k8s/                      # Kubernetes 清单
├── nginx/                    # 反向代理配置
├── docker-compose*.yml       # 基础 + 生产 + 安全 + override
├── docs/                     # 项目文档(50+ 文件)
├── scripts/ , Lib/           # 杂项辅助脚本
├── AGENTS.md                 # 代理/贡献者指南(按角色划分工作流)
├── README.md                 # 项目主 README
└── package.json              # 根工作区(npm workspaces:frontend)
```

### 后端地图(`backend/`)

| 目录 | 用途 | 关键文件 |
|-----|---------|-----------|
| `main.py` | **应用入口** — FastAPI 应用、36 个路由、14 个中间件、lifespan | — |
| `core/` | 横切基础设施:config、security、logging、http_client、cache、**lifecycle**、**prompt_sanitizer**、csrf、ssrf_protection、token_blacklist、metrics、response、validators、sensitive_data、security_validators | `config.py`、`lifecycle.py` |
| `core/enums/` | 共享枚举(`error_codes`) | — |
| `config/` | 静态配置(elasticsearch、wazuh) | — |
| `db/` | 异步 SQLAlchemy 引擎 + `AsyncSessionLocal` + `Base`;SQLite/PostgreSQL 切换 | `session.py` |
| `models/` | **34 个 SQLAlchemy 模型**(见第 4 节) | — |
| `schemas/` | Pydantic 请求/响应 DTO(24 个文件) | — |
| `routers/` | **38 个 FastAPI 路由**(见第 5 节) | — |
| `services/` | 业务逻辑 — 37 个顶层文件 + 9 个子包(见第 6 节) | — |
| `repositories/` | 数据访问层,封装模型(17 个 repo + `base.py`) | — |
| `middleware/` | 14 个中间件(audit、authz、csrf、idempotency、observability、performance、rate_limiter、request_context、security_headers、tenant、trace、exception) | — |
| `dependencies/` | FastAPI 依赖提供者(auth、rbac、tenant、audit、authorization) | — |
| `playbook_engine/` | DAG 自动化引擎 — `dag/`、`v6_linear/`、`v7_dag/`、`triggers/`、`notifications/`、`adapter.py`(见第 7 节) | — |
| `playbook_engine/v7_dag/plugins/` | **15 个内置 DAG 节点插件**(action_plan、asset_enrich、decision、extract_iocs、generate_report、http_request、human_approval、normalize、otx_lookup、parse_json、risk_score、slack_notify、sleep、timeline_build) | — |
| `integrations/` | 外部客户端 — `otx_client`(AlienVault OTX) | — |
| `marketplace/` | (当前为空 — 剧本市场逻辑在 `services/marketplace_service.py`) | — |
| `workers/` | 后台工作器 — `alert_worker` | — |
| `scripts/` | 运维脚本 — `archive_old_data`、`unlock_user` | — |
| `migrations_alembic/versions/` | **20 个 Alembic 迁移**(最新:`v1_3_0_marketplace`) | — |
| `tests/` | pytest 测试套件 + `conftest.py` | — |
| `prompts/`, `templates/` | LLM 提示词模板、报告模板 | — |
| `observability/` | 链路追踪 + JSON 日志配置 | `tracing.py`、`logging.py` |

### 前端地图(`frontend/`)

| 目录 | 用途 |
|-----|---------|
| `app/[locale]/` | **所有页面**位于 locale 段下(`en`/`zh`) — 见 2.1 |
| `app/api/` | Next.js API 路由垫片(shims) |
| `components/` | UI 组件,分 13 个子目录(`alert`、`alerts`、`chat`、`common`、`dag`、`impact`、`monitor`、`playbook`、`providers`、`tabs`、`threat_intel`、`websocket`)及顶层(`Navigation`、`ClientLayout`、`ChatHistorySidebar`、`GlobalSearch`、`Toast`、`WebVitals`、`AlertWebSocket`) |
| `components/common/` | 共享基础组件(Button、Card、Input、Skeleton 系列、VirtualList、ErrorBoundary、ResponsiveLayout、SkipToContent) |
| `stores/` | `authStore`(自定义)、`notificationStore`、`themeStore`(Zustand+persist) |
| `hooks/` | `useMonitor`(SSE+轮询)、`useCachedQuery`、`usePlaybooks`、`usePermission`、`useChatHistory`、`useAutoSave`、`useKeyboardShortcuts` |
| `lib/` | `api-client.ts`(主)、`api/client.ts`(遗留)、领域模块 `lib/api/*`(alerts、ai、assets、history、ioc、triggers、secrets、playbooks、auth)、`auth.ts`、`csrf.ts`、`queryClient.ts`、`cache.ts`、`sentry.ts`、`monitor.ts` |
| `lib/api/` | 领域 API 模块 + `legacy.ts` 兼容垫片(`api`、`api_v7`、`api_v73`、`api_v74`) |
| `i18n/` + `messages/` | next-intl 路由(`en`/`zh`,前缀:always);25 个拆分命名空间 + 单体 `en.json`/`zh.json` |
| `types/` | TypeScript 领域类型(含 `wazuh`) |
| `providers/` | **空目录**(遗留)— 真正的 provider 在 `components/providers/QueryProvider.tsx` |
| `e2e/` | Playwright 测试套件(admin、ai、alerts、auth、dashboard、i18n、marketplace、playbooks、reports、security、threat-intel) |

#### 2.1 前端路由(位于 `/[locale]/` 下)
首页(`/`) · login · alerts · alerts/[id] · playbooks · playbooks/definitions · playbooks/approvals · ai-assistant · threat-intel · threat-intel/dashboard · threat-hunting · monitor · marketplace · assets · reports · audit · correlation · cloud-native · ueba · triggers · triggers/webhook/new · triggers/cron/new · settings · settings/notifications · settings/api-keys · settings/ai-models · admin/{dashboard,users,settings,secrets,audit,health} · test

---

## 3. 架构

### 3.1 总体架构图

```
        ┌─────────────────────────────────────────────────────────────┐
        │                        客户端(浏览器)                       │
        │  Next.js 16 / React 19 / TanStack Query / Zustand / WS+SSE   │
        └───────────────┬───────────────────────────┬──────────────────┘
                        │ HTTPS(/api → :8000 代理) │ WebSocket / SSE
                        ▼                            ▼
        ┌─────────────────────────────────────────────────────────────┐
        │                     FastAPI 应用(main.py)                   │
        │  14 个中间件:trace → request_context → tenant → audit →     │
        │    authz → rbac → csrf → idempotency → rate_limit →         │
        │    security_headers → performance → observability →         │
        │    exception_handler                                        │
        │  38 个路由 → 服务 → 仓储 → 模型 → 数据库                     │
        └──┬───────────┬───────────┬───────────────┬────────────┬──────┘
           │           │           │               │            │
           ▼           ▼           ▼               ▼            ▼
       ┌───────┐  ┌─────────┐ ┌──────────┐  ┌──────────┐  ┌─────────┐
       │SQLite/│  │ Redis   │ │ ChromaDB │  │ OTX/TI   │  │ Wazuh   │
       │Postgres│ │ 消息代理/│ │ (RAG     │  │ 情报源    │  │ (告警)  │
       │       │  │ 缓存    │ │  向量库) │  │          │  │         │
       └───────┘  └─────────┘ └──────────┘  └──────────┘  └─────────┘
           │           │           │               │
           │           ▼           ▼               │
           │     LLM 提供商(6 个):Zhipu/Claude/OpenAI/NVIDIA/Moonshot/OpenRouter
           │
           ▼
      可观测性:OpenTelemetry → OTLP / Prometheus / Sentry
```

### 3.2 请求生命周期(典型 API 调用)

1. **进入** `main.py` FastAPI 应用 → **中间件链**顺序如下:
   `TraceIDMiddleware` → `RequestContextMiddleware` → `TenantMiddleware` → `AuditMiddleware` → `ResourceAuthorizationMiddleware`(RBAC) → `CSRFMiddleware`(变更类方法) → `IdempotencyMiddleware`(适用时) → `RateLimiterMiddleware` → `SecurityHeadersMiddleware` → `PerformanceMiddleware` → `ObservabilityMiddleware` → `ExceptionCaptureMiddleware`。
2. **路由** — 38 个路由之一(`routers/`),每个都注入**依赖**(`dependencies/auth.py` → 当前用户;`dependencies/tenant.py` → 租户作用域;`dependencies/rbac.py` → 权限校验;`dependencies/audit.py`)。
3. **服务** — `services/` 中的业务逻辑(通过 `get_*()` 工厂单例),组合多个服务(如 `AlertService.analyze` 调用 History/Asset/IOC/Impact/ThreatIntel + LLM)。
4. **仓储** — 通过 `repositories/`(如 `alert_repository`、`playbook_run_repository`)基于 SQLAlchemy 异步会话进行数据访问。
5. **模型** — SQLAlchemy ORM(`models/`),通过 `AsyncSessionLocal` 提交到数据库。
6. **响应** — 序列化 Pydantic schema(`schemas/`);可观测性记录 span/metrics;审计日志持久化。

### 3.3 实时告警流(核心流水线)

```
Wazuh ──► /api/alert-stream ──► WazuhStreamService.stream_alert()
   │                                    │
   │                          ┌─────────┴──────────┐
   │                          ▼                    ▼
   │            AlertDeduplicator         AlertAggregator
   │           (指纹 + 24 小时窗口)        (按来源/事件分组)
   │                          │
   │                AlertStormSuppressor(按严重程度的阈值)
   │                          │ 持久化
   │                          ▼
   │                   SecurityAlert(数据库)
   │                          │
   │              ┌───────────┼─────────────┐
   │              ▼           ▼             ▼
   │    AlertService.   AlertEnrichment   AlertLifecycle
   │     analyze()      (OTX 威胁情报,    (状态/备注/时间线)
   │     (LLM + IOC)     24 小时 TTL)        │
   │              │           │                  │
   │              └─────┬─────┘                  │
   │                    ▼                         │
   │           AlertEvaluator(规则 → 通道:Log/Webhook/Email)
   │                    │
   └─── websocket ──► WazuhStreamService 广播 ──► 订阅的客户端
```

### 3.4 剧本 DAG 执行流程

```
触发器(webhook/cron/告警/手动)
  → TriggerService → PlaybookService.load(定义)
  → DAGCompiler.validate(定义)  [失败抛出 DAGValidationError]
  → DAGScheduler.execute(PlaybookDAGEngine):
        对每个就绪节点(依赖已满足):
            ExecutorFactory.get(node.type) → BaseExecutor.execute(context)
                ├─ builtin_extract_iocs / otx_lookup / asset_enrich
                ├─ builtin_decision / risk_score
                ├─ builtin_http_request(SSRF 防护)
                ├─ builtin_human_approval(等待审批放行)
                ├─ builtin_slack_notify / generate_report / timeline_build
                └─ builtin_sleep
            → 持久化 PlaybookNodeRun + PlaybookNodeAttempt
        失败时回滚;中止时取消
  → RunQueueManager(并发上限=3,FIFO/优先级,幂等性缓存)
```

---

## 4. 数据库分析

### 4.1 配置
- **引擎**:异步 SQLAlchemy(`backend/db/session.py`)。`DATABASE_URL` 默认为 `data/app.db` 的 SQLite;当 `DATABASE_URL=postgresql://...` 时使用 PostgreSQL。SQLite 使用 `NullPool`;PostgreSQL 使用连接池(`db_pool_size=20`、`db_max_overflow=40`)。
- **测试隔离**:`ENVIRONMENT=test` → 独立的 `/tmp/soc_copilot_test.db`。
- **Base**:`sqlalchemy.orm.declarative_base`。
- **迁移**:Alembic(`backend/migrations_alembic/`),**20 个版本**。最新:`v1_3_0_marketplace`。其他包括 `v0_8_0_event_correlation`、`v1_1_0_arch_upgrade`、`v1_2_0_phase1_optimizations`、`v0_9_1_security_alerts`。

### 4.2 模型(34 个)按领域分组

| 领域 | 模型 | 说明 |
|--------|--------|-------|
| **认证与 RBAC** | `user`、`rbac`(`roles`)、`api_key`、`tenant_mixin` | `UserRole` 枚举;`TenantMixin` 添加 `tenant_id` 作用域 |
| **告警** | `security_alert`、`alert_note`、`ioc_hit`、`root_cause_analysis` | `SecurityAlert.fingerprint` 用于去重;遗留 `AlertStatus` → `NEW/RESOLVED/false_positive/investigating/escalated` |
| **漏洞** | `security_vulnerability` | 状态 `REPORTED`→…;支持按 severity/status/type/component 过滤 |
| **剧本** | `playbook_definition`、`playbook_run`、`playbook_node_run`、`playbook_node_attempt`、`playbook_output`、`playbook_approval`、`trigger`(`trigger_invocations`) | 完整的 DAG 执行审计追踪 |
| **AI** | `ai_model`、`ai_task`、`ai_user_setting` | `AITaskModel`:PENDING/PROCESSING/COMPLETED/FAILED/TIMEOUT |
| **威胁情报** | `threat_intel_cache`、`ioc_hit` | 威胁情报缓存 TTL(`ti_cache_ttl_hours=168`) |
| **关联 / UEBA** | `correlated_event`、`correlation_rule`、`event_similarity` | 基于 DSL 的关联规则 |
| **市场** | `marketplace`(`marketplace_playbooks`) | 目录:评论、难度、分类 |
| **资产** | `asset` | 用于影响分析的资产清单 |
| **运维** | `audit_log`、`secret`、`monitor_history`、`monitoring_alerts`、`message_filters`、`message_queue`、`websocket_metrics`、`history`、`blocked_ip` | 审计/密钥(管理)/监控/消息/封禁 |

### 4.3 约定
- **主键**:UUID `String(36)`(如 `ai_task.id`);大多数模型遵循字符串 UUID。
- **时间戳**:有生命周期的模型带有 `created_at`/`updated_at`。
- **租户作用域**:`TenantMixin` + `services/tenant_query.with_tenant_scope()` 实现多租户隔离(SQLAlchemy + Redis 键)。
- **模式漂移容忍**:`security_alert_schema.ensure_security_alerts_schema()` 运行时修补 SQLite 开发库缺失的列。
- **软状态**:`alert_lifecycle._normalize_status()` 将遗留状态映射到枚举。

---

## 5. API 分析

### 5.1 路由清单(38 个路由,均位于 `/api` 下)

| 路由 | 前缀/标签 | 用途 |
|--------|-----------|---------|
| `health` | `/health` | 健康检查 + Prometheus 指标 |
| `auth` | `/auth` | 登录/登出/刷新,引导管理员 |
| `users` | `/users` | 用户增删改查 |
| `api_keys` | `/api-keys` | API Key 管理 |
| `audit` | `/audit` | 审计日志查询 + 归档 |
| `alert` | `/alert` | **告警 AI 分析**(核心) |
| `alerts_lifecycle` | `/alerts/lifecycle` | 告警状态/备注/时间线 |
| `alert_enrichment` | `/alerts/enrichment` | 威胁情报富化 |
| `alert_stream` | `/alerts/stream` | Wazuh 告警流接入 |
| `alerts_to_loki` | `/alerts/loki` | 转发到 Loki |
| `security_alerts` | `/security-alerts` | 外部告警接入 |
| `monitoring_alerts` | `/monitoring-alerts` | 告警规则增删改查 |
| `report` | `/report` | LLM 报告生成 |
| `timeline` | `/timeline` | 取证时间线构建 |
| `history` | `/history` | 分析历史 |
| `assets` | `/assets` | 资产清单 |
| `ioc_hits` | `/ioc-hits` | IOC 命中统计 |
| `threat_intel` | `/threat-intel` | OTX 威胁情报查询 |
| `threat_hunting` | `/threat-hunting` | 基于假设的威胁狩猎 |
| `playbook` | `/playbook` | 剧本运行/执行 |
| `playbook_definitions` | `/playbooks/definitions` | 剧本增删改查 |
| `triggers` | `/triggers` | Webhook + Cron 触发器 |
| `webhooks` | `/webhooks` | Webhook 接入 |
| `secrets` | `/secrets` | 加密密钥(Fernet) |
| `admin_settings` | `/admin/settings` | 系统设置 |
| `ai` | `/ai` | AI Copilot 对话 |
| `ai_models` | `/ai-models` | 模型管理 |
| `ai_tasks` | `/ai-tasks` | 后台 AI 任务队列 |
| `ueba` | `/ueba` | UEBA 分析 |
| `marketplace` | `/marketplace` | 剧本市场 |
| `cloud_native` | `/cloud-native` | K8s/容器安全 |
| `monitor` | `/monitor` | 实时监控(SSE) |
| `correlation` | `/correlation` | 事件关联引擎 |
| `blocked_ips` | `/blocked-ips` | IP/域名封禁 |
| `security_vulnerabilities` | `/security-vulnerabilities` | 漏洞跟踪 |
| `notifications` | `/notifications` | 通道 + 队列状态 |
| `export` | `/export` | 数据导出 |
| `system_dashboard` | `/system/dashboard` | 系统健康 |
| `websocket` | `/ws` | WebSocket 实时告警 |
| `websocket_filters` | `/ws/filters` | WS 订阅过滤 |
| `performance` | `/performance` | 性能指标 |

### 5.2 Schema(`backend/schemas/` 中的 24 个)
Pydantic v2 DTO:`ai_model`、`alert`、`alert_analysis`、`alert_lifecycle`、`alert_stream`、`api_key`、`asset`、`audit`、`blocked_ip`、`common`、`events`、`history`、`impact`、`ioc_hit`、`marketplace`、`playbook`、`playbook_dag`、`playbook_run`、`report`、`security_alert`、`threat_intel`、`timeline`、`trigger`、`user`。

### 5.3 认证与安全模型
- **JWT**(`python-jose`),12 小时访问 / 7 天刷新。前端采用**优先 Cookie**策略(`access_token`/`refresh_token` 为 HttpOnly),localStorage 作为降级方案。
- **CSRF**:变更类方法使用 `X-CSRF-Token` 头;`csrf_token` cookie;由 `csrf_middleware`(后端)+ `lib/csrf.ts`(前端)校验。
- **RBAC**:基于角色(`models/rbac.py` `roles`),通过 `dependencies/rbac.py` + `middleware/authorization_middleware.py` 强制执行。
- **API Key**:独立的 `api_keys` 模型/路由用于程序化访问。
- **SSRF 防护**:`core/ssrf_protection.py` + `http_request_executor` 的 URL/主机校验(`is_private_ip`、`resolve_hostname`、`validate_url`)。
- **静态密钥加密**:Fernet(`services/security/secret_service.py`),需要 `SECRET_ENCRYPTION_KEY`。
- **限流**:`middleware/rate_limiter.py`。
- **幂等性**:`middleware/idempotency_middleware.py` + Webhook HMAC(`services/webhook_deduplication.py`)。

### 5.4 超时策略(`core/config.py`)
`api_timeout_analysis_ms=120000` · `default_ms=30000` · `health_ms=5000` · `report_ms=120000` · `timeline_ms=120000` · `dag_run_ms=300000`。

---

## 6. 核心业务分析

### 6.1 服务总览(`backend/services/`)

**37 个顶层服务** + **9 个子包**构成业务核心。通过 `get_*_service()` 工厂实现单例模式;全部为异步。

**核心服务**:`AlertService.analyze()`(`services/alerting/alert_service.py:76`)是集成枢纽 — 编排 IOC 提取、LLM 分析、威胁情报、影响分析和历史持久化。

| 关注点 | 服务 |
|---------|-----------|
| **告警流水线** | `services/alerting/*`(去重、聚合器、风暴抑制、富化、生命周期、评估器、流) |
| **AI / LLM** | `ai_providers.py`(6 个提供商) → `ai_service_enhanced.py`(编排 + RAG) → `llm_retry.py`(容错) → `ai_task_service.py`(数据库支撑的异步队列,max_concurrent=5) |
| **RAG / 向量** | `vector_store.py`(`ChromaDBStore`、`MemoryVectorStore`、工厂) |
| **报告** | `report_service.py`(LLM 驱动的 SOC 报告) |
| **时间线** | `timeline_service.py`(双引擎 IOC 提取) |
| **威胁情报** | `threat_intel_service.py`(OTX,感知内部域名/封禁 TLD) |
| **威胁狩猎** | `threat_hunting_service.py`(基于假设) |
| **UEBA** | `ueba_service.py`(基线、异常检测、风险画像) |
| **事件关联** | `event_correlation_service.py` + `services/correlation/`(DSL `RuleEngine`、窗口聚合、加权评分) |
| **影响分析** | `impact_service.py` + `asset_service.py` |
| **剧本生命周期** | `services/playbook/*`(运行、DAG 编译器/引擎/调度器、上下文、版本管理、导入/导出、回放) |
| **剧本执行器** | `services/playbook_executors/*`(按节点类型) |
| **通知** | `services/notifications/*`(Email、Feishu/飞书、Slack + registry/templates) |
| **市场** | `marketplace_service.py`(`PlaybookMarketplace`) |
| **云原生** | `cloud_native_service.py`(K8s/容器发现) |
| **运行队列** | `run_queue_manager.py`(并发=3、幂等性、FIFO/优先级) |
| **触发器** | `trigger_service.py` + `cron_scheduler_service.py` |
| **Webhook** | `webhook_deduplication.py` + `loki_alert_sender.py` |
| **WebSocket 基础设施** | `websocket_manager.py`、`websocket_connection_pool.py`、`websocket_compression.py`、`message_batch_service.py`、`message_filter.py`、`message_queue.py` |
| **缓存** | `query_cache.py`(`TTLCache`、`cached()` 装饰器) |
| **审计/归档** | `audit_archive_service.py`(`run_scheduled_archival`) |
| **租户隔离** | `tenant_query.py` |
| **事件总线** | `event_bus.py`(基于消息代理的异步发布/订阅) |

### 6.2 消息代理
可插拔 ABC(`services/message_broker/base.py`):`publish/consume/ack/nack/replay_dlq`。**Redis 是唯一在线实现**(Streams + DLQ + 延迟队列)。Kafka 存根存在但未实现。

### 6.3 生命周期管理
所有长运行服务遵循 `core/lifecycle.py` 的 `LifecycleService` 模式;`services/lifecycle/` 包装每一个(ai_task_processor、cron_scheduler、database、queue_manager、rate_limiter、websocket_monitoring)。启动/关闭在 `main.py` 的 lifespan 中接线。

---

## 7. 关键模块

### 7.1 剧本引擎(`backend/playbook_engine/`)

多个版本共存:
- **`dag/`** — 通用 DAG 原语(`engine.py`、`state_machine.py`、`retry_policy.py`、`exceptions.py`)。
- **`v6_linear/`** — 遗留线性流水线引擎(`engine.py`、`models.py`、`registry.py`)。
- **`v7_dag/`** — **当前活动引擎**(基于 DAG)。`base_node.py`、`registry.py` 以及 `plugins/`(15 个内置节点类型)。
- **`triggers/`** — `alert_triggers.py`、`cron.py`、`webhook.py`。
- **`notifications/`** — `http_callback.py`、`slack.py`。
- **`adapter.py`** — 桥接不同引擎版本的外观。

**15 个内置节点插件**(`v7_dag/plugins/`):`action_plan`、`asset_enrich`、`decision`、`extract_iocs`、`generate_report`、`http_request`、`human_approval`、`normalize`、`otx_lookup`、`parse_json`、`risk_score`、`slack_notify`、`sleep`、`timeline_build`。

更高层的编排位于 `services/playbook/`(编译器校验并抛出 `DAGValidationError`;引擎处理节点就绪/回滚;调度器运行并发异步执行 + 取消)。`playbook_executors/` 提供通过 `ExecutorFactory` 选择的按节点类型执行器,全部子类化 `BaseExecutor` 并带有 SSRF 防护。

### 7.2 AI / LLM 子系统

```
ai_providers.LLMFactory.create_from_config()
   → LLMProvider(httpx)— Zhipu/Claude/OpenAI/NVIDIA/Moonshot/OpenRouter
   → EnhancedAIService.generate_structured(prompt, response_class)
        ├─ clean_json_content() + 类型强转 + 重试(max_retries=3)
        └─ RAG 通过 VectorStoreFactory(Chroma / Memory)
   → LLMRetryService 包装器(MAX_RETRIES=2)
        ├─ 结构化路径:schema 校验 → _create_correction_prompt → 重试 → _create_degraded_response 降级
        └─ 自由格式路径:指数退避 → 全部失败时返回 ("", model, degraded=True)
   → AITaskQueueService.submit_task()
        ├─ 数据库行 PENDING → asyncio.Queue
        ├─ _processor_loop(max_concurrent=5) → asyncio.wait_for(timeout)
        ├─ _handle_task_error → TIMEOUT/FAILED;_maybe_retry_task
        └─ 状态:get_task_status / cancel_task
```
**保证**:调用方始终获得有效的类型化对象(降级模式永不抛异常)。

### 7.3 告警流水线
见第 3.3 节。关键类:`WazuhStreamService`、`AlertDeduplicator`(SHA-256 指纹,strict/balanced/relaxed)、`AlertAggregator`、`AlertStormSuppressor`(按严重程度阈值:critical=10/high=20/med=50/low=100/info=200,15 分钟窗口)、`AlertEnrichmentService`(OTX,24 小时 TTL)、`AlertLifecycleService`(时间线合成)、`AlertEvaluator`(规则 → Log/Webhook/Email 通道)。

### 7.4 安全加固
`core/prompt_sanitizer.py`(提示注入防护)、`core/ssrf_protection.py`、`core/sensitive_data.py`、`core/security_validators.py`、`core/token_blacklist.py`、`middleware/security_headers.py`、Fernet 密钥服务、Webhook HMAC 幂等性、租户隔离、RBAC + 资源授权、CSRF、限流、幂等性。

---

## 8. 开发快速上手

### 8.1 环境搭建
```bash
# 1. Python 虚拟环境(后端)
python3.11 -m venv venv && source venv/bin/activate
cd backend && pip install -r requirements.txt

# 2. 前端依赖
cd ../frontend && npm install

# 3. 配置环境变量
cp .env.example .env          # 填写:JWT_SECRET、ZHIPU_API_KEY/ANTHROPIC_API_KEY、
                              #   SECRET_ENCRYPTION_KEY、OTX_API_KEY、REDIS_URL、DATABASE_URL
```

### 8.2 运行(开发)
```bash
# 在仓库根目录 — 并发运行后端(:8000)+ 前端(:3003)
npm run dev

# 或分开运行:
npm run dev:backend    # uvicorn main:app --reload --port 8000
npm run dev:frontend   # next dev -p 3003
```
- 前端将 `/api/*` 代理到 `http://localhost:8000/api/*`(在 `next.config.js` 中)。
- 数据库默认为 `data/app.db`(SQLite)— 设置 `DATABASE_URL=postgresql://...` 切换 Postgres。

### 8.3 数据库
```bash
npm run db:migrate      # alembic upgrade head
npm run db:rollback     # alembic downgrade -1
npm run db:reset        # downgrade base && upgrade head
```

### 8.4 质量门禁
```bash
npm run lint            # 前端:tsc --noEmit + prettier --check | 后端:ruff check .
npm run lint:fix        # 前端:prettier --write | 后端:ruff --fix
npm run format          # 前端:prettier | 后端:black + isort
npm run type-check      # 前端:tsc --noEmit

npm run test            # 前端:vitest | 后端:pytest
npm run test:frontend   # vitest run
npm run test:backend    # pytest
npm run test:coverage   # 两者均带覆盖率

# 端到端(frontend/)
cd frontend && npm run test:e2e        # playwright
cd frontend && npm run test:e2e:ui     # playwright --ui
```

### 8.5 常见任务

**新增 API 端点**(参考 `AGENTS.md`):
1. 在 `backend/models/` 定义 SQLAlchemy 模型
2. 在 `backend/repositories/` 创建仓储
3. 在 `backend/services/` 实现服务(异步,`get_*_service()` 工厂)
4. 在 `backend/schemas/` 创建 Pydantic schema
5. 在 `backend/routers/` 添加路由,并在 `backend/main.py` 注册
6. 生成迁移:`alembic revision --autogenerate -m "..."`
7. 在 `backend/tests/` 添加测试

**新增前端页面**:
1. 创建 `frontend/app/[locale]/<route>/page.tsx`
2. 用 `loadAuthState()` / `isAdmin()` 进行客户端门禁
3. 在 `frontend/lib/api/` 下添加 API 模块(使用 `apiClient`)
4. 在 `frontend/components/<feature>/` 下添加组件
5. 在 `frontend/messages/{en,zh}/<namespace>.json` 添加 i18n 键,并在 `i18n/namespaces.ts` 注册命名空间
6. 使用 `useTranslations('<namespace>')`

**新增剧本节点类型**:
1. 在 `backend/services/playbook_executors/` 创建执行器(子类化 `BaseExecutor`)
2. 在 `ExecutorFactory` 中注册
3. 在 `backend/playbook_engine/v7_dag/plugins/` 创建插件

### 8.6 应遵循的约定
- **Python**:Ruff(lint)+ Black(格式化)+ isort;公共 API 100% 类型注解;异步优先。
- **TypeScript**:严格模式;`@/*` 路径别名;服务端状态优先用 TanStack Query,UI 状态用 Zustand。
- **命名**:后端 `snake_case.py`;前端组件 `PascalCase.tsx`,工具 `camelCase.ts`。
- **Git**:按类型前缀分支(`feat/`、`fix/`、`ui/`、`refactor/`、`perf/`、`a11y/`);使用约定式提交信息。
- **安全**:绝不提交密钥 — 使用 `services/secrets` + Fernet;校验所有输入;应用 RBAC 依赖;剧本中所有出站 HTTP 加 SSRF 防护。

### 8.7 关键入口文件地图

| 我想... | 查看... |
|--------------|-----------|
| 了解应用启动 | `backend/main.py` |
| 修改配置/环境变量 | `backend/core/config.py` + `.env` |
| 新增/修改数据库表 | `backend/models/` + `backend/migrations_alembic/versions/` |
| 新增 API 端点 | `backend/routers/` + `backend/services/` + `backend/schemas/` |
| 修改告警分析 | `backend/services/alerting/alert_service.py:76`(`AlertService.analyze`) |
| 调整 LLM 行为 | `backend/services/ai_service_enhanced.py` + `backend/services/llm_retry.py` + `backend/prompts/` |
| 新增剧本节点 | `backend/services/playbook_executors/` + `backend/playbook_engine/v7_dag/plugins/` |
| 新增通知通道 | `backend/services/notifications/` |
| 前端路由 | `frontend/app/[locale]/` |
| 前端 API 调用 | `frontend/lib/api-client.ts` + `frontend/lib/api/` |
| 前端实时 | `frontend/lib/alertWebSocket.ts` + `frontend/hooks/useMonitor.ts` |
| 国际化 | `frontend/messages/{en,zh}/` + `frontend/i18n/namespaces.ts` |
| 部署 | `docker-compose.prod.yml` + `k8s/` + `.github/workflows/ci-cd.yml` |

---

### 已知技术债务观察(来自分析)
- 前端**双重 API 客户端**(`lib/api-client.ts` 主 vs `lib/api/client.ts` 遗留)— 需合并。
- 前端**双重缓存**(TanStack Query vs `lib/cache.ts`/`useCachedQuery`)— 二选一。
- **认证 store** 是自定义 `useSyncExternalStore`,而非 Zustand(据其自身注释可转换)。
- **`next-themes`** 是依赖但未使用(主题通过自定义 Zustand `themeStore` 实现)。
- **`providers/`** 目录为空 — 真正的 provider 在 `components/providers/`。
- **重复的 i18n 配置**(`i18n.ts` + `i18n/request.ts`)。
- `lib/api/legacy.ts` 中的**遗留兼容垫片**(`api`、`api_v7` …)— 迁移进行中。
- 后端 **`marketplace/`** 目录为空(逻辑在 `services/marketplace_service.py`)。
- **`integration/`** 服务子包是空占位符。
- **Kafka broker** 仅存根,未实现(仅 Redis)。
- **前端路由保护是按页面客户端侧**(无中间件层守卫)。

---

*2026-06-17 基于全代码库扫描生成(阶段 1–8)。*
