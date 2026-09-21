# SOC Copilot - Code Wiki

> **版本**: v0.9.0 | **最后更新**: 2026-05-09 | **许可证**: MIT (内部使用)

---

## 目录

1. [项目概览](#1-项目概览)
2. [整体架构](#2-整体架构)
3. [项目目录结构](#3-项目目录结构)
4. [后端模块详解](#4-后端模块详解)
   - 4.1 [核心层 (core/)](#41-核心层-core)
   - 4.2 [数据模型层 (models/)](#42-数据模型层-models)
   - 4.3 [数据访问层 (repositories/)](#43-数据访问层-repositories)
   - 4.4 [业务服务层 (services/)](#44-业务服务层-services)
   - 4.5 [API路由层 (routers/)](#45-api路由层-routers)
   - 4.6 [请求校验层 (schemas/)](#46-请求校验层-schemas)
   - 4.7 [中间件层 (middleware/)](#47-中间件层-middleware)
   - 4.8 [认证与授权 (dependencies/)](#48-认证与授权-dependencies)
   - 4.9 [Playbook引擎 (playbook_engine/)](#49-playbook引擎-playbook_engine)
   - 4.10 [可观测性 (observability/)](#410-可观测性-observability)
5. [前端模块详解](#5-前端模块详解)
   - 5.1 [技术栈与依赖](#51-技术栈与依赖)
   - 5.2 [路由结构](#52-路由结构)
   - 5.3 [组件体系](#53-组件体系)
   - 5.4 [国际化 (i18n)](#54-国际化-i18n)
   - 5.5 [状态管理](#55-状态管理)
   - 5.6 [API集成](#56-api集成)
6. [基础设施与部署](#6-基础设施与部署)
   - 6.1 [Docker Compose 架构](#61-docker-compose-架构)
   - 6.2 [Nginx 反向代理](#62-nginx-反向代理)
   - 6.3 [Kubernetes 部署](#63-kubernetes-部署)
   - 6.4 [CI/CD 流水线](#64-cicd-流水线)
7. [依赖关系图](#7-依赖关系图)
8. [项目运行方式](#8-项目运行方式)
9. [安全体系](#9-安全体系)
10. [开发规范](#10-开发规范)

---

## 1. 项目概览

**SOC Copilot** 是一个面向安全运营中心 (SOC) 团队的智能分析工作台，提供告警分析、事件时间线重建、报告生成、资产管理、威胁情报查询和 Playbook 自动化编排能力。

### 核心能力

| 能力 | 说明 |
|------|------|
| 告警分析器 | 事件分类 (9种安全事件类型)、严重性评估、双引擎IOC提取 (本地正则+AI)、实体识别、证据提取与修复建议、影响分析面板 |
| 时间线构建器 | 自动事件时间线重建、可疑事件智能排名 (Top 5)、下一步调查建议 |
| 报告生成器 | Ticket模板、日报模板、事后分析模板 |
| 资产管理 | 全生命周期CRUD、批量导入、多维搜索、资产关键性分级 |
| 威胁情报 | AlienVault OTX集成、本地缓存 (7天TTL)、合规过滤 |
| Playbook引擎 | DAG可视化编辑器、节点插件系统、触发器 (Webhook/Cron)、审批流程、密钥管理、执行队列 |

### 技术栈总览

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端语言 | Python | 3.12+ |
| 后端框架 | FastAPI | 0.135.1 |
| ORM | SQLAlchemy (async) | 2.0.47+ |
| 数据库 | SQLite (开发) / PostgreSQL (生产) | - |
| 缓存 | Redis | 7.x |
| 数据验证 | Pydantic | 2.9.2 |
| 前端框架 | Next.js (App Router) | 16.2 |
| UI库 | React | 19.0 |
| 类型系统 | TypeScript | 5.x |
| CSS框架 | Tailwind CSS | 3.4 |
| DAG可视化 | React Flow | 11.11.4 |
| 容器化 | Docker + Docker Compose | - |
| 编排 | Kubernetes (可选) | - |
| 可观测性 | Prometheus + OpenTelemetry | - |

---

## 2. 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户浏览器                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTPS
┌───────────────────────────▼─────────────────────────────────────┐
│                     Nginx 反向代理                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ TLS终止          │  │ 速率限制         │  │ 安全响应头   │  │
│  │ HTTP→HTTPS重定向 │  │ 登录:5次/分钟    │  │ HSTS/CSP/XFO │  │
│  └──────────────────┘  │ API:10次/秒      │  └──────────────┘  │
│                        └──────────────────┘                     │
└──────┬────────────────────────┬────────────────────────────────┘
       │                        │
┌──────▼──────┐          ┌─────▼──────────────────────────────────┐
│  Frontend   │          │           Backend (FastAPI)             │
│  Next.js    │  /api/*  │  ┌──────────────────────────────────┐  │
│  :3003      │─────────▶│  │        中间件链                   │  │
│             │          │  │  TraceID → Tenant → RequestContext │  │
│  ┌────────┐ │          │  │  → Observability → Exception      │  │
│  │ App    │ │          │  │  → SetUserState → Audit           │  │
│  │ Router │ │          │  │  → ResourceAuth → CSRF            │  │
│  └────────┘ │          │  └──────────────────────────────────┘  │
│  ┌────────┐ │          │  ┌──────────────────────────────────┐  │
│  │React   │ │  /ws     │  │        路由层 (Routers)          │  │
│  │Query   │ │◀────────▶│  │  30+ API端点模块                 │  │
│  └────────┘ │  WebSocket│  └──────────────────────────────────┘  │
│  ┌────────┐ │          │  ┌──────────────────────────────────┐  │
│  │Zustand │ │          │  │        服务层 (Services)          │  │
│  │Store   │ │          │  │  AI/Playbook/TI/Asset/...        │  │
│  └────────┘ │          │  └──────────────────────────────────┘  │
└─────────────┘          │  ┌──────────────────────────────────┐  │
                         │  │      Playbook引擎 (DAG)          │  │
                         │  │  拓扑排序 → 并发执行 → 重试策略  │  │
                         │  │  节点插件 → 密钥管理 → 执行队列  │  │
                         │  └──────────────────────────────────┘  │
                         └──────┬──────────────────┬──────────────┘
                                │                  │
                    ┌───────────▼──────┐  ┌────────▼────────┐
                    │   PostgreSQL     │  │     Redis        │
                    │   :5432          │  │     :6379        │
                    │   (数据持久化)   │  │  (缓存/黑名单)   │
                    └──────────────────┘  └─────────────────┘
```

### 数据流

1. **请求入口**: 浏览器 → Nginx (TLS/限流/安全头) → Frontend/Backend
2. **API请求**: Frontend → `/api/*` 代理 → Backend FastAPI → 中间件链 → 路由 → 服务 → 数据库
3. **实时推送**: Backend WebSocket Manager → `/ws` → Frontend 实时告警/通知
4. **AI分析**: 用户提交告警 → AI Service → LLM Provider (智谱/Claude/OpenAI等) → 分析结果
5. **Playbook执行**: 触发器/手动 → DAG引擎 → 拓扑排序 → 并发节点执行 → 结果持久化

---

## 3. 项目目录结构

```
soc-copilot/
├── backend/                         # 后端服务
│   ├── main.py                      # 应用入口 (FastAPI实例、生命周期、中间件注册)
│   ├── core/                        # 核心配置与工具
│   │   ├── config.py                # 全局配置 (Pydantic Settings)
│   │   ├── security.py              # 安全工具 (JWT/密码/API Key)
│   │   ├── logger.py                # 日志配置
│   │   ├── cache.py                 # 缓存工具
│   │   ├── csrf.py                  # CSRF防护
│   │   ├── cookie_auth.py           # Cookie认证
│   │   ├── exceptions.py            # 自定义异常
│   │   ├── http_client.py           # HTTP客户端 (共享连接池)
│   │   ├── lifecycle.py             # 服务生命周期管理
│   │   ├── metrics.py               # Prometheus指标
│   │   ├── response.py              # 统一响应格式
│   │   ├── security_validators.py   # 安全验证器
│   │   ├── sensitive_data.py        # 敏感数据脱敏
│   │   ├── ssrf_protection.py       # SSRF防护
│   │   ├── token_blacklist.py       # JWT令牌黑名单
│   │   ├── validators.py            # 通用输入验证
│   │   └── enums/error_codes.py     # 错误码枚举
│   ├── db/                          # 数据库
│   │   └── session.py               # 会话管理 (SQLite/PostgreSQL双模式)
│   ├── models/                      # SQLAlchemy数据模型 (30+模型)
│   ├── repositories/                # 数据访问层 (Repository模式)
│   ├── schemas/                     # Pydantic请求/响应模型
│   ├── routers/                     # API路由 (30+路由模块)
│   ├── services/                    # 业务逻辑层
│   │   ├── ai_service.py            # AI分析服务
│   │   ├── ai_providers.py          # LLM Provider抽象层
│   │   ├── ai_task_service.py       # AI后台任务
│   │   ├── ai_queue_manager.py      # AI任务队列
│   │   ├── asset_service.py         # 资产管理
│   │   ├── audit_archive_service.py # 审计归档
│   │   ├── event_bus.py             # 事件总线
│   │   ├── threat_intel_service.py  # 威胁情报
│   │   ├── timeline_service.py      # 时间线构建
│   │   ├── report_service.py        # 报告生成
│   │   ├── notification_service.py  # 通知服务
│   │   ├── websocket_manager.py     # WebSocket管理
│   │   ├── run_queue_manager.py     # Playbook执行队列
│   │   ├── message_queue.py         # 消息队列
│   │   ├── vector_store.py          # 向量存储 (ChromaDB)
│   │   ├── ueba_service.py          # UEBA用户行为分析
│   │   ├── impact_service.py        # 影响分析
│   │   ├── ioc_hits_service.py      # IOC命中追踪
│   │   ├── correlation/             # 事件关联引擎
│   │   ├── lifecycle/               # 服务生命周期实现
│   │   ├── notifications/           # 通知渠道 (飞书/Slack/邮件)
│   │   ├── playbook/                # Playbook执行服务
│   │   ├── security/                # 安全服务
│   │   └── user/                    # 用户服务
│   ├── playbook_engine/             # Playbook引擎
│   │   ├── dag/                     # DAG引擎核心
│   │   │   ├── engine.py            # 执行引擎 (拓扑排序+并发)
│   │   │   ├── state_machine.py     # 节点状态机
│   │   │   ├── retry_policy.py      # 重试策略 (指数退避)
│   │   │   └── exceptions.py        # DAG异常定义
│   │   ├── v7_dag/                  # v0.7.4+ 插件系统
│   │   │   ├── base_node.py         # 节点插件基类
│   │   │   ├── registry.py          # 节点注册表
│   │   │   └── plugins/             # 内置插件
│   │   │       ├── builtin_http_request.py
│   │   │       ├── builtin_otx_lookup.py
│   │   │       ├── builtin_decision.py
│   │   │       ├── builtin_slack_notify.py
│   │   │       └── builtin_human_approval.py
│   │   └── triggers/                # 触发器
│   │       └── cron.py              # Cron定时触发器
│   ├── middleware/                   # HTTP中间件
│   ├── dependencies/                 # FastAPI依赖注入
│   ├── observability/                # 可观测性
│   │   ├── tracing.py               # OpenTelemetry追踪
│   │   ├── metrics.py               # Prometheus指标
│   │   ├── logging.py               # 结构化日志
│   │   ├── context.py               # 上下文传播
│   │   └── exporters.py             # 导出器
│   ├── integrations/                 # 外部集成
│   │   └── otx_client.py            # AlienVault OTX客户端
│   ├── utils/                        # 工具函数
│   │   ├── ioc_extract.py           # IOC提取 (正则引擎)
│   │   ├── retry.py                 # 重试工具
│   │   ├── retry_policy.py          # 重试策略
│   │   └── ti_filter.py             # 威胁情报合规过滤
│   ├── prompts/                      # AI提示词模板
│   ├── templates/                    # 报告模板
│   ├── workers/                      # 后台Worker
│   │   └── alert_worker.py          # 告警处理Worker
│   ├── migrations_alembic/           # 数据库迁移
│   ├── scripts/                      # 运维脚本
│   ├── tests/                        # 测试
│   ├── Dockerfile                     # 容器构建
│   ├── pyproject.toml                # Python项目配置
│   ├── requirements.txt              # Python依赖
│   ├── alembic.ini                   # 迁移配置
│   └── ruff.toml                     # Linter配置
│
├── frontend/                         # 前端应用
│   ├── app/                          # Next.js App Router
│   │   └── [locale]/                 # 国际化路由
│   │       ├── layout.tsx            # 根布局
│   │       ├── page.tsx              # 首页 (安全运营概览)
│   │       ├── alerts/               # 告警管理
│   │       ├── assets/               # 资产管理
│   │       ├── audit/                # 审计日志
│   │       ├── login/                # 登录页
│   │       ├── monitor/              # 实时监控
│   │       ├── playbooks/            # Playbook管理
│   │       ├── reports/              # 报告中心
│   │       └── settings/             # 系统设置
│   ├── components/                   # React组件
│   │   ├── common/                   # 通用组件
│   │   │   └── ResponsiveLayout.tsx  # 响应式布局
│   │   ├── ClientLayout.tsx          # 客户端布局
│   │   ├── dag/                      # DAG编辑器组件
│   │   └── playbook/                 # Playbook组件
│   ├── __tests__/                    # 测试
│   ├── Dockerfile                     # 容器构建
│   ├── package.json                  # Node.js依赖
│   ├── tailwind.config.ts            # Tailwind配置
│   └── tsconfig.json                 # TypeScript配置
│
├── nginx/                            # Nginx配置
│   ├── nginx.conf                    # 开发环境配置
│   └── nginx.prod.conf               # 生产环境配置
│
├── k8s/                              # Kubernetes部署
│   ├── 00-namespace.yaml             # 命名空间
│   ├── 00-config.yaml                # 配置
│   ├── 01-postgres.yaml              # PostgreSQL
│   ├── 02-redis.yaml                 # Redis
│   ├── 03-backend.yaml               # 后端
│   ├── 04-frontend.yaml              # 前端
│   ├── 05-ingress.yaml               # Ingress
│   └── 06-hpa.yaml                   # 自动扩缩容
│
├── config/                           # 外部服务配置
│   └── wazuh/ossec.conf              # Wazuh SIEM配置
│
├── security-modules/                 # 安全模块
│   └── log-forwarder/                # 日志转发器
│
├── Scripts/                          # 运维脚本
│   ├── deploy/                       # 部署脚本
│   ├── backup.sh                     # 数据库备份
│   ├── restore.sh                    # 数据库恢复
│   ├── scale-workers.sh              # Worker扩缩容
│   └── setup-feishu.sh              # 飞书集成配置
│
├── messages/                         # i18n翻译文件
│   ├── en.json                       # 英文
│   └── zh.json                       # 中文
│
├── i18n/                             # i18n配置
│   └── request.ts                    # next-intl请求配置
│
├── docs/                             # 项目文档
├── docker-compose.yml                # 开发环境编排
├── docker-compose.prod.yml           # 生产环境编排
├── docker-compose.security.yml       # 安全扫描编排
├── Makefile                          # 构建命令
├── package.json                      # 根级Node.js配置
├── next.config.js                    # Next.js配置
├── tsconfig.json                     # 根级TypeScript配置
├── .env.example                      # 环境变量模板
└── AGENTS.md                         # AI开发代理指南
```

---

## 4. 后端模块详解

### 4.1 核心层 (core/)

核心层提供全局配置、安全工具和基础设施功能，是所有其他模块的基础依赖。

#### `config.py` — 全局配置

| 类/函数 | 说明 |
|---------|------|
| `Settings` | Pydantic Settings类，从环境变量/`.env`文件加载所有配置。包含AI Provider、数据库、JWT、CORS、OTX威胁情报、Playbook队列、Wazuh集成等60+配置项 |
| `get_settings()` | 缓存的配置实例获取 (lru_cache) |
| `get_settings_fresh()` | 清除缓存后重新加载配置 |

**关键配置分组**:

- **AI Provider**: `ai_provider`, `zhipu_api_key`, `anthropic_api_key` 等 — 支持6种LLM Provider
- **数据库**: `db_pool_size`, `db_max_overflow`, `db_pool_recycle` — PostgreSQL连接池
- **安全**: `jwt_secret`, `jwt_expire_minutes`, `secret_encryption_key`, `cors_origins`
- **Playbook**: `run_queue_max`, `run_queue_policy`, `dag_concurrency_max`, `http_allowed_hosts`
- **Wazuh**: `wazuh_enabled`, `wazuh_api_url`, `wazuh_poll_interval`, `wazuh_batch_size`

#### `security.py` — 安全工具

| 函数 | 说明 |
|------|------|
| `verify_password(plain, hashed)` | bcrypt密码验证 |
| `get_password_hash(password)` | bcrypt密码哈希 (开发10轮/生产12轮) |
| `create_access_token(data, expires_delta)` | 创建JWT Access Token (含iat声明) |
| `create_refresh_token(data)` | 创建JWT Refresh Token (7天有效期) |
| `decode_token(token)` | 解码验证JWT令牌 |
| `is_token_invalidated_by_user_update(payload, updated_at)` | 基于用户更新时间的令牌失效检测 (无需黑名单) |
| `hash_api_key(api_key)` | API Key bcrypt哈希 (v2前缀标识) |
| `verify_api_key(plain, hashed)` | API Key验证 (兼容v1 SHA256和v2 bcrypt) |
| `generate_api_key()` | 生成`sk_`前缀的API Key |

#### `lifecycle.py` — 服务生命周期管理

| 类 | 说明 |
|----|------|
| `ServicePriority` | 优先级枚举: CRITICAL(0) → ESSENTIAL(10) → NORMAL(20) → OPTIONAL(30) |
| `LifecycleService` | 抽象基类，定义`start()`/`stop()`/`health_check()`接口 |
| `LifecycleManager` | 生命周期管理器，按优先级+依赖关系排序启动，反向关闭，失败回滚 |
| `ServiceState` | 服务状态数据类 (started/error/started_at/stopped_at) |

**注册的生命周期服务**:

| 优先级 | 服务 | 说明 |
|--------|------|------|
| CRITICAL | DatabaseService | 数据库初始化 |
| ESSENTIAL | QueueManagerService | Playbook执行队列 |
| ESSENTIAL | CronSchedulerServiceWrapper | Cron定时调度器 |
| ESSENTIAL | RateLimiterService | 速率限制器 |
| NORMAL | AITaskProcessorService | AI后台任务处理 |
| NORMAL | WebSocketMonitoringService | WebSocket监控 |
| NORMAL | AlertEvaluatorService | 告警评估器 |
| OPTIONAL | AuditArchiveService | 审计日志归档清理 |

#### 其他核心模块

| 模块 | 说明 |
|------|------|
| `logger.py` | 结构化JSON日志配置 |
| `cache.py` | 缓存工具 (Redis/内存双模式) |
| `csrf.py` | CSRF令牌生成与验证 (Double Submit Cookie) |
| `cookie_auth.py` | Cookie认证支持 |
| `exceptions.py` | 自定义异常层次结构 |
| `http_client.py` | 共享httpx异步HTTP客户端 (连接池复用) |
| `metrics.py` | Prometheus指标注册与收集 |
| `response.py` | 统一API响应格式 |
| `security_validators.py` | 生产环境安全验证 |
| `sensitive_data.py` | 敏感数据脱敏处理 |
| `ssrf_protection.py` | SSRF防护 (私有IP/域名黑名单) |
| `token_blacklist.py` | JWT令牌黑名单 (Redis/内存双模式) |
| `validators.py` | 通用输入验证 (ID格式/SQL注入防护) |
| `enums/error_codes.py` | 标准化错误码枚举 |

---

### 4.2 数据模型层 (models/)

项目采用 SQLAlchemy ORM，共定义 **30+ 数据模型**，支持 SQLite (开发) 和 PostgreSQL (生产) 双模式。

#### 核心模型一览

| 模型 | 表名 | 说明 | 关键字段 |
|------|------|------|----------|
| `UserModel` | users | 用户 | id, username, email, hashed_password, role, is_active, must_change_password |
| `UserRole` | (枚举) | 用户角色 | ADMIN, ANALYST, AUDITOR |
| `APIKeyModel` | api_keys | API密钥 | id, user_id, key_prefix, key_hash, is_active, expires_at, last_used_at |
| `AssetModel` | assets | 资产 | id, hostname, ip_address, owner, business_line, criticality, tags |
| `AuditLogModel` | audit_logs | 审计日志 | id, user_id, action, method, path, status_code, target_type, target_id |
| `SecurityAlert` | security_alerts | 安全告警 | id, title, severity, source, status, raw_data, enriched_data |
| `AlertNoteModel` | alert_notes | 告警备注 | id, alert_id, user_id, content |
| `HistoryModel` | analysis_history | 分析历史 | id, user_id, analysis_type, input_data, result_data |
| `IOCHitModel` | ioc_hits | IOC命中 | id, ioc_type, ioc_value, source_alert_id, threat_intel_data |
| `ThreatIntelCacheModel` | threat_intel_cache | 威胁情报缓存 | id, ioc_type, ioc_value, data, expires_at |

#### Playbook相关模型

| 模型 | 表名 | 说明 |
|------|------|------|
| `PlaybookDefinitionModel` | playbook_definitions | Playbook定义 (含DAG JSON) |
| `PlaybookRunModel` | playbook_runs | Playbook执行记录 |
| `PlaybookRunStepModel` | playbook_run_steps | 执行步骤记录 |
| `PlaybookNodeRunModel` | playbook_node_runs | DAG节点执行记录 |
| `PlaybookNodeAttemptModel` | playbook_node_attempts | 节点重试尝试记录 |
| `PlaybookOutputModel` | playbook_outputs | 节点输出数据 |
| `PlaybookApprovalModel` | playbook_approvals | 人工审批记录 |
| `PlaybookTriggerModel` | playbook_triggers | 触发器配置 |
| `TriggerInvocationModel` | trigger_invocations | 触发器调用记录 |
| `SecretModel` | secrets | 加密密钥存储 (Fernet) |

#### AI与高级分析模型

| 模型 | 表名 | 说明 |
|------|------|------|
| `AIModelModel` | ai_models | AI模型配置 |
| `AIModelCapability` | (枚举) | 模型能力 (分析/嵌入/聊天) |
| `AIProvider` | (枚举) | AI Provider (智谱/Claude/OpenAI/NVIDIA/Moonshot/OpenRouter) |
| `AITaskModel` | ai_tasks | AI后台任务 |
| `AIUserSettingModel` | ai_user_settings | 用户AI偏好设置 |
| `RootCauseAnalysis` | root_cause_analyses | 根因分析记录 |

#### 关联与事件模型

| 模型 | 表名 | 说明 |
|------|------|------|
| `CorrelatedEvent` | correlated_events | 关联事件 |
| `CorrelationRule` | correlation_rules | 关联规则 |
| `EventSimilarity` | event_similarities | 事件相似度 |
| `MonitorHistoryModel` | monitor_history | 监控历史 |
| `MarketplacePlaybookModel` | marketplace_playbooks | Playbook市场 |
| `MarketplaceReviewModel` | marketplace_reviews | 市场评价 |
| `BlockedIP` | blocked_ips | IP/域名封禁 |
| `RBAC` (Role/Permission) | roles, permissions | RBAC权限模型 |

---

### 4.3 数据访问层 (repositories/)

采用 Repository 模式封装数据访问逻辑，隔离 ORM 细节。

| 类 | 说明 |
|----|------|
| `BaseRepository` | 泛型基类，提供CRUD模板方法 |
| `UserRepository` | 用户数据访问 (含密码重置、角色更新) |
| `AssetRepository` | 资产数据访问 (含多维搜索、批量导入) |
| `AuditRepository` | 审计日志数据访问 (含归档清理) |
| `SecretRepository` | 密钥数据访问 (含Fernet加解密) |

---

### 4.4 业务服务层 (services/)

#### AI服务

| 类/模块 | 说明 |
|---------|------|
| `AIService` | AI分析核心服务，协调告警分析、时间线构建、报告生成 |
| `LLMProvider` | LLM Provider抽象基类，定义`chat_completion()`和`embedding()`接口 |
| `ZhipuAIProvider` | 智谱AI实现 (GLM-4) |
| `AnthropicProvider` | Claude实现 |
| `OpenAIProvider` | OpenAI实现 |
| `NVIDIAProvider` | NVIDIA NIM实现 (Llama-3.1-405B) |
| `MoonshotProvider` | Moonshot AI实现 (Kimi) |
| `OpenRouterProvider` | OpenRouter实现 |
| `AITaskService` | AI后台任务管理 (创建/取消/轮询) |
| `AIQueueManager` | AI任务队列管理 (并发控制) |
| `ai_service_enhanced.py` | 增强AI服务 (双引擎IOC提取) |

#### 核心业务服务

| 类/模块 | 说明 |
|---------|------|
| `AssetService` | 资产管理 (CRUD/搜索/批量导入) |
| `TimelineService` | 时间线构建 (事件排序/可疑排名) |
| `ReportService` | 报告生成 (Ticket/日报/事后分析) |
| `ThreatIntelService` | 威胁情报 (OTX查询/本地缓存/合规过滤) |
| `ImpactService` | 影响分析 (风险评分/关联资产) |
| `IOCHitsService` | IOC命中追踪 |
| `HistoryService` | 分析历史管理 |
| `NotificationService` | 通知服务 (飞书/Slack/邮件) |
| `AuditArchiveService` | 审计日志归档与清理 |
| `CloudNativeService` | 云原生安全服务 |
| `UEBAService` | 用户实体行为分析 |
| `MarketplaceService` | Playbook市场服务 |

#### 基础设施服务

| 类/模块 | 说明 |
|---------|------|
| `WebSocketManager` | WebSocket连接管理 (频道订阅/实时推送/心跳检测) |
| `EventBus` | 进程内事件总线 (发布/订阅模式) |
| `RunQueueManager` | Playbook执行队列 (FIFO/优先级/并发控制) |
| `MessageQueue` | 消息队列 (告警分发) |
| `MessageBatchService` | 消息批处理 |
| `MessageFilter` | 消息过滤 |
| `QueryCache` | 查询缓存 |
| `OfflineCache` | 离线缓存 |
| `VectorStore` | 向量存储 (ChromaDB嵌入) |
| `LokiAlertSender` | Grafana Loki告警发送 |
| `WebhookDeduplication` | Webhook去重 |
| `WebSocketCompression` | WebSocket压缩 |
| `LLMRetry` | LLM调用重试策略 |

#### 通知渠道

| 模块 | 说明 |
|------|------|
| `notifications/base.py` | 通知渠道抽象基类 |
| `notifications/feishu.py` | 飞书Webhook通知 |
| `notifications/slack.py` | Slack Webhook通知 |
| `notifications/email.py` | 邮件通知 |

---

### 4.5 API路由层 (routers/)

项目包含 **30+ API路由模块**，所有路由以`/api`为前缀。

#### 核心路由

| 路由模块 | 前缀 | 说明 |
|----------|------|------|
| `auth.py` | `/api/auth` | 认证 (登录/登出/刷新令牌) |
| `users.py` | `/api/users` | 用户管理 (CRUD/角色分配) |
| `api_keys.py` | `/api/api-keys` | API密钥管理 |
| `health.py` | `/api/health` | 健康检查与系统指标 |

#### 安全分析路由

| 路由模块 | 前缀 | 说明 |
|----------|------|------|
| `alert.py` | `/api/analyze-alert` | 告警分析 |
| `timeline.py` | `/api/build-timeline` | 时间线构建 |
| `report.py` | `/api/generate-report` | 报告生成 |
| `alert_enrichment.py` | `/api/alerts/{id}/enrich` | 告警富化 (威胁情报增强) |
| `alerts_lifecycle.py` | `/api/alerts/lifecycle` | 告警生命周期管理 |
| `alert_stream.py` | `/api/alert-stream` | Wazuh告警流管理 |
| `alerts_to_loki.py` | `/api/alerts-to-loki` | 告警转发至Loki |
| `security_alerts.py` | `/api/security-alerts` | 外部安全告警接入 |
| `security_vulnerabilities.py` | `/api/security-vulnerabilities` | 安全漏洞管理 |
| `monitoring_alerts.py` | `/api/monitoring-alerts` | 监控告警规则 |

#### 资产与情报路由

| 路由模块 | 前缀 | 说明 |
|----------|------|------|
| `assets.py` | `/api/assets` | 资产管理 |
| `threat_intel.py` | `/api/threat-intel` | 威胁情报查询 |
| `ioc_hits.py` | `/api/ioc-hits` | IOC命中查询 |
| `blocked_ips.py` | `/api/blocked-ips` | IP/域名封禁管理 |
| `correlation.py` | `/api/correlation` | 事件关联引擎 |
| `threat_hunting.py` | `/api/threat-hunting` | 威胁狩猎 |
| `ueba.py` | `/api/ueba` | UEBA分析 |

#### Playbook路由

| 路由模块 | 前缀 | 说明 |
|----------|------|------|
| `playbook_definitions.py` | `/api/playbook-definitions` | Playbook定义CRUD/执行/发布/导入导出 |
| `playbook.py` | `/api/playbook/runs` | Playbook执行历史/回放 |
| `playbook/approvals.py` | `/api/playbook/approvals` | 审批管理 |
| `playbook/definitions.py` | `/api/playbook/definitions` | 定义版本管理 |
| `playbook/runs.py` | `/api/playbook/runs` | 执行详情 |
| `triggers.py` | `/api/triggers` | 触发器管理 |
| `secrets.py` | `/api/secrets` | 密钥管理 (Fernet加密) |

#### AI与系统路由

| 路由模块 | 前缀 | 说明 |
|----------|------|------|
| `ai.py` | `/api/ai` | AI Copilot对话 |
| `ai_models.py` | `/api/ai-models` | AI模型管理 |
| `ai_tasks.py` | `/api/ai-tasks` | AI后台任务 |
| `audit.py` | `/api/audit` | 审计日志查询 |
| `history.py` | `/api/history` | 分析历史 |
| `webhooks.py` | `/api/webhooks` | Webhook管理 |
| `notifications.py` | `/api/notifications` | 通知渠道/队列状态 |
| `system_dashboard.py` | `/api/system/dashboard` | 系统仪表盘 |
| `performance.py` | `/api/performance` | 性能指标 |
| `admin_settings.py` | `/api/admin/settings` | 管理员设置 |
| `marketplace.py` | `/api/marketplace` | Playbook市场 |
| `cloud_native.py` | `/api/cloud-native` | 云原生安全 |
| `monitor.py` | `/api/monitor` | 实时监控 |
| `export.py` | `/api/export` | 数据导出 |

#### 实时通信路由

| 路由模块 | 前缀 | 说明 |
|----------|------|------|
| `websocket.py` | `/ws` | WebSocket实时告警推送 |
| `websocket_filters.py` | `/api/websocket-filters` | WebSocket过滤器管理 |

---

### 4.6 请求校验层 (schemas/)

基于 Pydantic v2 的请求/响应模型，提供数据验证和序列化。

| Schema模块 | 说明 |
|------------|------|
| `alert.py` | 告警分析请求/响应 |
| `alert_analysis.py` | 告警分析结果 |
| `alert_lifecycle.py` | 告警生命周期操作 |
| `alert_stream.py` | 告警流数据 |
| `user.py` | 用户CRUD/登录/令牌 |
| `asset.py` | 资产CRUD/搜索/导入 |
| `playbook.py` | Playbook定义/创建/更新 |
| `playbook_dag.py` | DAG定义/节点/边 |
| `playbook_run.py` | 执行请求/响应/节点结果 |
| `threat_intel.py` | 威胁情报查询/响应 |
| `audit.py` | 审计日志查询 |
| `api_key.py` | API密钥创建/响应 |
| `ioc_hit.py` | IOC命中数据 |
| `timeline.py` | 时间线构建请求/响应 |
| `report.py` | 报告生成请求/响应 |
| `trigger.py` | 触发器配置 |
| `marketplace.py` | 市场Playbook/评价 |
| `security_alert.py` | 安全告警 |
| `common.py` | 通用分页/排序/响应模型 |
| `events.py` | 事件数据模型 |
| `history.py` | 分析历史 |
| `impact.py` | 影响分析 |
| `blocked_ip.py` | IP封禁 |
| `ai_model.py` | AI模型配置 |

---

### 4.7 中间件层 (middleware/)

中间件按注册顺序执行，形成请求处理管道：

```
请求 → TraceID → Tenant → RequestContext → Observability → ExceptionCapture
     → SetUserState → Audit → ResourceAuthorization → CSRF → 路由处理
```

| 中间件 | 说明 |
|--------|------|
| `TraceIDMiddleware` | 为每个请求生成唯一TraceID，贯穿日志链路 |
| `TenantMiddleware` | 多租户上下文注入 |
| `RequestContextMiddleware` | 请求上下文管理 (IP/UA/方法) |
| `ObservabilityMiddleware` | 可观测性数据收集 (请求耗时/状态码) |
| `ExceptionCaptureMiddleware` | 全局异常捕获与转换 |
| `SetUserStateMiddleware` | 从JWT/API Key解析用户身份注入request.state |
| `AuditMiddleware` | 审计日志记录 (操作/资源/结果) |
| `ResourceAuthorizationMiddleware` | 资源级权限校验 |
| `CSRFMiddleware` | CSRF防护 (Double Submit Cookie) |
| `SecurityHeadersMiddleware` | 安全响应头 (CSP/HSTS/XFO/XCTO) |
| `PerformanceMiddleware` | 慢请求检测与告警 (阈值200ms) |
| `RateLimiterMiddleware` | 速率限制 (登录/API/通用) |
| `EnvValidator` | 启动时环境变量安全验证 |
| `IdempotencyMiddleware` | 幂等性保证 (触发器/Webhook) |

---

### 4.8 认证与授权 (dependencies/)

#### 认证流程

```
请求 → get_current_user_optional()
         ├── 1. 尝试 X-API-Key Header → get_user_by_api_key() → bcrypt验证
         ├── 2. 尝试 Authorization Bearer → decode_token() → 黑名单检查 → 用户更新时间失效检查
         └── 3. 尝试 Cookie → get_token_from_cookie() → 同JWT流程
```

| 依赖函数 | 说明 |
|----------|------|
| `get_current_user_optional()` | 可选认证 (未认证返回None) |
| `get_current_user()` | 必须认证 (未认证返回401) |
| `require_role(*roles)` | 角色检查工厂函数 |
| `require_admin` | 仅管理员 |
| `require_analyst_or_admin` | 分析师或管理员 |
| `require_auditor_or_admin` | 审计员或管理员 |
| `get_api_key_user()` | API Key认证 (必须提供) |
| `require_permission(code)` | 细粒度权限检查 (RBAC) |

#### RBAC权限模型

| 角色 | 权限范围 |
|------|----------|
| **ADMIN** | 全部权限 (用户/密钥/审计/资产/IOC/历史/分析/Playbook/TI) |
| **ANALYST** | 分析操作 + 资产/IOC/历史读写 + Playbook执行 + TI查询 |
| **AUDITOR** | 只读分析 + 审计日志查看 + TI查询 |

---

### 4.9 Playbook引擎 (playbook_engine/)

Playbook引擎是项目最核心的模块之一，实现了基于DAG的工作流编排。

#### 架构层次

```
┌──────────────────────────────────────────────────┐
│                  路由层 (Routers)                  │
│  playbook_definitions / triggers / approvals      │
└───────────────────────┬──────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────┐
│                服务层 (Services)                   │
│  PlaybookRunService / VersionService / Replay     │
└───────────────────────┬──────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────┐
│              DAG引擎 (dag/engine.py)              │
│  ┌─────────────┐  ┌──────────────┐               │
│  │ 拓扑排序    │→ │ 并发执行器   │               │
│  └─────────────┘  └──────┬───────┘               │
│                          │                        │
│  ┌─────────────┐  ┌─────▼────────┐               │
│  │ 状态机      │  │ 重试策略     │               │
│  │ PENDING     │  │ 指数退避     │               │
│  │ RUNNING     │  │ MaxRetries=3 │               │
│  │ SUCCESS     │  └──────────────┘               │
│  │ FAILED      │                                  │
│  │ SKIPPED     │                                  │
│  └─────────────┘                                  │
└───────────────────────┬──────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────┐
│            节点插件系统 (v7_dag/)                  │
│  ┌──────────────────────────────────────────┐    │
│  │ NodeRegistry (自动加载 plugins/ 目录)     │    │
│  └──────────────────────────────────────────┘    │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐     │
│  │HTTPRequest│ │OTXLookup │ │  Decision    │     │
│  └──────────┘ └──────────┘ └──────────────┘     │
│  ┌──────────┐ ┌──────────────┐                   │
│  │SlackNotify│ │HumanApproval│                   │
│  └──────────┘ └──────────────┘                   │
└──────────────────────────────────────────────────┘
```

#### DAG引擎核心类

| 类 | 说明 |
|----|------|
| `DAGNode` | DAG节点定义 (id/name/config/inputs/inputs_template/retry_policy/timeout) |
| `DAGEdge` | DAG边定义 (source/target/condition) |
| `DAGDefinition` | DAG定义 (nodes/edges)，提供依赖解析 |
| `DAGEngine` | 执行引擎，拓扑排序+并发执行+全局超时 |

#### 节点状态机

```
PENDING → RUNNING → SUCCESS
                  → FAILED → (重试) → RUNNING
                           → (超过重试) → FAILED
         → SKIPPED (条件不满足)
```

#### 内置节点插件

| 插件 | 类型 | 说明 |
|------|------|------|
| `builtin_http_request` | Action | HTTP请求 (受沙箱白名单限制) |
| `builtin_otx_lookup` | Process | OTX威胁情报查询 |
| `builtin_decision` | Decision | 条件分支判断 |
| `builtin_slack_notify` | Action | Slack通知发送 |
| `builtin_human_approval` | Control | 人工审批 (暂停等待) |

#### 触发器系统

| 类型 | 说明 |
|------|------|
| Webhook | 外部HTTP触发，支持幂等性 (基于签名去重) |
| Cron | 定时触发，基于croniter表达式解析 |

#### 上下文变量系统

| 变量 | 说明 |
|------|------|
| `{{context.xxx}}` | 全局上下文变量 |
| `{{input.xxx}}` | 运行时输入变量 |
| `{{node.<id>.field}}` | 上游节点输出引用 |
| `{{secret.xxx}}` | 加密密钥引用 (Fernet解密) |

---

### 4.10 可观测性 (observability/)

| 模块 | 说明 |
|------|------|
| `tracing.py` | OpenTelemetry分布式追踪 (OTLP gRPC导出) |
| `metrics.py` | Prometheus指标 (请求计数/延迟/Playbook执行) |
| `logging.py` | 结构化JSON日志 (自动注入TraceID) |
| `context.py` | 上下文传播工具 |
| `exporters.py` | 自定义导出器 |

---

## 5. 前端模块详解

### 5.1 技术栈与依赖

| 类别 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | Next.js | 16.2 | React全栈框架 (App Router) |
| UI库 | React | 19.0 | 用户界面 |
| 类型 | TypeScript | 5.x | 类型安全 |
| 样式 | Tailwind CSS | 3.4 | 原子化CSS |
| 状态管理 | @tanstack/react-query | 5.90 | 服务端状态管理 |
| 主题 | next-themes | 0.4 | 暗色/亮色模式 |
| 国际化 | next-intl | 4.8 | 多语言支持 (中/英) |
| DAG可视化 | reactflow | 11.11 | DAG流程编辑器 |
| 图表 | recharts | 3.7 | 数据可视化 |
| 图标 | lucide-react | 0.577 | 图标库 |
| 虚拟列表 | react-window | 1.8 | 大数据列表渲染 |
| Markdown | react-markdown | 10.1 | Markdown渲染 |
| 错误监控 | @sentry/nextjs | 10.40 | 前端错误追踪 |
| 性能 | web-vitals | 5.1 | Core Web Vitals |
| 工具 | clsx + tailwind-merge | - | 样式合并 |
| CSS变体 | class-variance-authority | 0.7 | 组件样式变体 |

**开发依赖**: Vitest (单元测试) + Playwright (E2E测试) + ESLint + Prettier

### 5.2 路由结构

基于 Next.js App Router 的文件路由，`[locale]` 为国际化动态段：

| 路由路径 | 页面文件 | 说明 |
|----------|----------|------|
| `/` | `page.tsx` | 安全运营概览首页 (统计卡片/动态标签/历史面板) |
| `/alerts` | `alerts/page.tsx` | 告警管理 (列表/筛选/详情) |
| `/assets` | `assets/page.tsx` | 资产管理 (CRUD/搜索/导入) |
| `/audit` | `audit/page.tsx` | 审计日志 (查询/筛选/导出) |
| `/login` | `login/page.tsx` | 用户登录 |
| `/monitor` | `monitor/page.tsx` | 实时监控仪表盘 |
| `/playbooks` | `playbooks/page.tsx` | Playbook管理 (定义/执行/审批) |
| `/reports` | `reports/page.tsx` | 报告中心 |
| `/settings` | `settings/page.tsx` | 系统设置 |

### 5.3 组件体系

| 组件 | 说明 |
|------|------|
| `ClientLayout` | 客户端布局 (主题切换/加载状态/导航) |
| `ResponsiveLayout` | 响应式布局 (移动端/桌面端适配) |
| `DAGCanvas` | DAG画布 (React Flow集成) |
| `DAGNode` | DAG节点渲染 (多种节点类型) |
| `Navigation` | 导航栏 (响应式/国际化) |
| `playbook/*` | Playbook相关组件 (定义列表/执行详情/审批) |

### 5.4 国际化 (i18n)

- **框架**: next-intl (基于ICU消息格式)
- **配置**: `i18n/request.ts` — 请求级locale检测
- **翻译文件**: `messages/en.json` (英文) + `messages/zh.json` (中文)
- **路由**: `[locale]` 动态段自动切换语言
- **工具脚本**: `Scripts/` 下提供翻译同步检查、缺失翻译检测、类型生成等工具

### 5.5 状态管理

| 方案 | 用途 |
|------|------|
| **React Query** (`@tanstack/react-query`) | 服务端状态管理 (API数据获取/缓存/同步) |
| **Zustand** (隐含) | 客户端全局状态 (UI状态/用户偏好) |
| **React State** | 组件本地状态 |

### 5.6 API集成

- **代理模式**: Next.js rewrites 将 `/api/*` 代理至 `http://localhost:8000/api/*`
- **WebSocket**: 直连 `ws://localhost:8000/ws` 实现实时告警推送
- **认证**: JWT Bearer Token + Cookie 双模式
- **CSRF**: Double Submit Cookie 模式

---

## 6. 基础设施与部署

### 6.1 Docker Compose 架构

#### 开发环境 (`docker-compose.yml`)

| 服务 | 镜像 | 端口 | 网络 | 资源限制 |
|------|------|------|------|----------|
| postgres | postgres:15-alpine | 127.0.0.1:5432 | database-net (internal) | 2CPU/2G |
| redis | redis:7-alpine | 127.0.0.1:6379 | backend-net (internal) | 1CPU/512M |
| backend | 自建 | 8000 (内部) | backend-net + database-net | 2CPU/2G |
| frontend | 自建 | 3000 (内部) | frontend-net | 1CPU/1G |
| nginx | nginx:1.26-alpine | 80:80, 443:443 | frontend-net | 0.5CPU/256M |

**网络隔离**: 三层网络架构
- `frontend-net`: 前端→Nginx通信
- `backend-net` (internal): 后端→Redis通信，禁止外部访问
- `database-net` (internal): 后端→PostgreSQL通信，禁止外部访问

**安全措施**:
- PostgreSQL/Redis 仅绑定 127.0.0.1
- `DB_PASSWORD` 和 `SECRET_KEY` 为必须环境变量 (缺失则启动失败)
- 所有容器设置 CPU/内存限制

#### 生产环境 (`docker-compose.prod.yml`)

- Nginx启用 (profiles: production)
- TLS 1.2/1.3 强制
- HSTS 预加载
- 更严格的速率限制

### 6.2 Nginx 反向代理

| 配置项 | 值 | 说明 |
|--------|-----|------|
| TLS协议 | TLSv1.2 TLSv1.3 | 禁用旧协议 |
| HSTS | max-age=63072000; includeSubDomains; preload | 强制HTTPS |
| 登录限流 | 5次/分钟 | 防暴力破解 |
| API限流 | 10次/秒 | 防滥用 |
| 通用限流 | 30次/秒 | 基础保护 |
| WebSocket | /ws 路径，3600s超时 | 实时通信 |
| 安全头 | CSP/XFO/XCTO/XSS/Referrer/Permissions | 全量安全头 |
| 敏感路径 | .env/.git/.htaccess → 404 | 信息泄露防护 |

### 6.3 Kubernetes 部署

| 清单文件 | 资源 | 说明 |
|----------|------|------|
| `00-namespace.yaml` | Namespace | soc-copilot命名空间 |
| `00-config.yaml` | ConfigMap/Secret | 环境配置与密钥 |
| `01-postgres.yaml` | StatefulSet/Service | PostgreSQL持久化存储 |
| `02-redis.yaml` | Deployment/Service | Redis缓存 |
| `03-backend.yaml` | Deployment/Service | 后端API (多副本) |
| `04-frontend.yaml` | Deployment/Service | 前端应用 |
| `05-ingress.yaml` | Ingress | TLS终止与路由 |
| `06-hpa.yaml` | HorizontalPodAutoscaler | 自动扩缩容 |

### 6.4 CI/CD 流水线

| 工作流 | 文件 | 触发条件 | 说明 |
|--------|------|----------|------|
| CI/CD | `.github/workflows/ci-cd.yml` | Push/PR | 代码检查+测试+构建 |
| Pre-commit | `.github/workflows/pre-commit.yml` | Push | Gitleaks/Bandit/硬编码密码检测 |
| Security | `.github/workflows/security.yml` | 定时+Push | 依赖漏洞/密钥泄露/SAST/Docker扫描 |

---

## 7. 依赖关系图

### 后端模块依赖

```
main.py
  ├── core/ (配置/安全/日志/生命周期)
  ├── db/session.py ← core/config
  ├── middleware/ ← core/logger, core/config
  ├── dependencies/ ← core/security, models/, db/
  ├── routers/ ← dependencies/, services/, schemas/
  ├── services/ ← models/, repositories/, core/
  │   ├── ai_service.py ← ai_providers.py, core/http_client
  │   ├── playbook/ ← playbook_engine/dag/
  │   ├── notifications/ ← core/http_client
  │   └── lifecycle/ ← db/, services/
  ├── playbook_engine/
  │   ├── dag/engine.py ← dag/state_machine, dag/retry_policy
  │   └── v7_dag/registry.py ← v7_dag/plugins/*
  ├── repositories/ ← models/, db/
  ├── schemas/ ← models/ (类型映射)
  ├── observability/ ← core/config
  └── integrations/ ← core/http_client, core/config
```

### 前端模块依赖

```
app/[locale]/layout.tsx
  ├── next-intl (i18n)
  ├── next-themes (主题)
  └── components/ClientLayout
        ├── components/common/ResponsiveLayout
        ├── @tanstack/react-query (数据获取)
        └── Navigation

app/[locale]/page.tsx
  ├── @tanstack/react-query (useQuery)
  ├── recharts (图表)
  ├── lucide-react (图标)
  └── react-window (虚拟列表)

app/[locale]/playbooks/page.tsx
  ├── reactflow (DAG编辑器)
  ├── components/dag/DAGCanvas
  └── components/dag/DAGNode
```

### 外部服务依赖

```
SOC Copilot
  ├── AI Providers
  │   ├── 智谱AI (GLM-4)
  │   ├── Anthropic (Claude)
  │   ├── OpenAI (GPT)
  │   ├── NVIDIA NIM (Llama)
  │   ├── Moonshot (Kimi)
  │   └── OpenRouter
  ├── AlienVault OTX (威胁情报)
  ├── 飞书 (通知)
  ├── Slack (通知)
  ├── Wazuh SIEM (日志接入)
  ├── Grafana Loki (日志存储)
  └── Prometheus (指标收集)
```

---

## 8. 项目运行方式

### 本地开发 (推荐)

```bash
# 1. 克隆项目
git clone <repo-url> && cd soc-copilot

# 2. 后端设置
cd backend
python -m venv venv
source venv/bin/activate      # Linux/Mac
pip install -r requirements.txt

# 3. 前端设置
cd ../frontend
npm install

# 4. 配置环境变量
cp ../.env.example ../.env
# 编辑 .env 填入必要的 API Key 和密码

# 5. 启动开发服务器 (方式一: Makefile)
make dev

# 6. 启动开发服务器 (方式二: npm)
npm run dev

# 7. 启动开发服务器 (方式三: 分别启动)
cd backend && source ../venv/bin/activate && uvicorn main:app --reload --port 8000
cd frontend && npm run dev   # 端口 3003
```

### Docker Compose

```bash
# 开发环境
docker-compose up -d

# 生产环境 (含Nginx)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 安全扫描环境
docker-compose -f docker-compose.security.yml up -d
```

### Kubernetes

```bash
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/00-config.yaml
kubectl apply -f k8s/01-postgres.yaml
kubectl apply -f k8s/02-redis.yaml
kubectl apply -f k8s/03-backend.yaml
kubectl apply -f k8s/04-frontend.yaml
kubectl apply -f k8s/05-ingress.yaml
kubectl apply -f k8s/06-hpa.yaml
```

### 常用命令

| 命令 | 说明 |
|------|------|
| `make dev` | 启动前后端开发服务器 |
| `make test` | 运行所有测试 |
| `make lint` | 代码检查 |
| `make format` | 代码格式化 |
| `make db-migrate` | 运行数据库迁移 |
| `make db-rollback` | 回滚上次迁移 |
| `make docker-up` | 启动Docker容器 |
| `make docker-reset` | 重置Docker容器 |

### 访问地址

| 服务 | URL | 默认凭据 |
|------|-----|----------|
| 前端 | http://localhost:3003 | admin / (自动生成，见控制台) |
| 后端API | http://localhost:8000 | - |
| API文档 | http://localhost:8000/docs | - |
| 数据库 | `data/app.db` (SQLite自动创建) | - |

---

## 9. 安全体系

### 认证安全

| 措施 | 说明 |
|------|------|
| JWT双令牌 | Access Token (12h) + Refresh Token (7天) |
| 令牌失效 | 基于用户更新时间自动失效 (无需黑名单) |
| 令牌黑名单 | Redis/内存双模式，登出时主动失效 |
| API Key | bcrypt哈希存储，前缀快速查找，速率限制防枚举 |
| 密码策略 | bcrypt哈希 (生产12轮)，5次失败锁定30分钟，密码历史检查 |
| CSRF防护 | Double Submit Cookie模式 |
| 首次登录 | 强制修改密码 (must_change_password) |

### 网络安全

| 措施 | 说明 |
|------|------|
| 网络隔离 | 三层Docker网络 (frontend/backend/database) |
| 端口绑定 | 数据库/Redis仅绑定127.0.0.1 |
| CORS | 生产环境强制白名单，禁止通配符 |
| TLS | 1.2/1.3强制，HSTS预加载 |
| 速率限制 | 登录5次/分钟，API 10次/秒 |
| SSRF防护 | HTTP沙箱白名单，禁止私有IP/localhost |

### 数据安全

| 措施 | 说明 |
|------|------|
| 密钥管理 | Fernet加密存储，`{{secret.xxx}}`安全引用 |
| 敏感数据脱敏 | 日志中自动脱敏密码/Token |
| SQL注入防护 | Pydantic验证 + SQLAlchemy参数化查询 |
| 输入验证 | ID格式验证 + SQL输入过滤 |
| 审计日志 | 全操作审计，90天保留，自动归档 |

### Playbook安全

| 措施 | 说明 |
|------|------|
| dry_run默认 | 默认模拟执行，apply需显式授权 |
| 人工审批 | 关键操作暂停等待审批 |
| 执行日志 | 步骤级审计追踪 |
| HTTP沙箱 | 主机名白名单限制 |
| 幂等性 | Webhook触发器去重 |

---

## 10. 开发规范

### 代码质量

| 维度 | 后端 (Python) | 前端 (TypeScript) |
|------|---------------|-------------------|
| Linter | Ruff (pyproject.toml) | ESLint + Prettier |
| 格式化 | Black + isort | Prettier |
| 类型检查 | mypy --strict (公共API) | tsc --noEmit |
| 测试框架 | pytest + pytest-asyncio | Vitest + Playwright |
| 覆盖率目标 | ≥ 60% | - |
| 类型注解 | 100% (公共API) | ≥ 80% |

### 测试标记 (pytest markers)

| 标记 | 说明 |
|------|------|
| `@pytest.mark.unit` | 单元测试 (快速/隔离) |
| `@pytest.mark.integration` | 集成测试 (可能使用外部服务) |
| `@pytest.mark.e2e` | 端到端测试 (完整系统) |
| `@pytest.mark.auth` | 认证授权测试 |
| `@pytest.mark.ai` | AI服务测试 |
| `@pytest.mark.playbook` | Playbook引擎测试 |
| `@pytest.mark.redis` | 需要Redis的测试 |
| `@pytest.mark.database` | 需要数据库的测试 |

### Git规范

- Pre-commit hooks: Gitleaks (密钥检测) + Bandit (安全扫描) + 硬编码密码检测
- Dependabot: 自动依赖更新
- CODEOWNERS: 代码所有者审查

### 新功能开发流程

1. 在 `backend/models/` 定义数据模型
2. 在 `backend/schemas/` 定义请求/响应模型
3. 在 `backend/repositories/` 创建数据访问层
4. 在 `backend/services/` 实现业务逻辑
5. 在 `backend/routers/` 创建API路由
6. 添加测试用例
7. 更新API文档 (自动生成OpenAPI)
8. 前端对应页面和组件开发
9. 添加i18n翻译 (en.json + zh.json)
