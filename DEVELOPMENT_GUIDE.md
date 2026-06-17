# SOC Copilot — Development Guide

> Auto-generated from full codebase analysis. Living document — update when architecture changes.
> Project: **SOC Copilot** v0.8.2 · A Security Operations Center platform with AI-assisted alert triage, DAG-based automation playbooks, threat intelligence enrichment, and Wazuh integration.

---

## Table of Contents
1. [Project Scan (Overview)](#1-project-scan-overview)
2. [Code Map](#2-code-map)
3. [Architecture](#3-architecture)
4. [Database Analysis](#4-database-analysis)
5. [API Analysis](#5-api-analysis)
6. [Core Business Analysis](#6-core-business-analysis)
7. [Key Modules](#7-key-modules)
8. [Development Quickstart](#8-development-quickstart)

---

## 1. Project Scan (Overview)

**What it is:** A full-stack SOC platform that ingests security alerts (primarily from Wazuh), uses LLMs to analyze/triage them, enriches with threat intel (OTX, AbuseIPDB), correlates events, runs automated response playbooks (DAG engine), and streams results to a real-time dashboard.

**Who it serves:** Security analysts doing alert triage, threat hunting, incident response, and compliance reporting.

### Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Backend language** | Python | 3.11+ (async) |
| **Backend framework** | FastAPI | 0.135.1 |
| **ORM** | SQLAlchemy (async) | 2.0+ |
| **DB (dev)** | SQLite + aiosqlite | - |
| **DB (prod)** | PostgreSQL (via `DATABASE_URL`) | - |
| **Cache/Queue/Broker** | Redis | 7.2.1 |
| **Vector store (RAG)** | ChromaDB | 1.5.2 |
| **ML** | scikit-learn | 1.4.0 (UEBA / correlation) |
| **Migrations** | Alembic | 1.14.0 |
| **Frontend language** | TypeScript | 5 (strict) |
| **Frontend framework** | Next.js (App Router) | 16.2.3 |
| **UI runtime** | React | 19 |
| **Styling** | Tailwind CSS | 3.4 |
| **Data fetching** | TanStack Query | 5.90 |
| **i18n** | next-intl | 4.8 |
| **State** | Zustand + custom `useSyncExternalStore` | - |
| **Graph viz** | ReactFlow | 11.11 |
| **Charts** | Recharts | 3.7 |
| **Test (FE)** | Vitest + Playwright | 4 / 1.40 |
| **Test (BE)** | pytest (+ cov) | - |
| **Lint/Format** | Ruff + Black + isort (BE); ESLint + Prettier (FE) | - |
| **Observability** | OpenTelemetry + Prometheus + Sentry | - |
| **Deploy** | Docker / docker-compose / Kubernetes (`k8s/`) | - |
| **CI/CD** | GitHub Actions (`.github/workflows/`: ci-cd, security, pre-commit) | - |

### LLM Providers (6, via `LLMFactory`)
`zhipu` (GLM-4, **default**) · `claude` (Anthropic) · `openai` · `nvidia` (Llama-3.1-405b) · `moonshot` (Kimi) · `openrouter`. All are remote HTTP APIs via a shared `httpx.AsyncClient`.

---

## 2. Code Map

### Top-level layout

```
sec/
├── backend/                  # FastAPI API server (Python)
├── frontend/                 # Next.js App Router SPA (TypeScript)
├── ai-assistant-release/     # Standalone embeddable AI assistant widget
├── k8s/                      # Kubernetes manifests
├── nginx/                    # Reverse-proxy config
├── docker-compose*.yml       # base + prod + security + override
├── docs/                     # Project documentation (50+ files)
├── scripts/ , Lib/           # Misc helper scripts
├── AGENTS.md                 # Agent/contributor guide (per-role workflows)
├── README.md                 # Main project README
└── package.json              # Root workspace (npm workspaces: frontend)
```

### Backend map (`backend/`)

| Dir | Purpose | Key files |
|-----|---------|-----------|
| `main.py` | **App entry** — FastAPI app, 36 routers, 14 middleware, lifespan | — |
| `core/` | Cross-cutting infra: config, security, logging, http_client, cache, **lifecycle**, **prompt_sanitizer**, csrf, ssrf_protection, token_blacklist, metrics, response, validators, sensitive_data, security_validators | `config.py`, `lifecycle.py` |
| `core/enums/` | Shared enumerations (`error_codes`) | — |
| `config/` | Static config (elasticsearch, wazuh) | — |
| `db/` | Async SQLAlchemy engine + `AsyncSessionLocal` + `Base`; SQLite/PostgreSQL switch | `session.py` |
| `models/` | **34 SQLAlchemy models** (see §4) | — |
| `schemas/` | Pydantic request/response DTOs (24 files) | — |
| `routers/` | **38 FastAPI routers** (see §5) | — |
| `services/` | Business logic — 37 top-level files + 9 subpackages (see §6) | — |
| `repositories/` | Data-access layer wrapping models (17 repos + `base.py`) | — |
| `middleware/` | 14 middleware (audit, authz, csrf, idempotency, observability, performance, rate_limiter, request_context, security_headers, tenant, trace, exception) | — |
| `dependencies/` | FastAPI dependency providers (auth, rbac, tenant, audit, authorization) | — |
| `playbook_engine/` | DAG automation engine — `dag/`, `v6_linear/`, `v7_dag/`, `triggers/`, `notifications/`, `adapter.py` (see §7) | — |
| `playbook_engine/v7_dag/plugins/` | **15 builtin DAG node plugins** (action_plan, asset_enrich, decision, extract_iocs, generate_report, http_request, human_approval, normalize, otx_lookup, parse_json, risk_score, slack_notify, sleep, timeline_build) | — |
| `integrations/` | External clients — `otx_client` (AlienVault OTX) | — |
| `marketplace/` | (Currently empty — playbook marketplace lives in `services/marketplace_service.py`) | — |
| `workers/` | Background workers — `alert_worker` | — |
| `scripts/` | Ops scripts — `archive_old_data`, `unlock_user` | — |
| `migrations_alembic/versions/` | **20 Alembic migrations** (latest: `v1_3_0_marketplace`) | — |
| `tests/` | pytest suite + `conftest.py` | — |
| `prompts/`, `templates/` | LLM prompt templates, report templates | — |
| `observability/` | Tracing + JSON logging setup | `tracing.py`, `logging.py` |

### Frontend map (`frontend/`)

| Dir | Purpose |
|-----|---------|
| `app/[locale]/` | **All pages** under locale segment (`en`/`zh`) — see §2.1 |
| `app/api/` | Next.js API route shims |
| `components/` | UI components in 13 subdirs (`alert`, `alerts`, `chat`, `common`, `dag`, `impact`, `monitor`, `playbook`, `providers`, `tabs`, `threat_intel`, `websocket`) + top-level (`Navigation`, `ClientLayout`, `ChatHistorySidebar`, `GlobalSearch`, `Toast`, `WebVitals`, `AlertWebSocket`) |
| `components/common/` | Shared primitives (Button, Card, Input, Skeleton family, VirtualList, ErrorBoundary, ResponsiveLayout, SkipToContent) |
| `stores/` | `authStore` (custom), `notificationStore`, `themeStore` (Zustand+persist) |
| `hooks/` | `useMonitor` (SSE+polling), `useCachedQuery`, `usePlaybooks`, `usePermission`, `useChatHistory`, `useAutoSave`, `useKeyboardShortcuts` |
| `lib/` | `api-client.ts` (primary), `api/client.ts` (legacy), domain modules `lib/api/*` (alerts, ai, assets, history, ioc, triggers, secrets, playbooks, auth), `auth.ts`, `csrf.ts`, `queryClient.ts`, `cache.ts`, `sentry.ts`, `monitor.ts` |
| `lib/api/` | Domain API modules + `legacy.ts` compat shim (`api`, `api_v7`, `api_v73`, `api_v74`) |
| `i18n/` + `messages/` | next-intl routing (`en`/`zh`, prefix: always); 25 split namespaces + monolithic `en.json`/`zh.json` |
| `types/` | TypeScript domain types (incl. `wazuh`) |
| `providers/` | **Empty** (legacy) — real providers in `components/providers/QueryProvider.tsx` |
| `e2e/` | Playwright suites (admin, ai, alerts, auth, dashboard, i18n, marketplace, playbooks, reports, security, threat-intel) |

#### 2.1 Frontend Routes (under `/[locale]/`)
Home(`/`) · login · alerts · alerts/[id] · playbooks · playbooks/definitions · playbooks/approvals · ai-assistant · threat-intel · threat-intel/dashboard · threat-hunting · monitor · marketplace · assets · reports · audit · correlation · cloud-native · ueba · triggers · triggers/webhook/new · triggers/cron/new · settings · settings/notifications · settings/api-keys · settings/ai-models · admin/{dashboard,users,settings,secrets,audit,health} · test

---

## 3. Architecture

### 3.1 High-level diagram

```
        ┌─────────────────────────────────────────────────────────────┐
        │                        CLIENT (Browser)                      │
        │  Next.js 16 / React 19 / TanStack Query / Zustand / WS+SSE   │
        └───────────────┬───────────────────────────┬──────────────────┘
                        │ HTTPS (/api → :8000 proxy)│ WebSocket / SSE
                        ▼                            ▼
        ┌─────────────────────────────────────────────────────────────┐
        │                     FastAPI APP (main.py)                    │
        │  14 middleware: trace → request_context → tenant → audit →   │
        │    authz → rbac → csrf → idempotency → rate_limit →          │
        │    security_headers → performance → observability →          │
        │    exception_handler                                          │
        │  38 routers → services → repositories → models → DB          │
        └──┬───────────┬───────────┬───────────────┬────────────┬──────┘
           │           │           │               │            │
           ▼           ▼           ▼               ▼            ▼
       ┌───────┐  ┌─────────┐ ┌──────────┐  ┌──────────┐  ┌─────────┐
       │SQLite/│  │ Redis   │ │ ChromaDB │  │ OTX/TI   │  │ Wazuh   │
       │Postgres│ │ broker/ │ │ (RAG     │  │ feeds    │  │ (alerts)│
       │       │  │ cache   │ │  vector) │  │          │  │         │
       └───────┘  └─────────┘ └──────────┘  └──────────┘  └─────────┘
           │           │           │               │
           │           ▼           ▼               │
           │     LLM Providers (6): Zhipu/Claude/OpenAI/NVIDIA/Moonshot/OpenRouter
           │
           ▼
      Observability: OpenTelemetry → OTLP / Prometheus / Sentry
```

### 3.2 Request lifecycle (typical API call)

1. **Enter** `main.py` FastAPI app → **middleware chain** in order:
   `TraceIDMiddleware` → `RequestContextMiddleware` → `TenantMiddleware` → `AuditMiddleware` → `ResourceAuthorizationMiddleware` (RBAC) → `CSRFMiddleware` (mutating methods) → `IdempotencyMiddleware` (where applicable) → `RateLimiterMiddleware` → `SecurityHeadersMiddleware` → `PerformanceMiddleware` → `ObservabilityMiddleware` → `ExceptionCaptureMiddleware`.
2. **Route** — one of 38 routers (`routers/`), each injecting **dependencies** (`dependencies/auth.py` → current user; `dependencies/tenant.py` → tenant scope; `dependencies/rbac.py` → permission check; `dependencies/audit.py`).
3. **Service** — business logic in `services/` (singleton via `get_*()` factories), composes multiple services (e.g. `AlertService.analyze` calls History/Asset/IOC/Impact/ThreatIntel + LLM).
4. **Repository** — data access via `repositories/` (e.g. `alert_repository`, `playbook_run_repository`) over SQLAlchemy async session.
5. **Model** — SQLAlchemy ORM (`models/`), committed to DB via `AsyncSessionLocal`.
6. **Response** — Pydantic schema (`schemas/`) serialized; observability records span/metrics; audit log persists.

### 3.3 Real-time alert flow (the core pipeline)

```
Wazuh ──► /api/alert-stream ──► WazuhStreamService.stream_alert()
   │                                    │
   │                          ┌─────────┴──────────┐
   │                          ▼                    ▼
   │            AlertDeduplicator         AlertAggregator
   │           (fingerprint + 24h window) (group by src/event)
   │                          │
   │                AlertStormSuppressor (severity thresholds)
   │                          │ persist
   │                          ▼
   │                   SecurityAlert (DB)
   │                          │
   │              ┌───────────┼─────────────┐
   │              ▼           ▼             ▼
   │    AlertService.   AlertEnrichment   AlertLifecycle
   │     analyze()      (OTX TI, 24h TTL) (status/notes/timeline)
   │     (LLM + IOC)         │                  │
   │              │           │                  │
   │              └─────┬─────┘                  │
   │                    ▼                         │
   │           AlertEvaluator (rules → channels: Log/Webhook/Email)
   │                    │
   └─── websocket ──► WazuhStreamService broadcast ──► subscribed clients
```

### 3.4 Playbook DAG execution flow

```
Trigger (webhook/cron/alert/manual)
  → TriggerService → PlaybookService.load(definition)
  → DAGCompiler.validate(definition)  [raises DAGValidationError]
  → DAGScheduler.execute(PlaybookDAGEngine):
        for each ready node (dependencies satisfied):
            ExecutorFactory.get(node.type) → BaseExecutor.execute(context)
                ├─ builtin_extract_iocs / otx_lookup / asset_enrich
                ├─ builtin_decision / risk_score
                ├─ builtin_http_request (SSRF-guarded)
                ├─ builtin_human_approval (gates until approval)
                ├─ builtin_slack_notify / generate_report / timeline_build
                └─ builtin_sleep
            → persist PlaybookNodeRun + PlaybookNodeAttempt
        rollback on failure; cancel on abort
  → RunQueueManager (concurrency cap=3, FIFO/priority, idempotency cache)
```

---

## 4. Database Analysis

### 4.1 Setup
- **Engine**: async SQLAlchemy (`backend/db/session.py`). `DATABASE_URL` defaults to SQLite at `data/app.db`; PostgreSQL when `DATABASE_URL=postgresql://...`. SQLite uses `NullPool`; PostgreSQL uses pool (`db_pool_size=20`, `db_max_overflow=40`).
- **Test isolation**: `ENVIRONMENT=test` → separate `/tmp/soc_copilot_test.db`.
- **Base**: `sqlalchemy.orm.declarative_base`.
- **Migrations**: Alembic (`backend/migrations_alembic/`), **20 versions**. Latest: `v1_3_0_marketplace`. Others include `v0_8_0_event_correlation`, `v1_1_0_arch_upgrade`, `v1_2_0_phase1_optimizations`, `v0_9_1_security_alerts`.

### 4.2 Models (34) grouped by domain

| Domain | Models | Notes |
|--------|--------|-------|
| **Auth & RBAC** | `user`, `rbac` (`roles`), `api_key`, `tenant_mixin` | `UserRole` enum; `TenantMixin` adds `tenant_id` scoping |
| **Alerts** | `security_alert`, `alert_note`, `ioc_hit`, `root_cause_analysis` | `SecurityAlert.fingerprint` for dedup; legacy `AlertStatus` → `NEW/RESOLVED/false_positive/investigating/escalated` |
| **Vulnerabilities** | `security_vulnerability` | status `REPORTED`→…; severity/status/type/component filters |
| **Playbooks** | `playbook_definition`, `playbook_run`, `playbook_node_run`, `playbook_node_attempt`, `playbook_output`, `playbook_approval`, `trigger` (`trigger_invocations`) | Full DAG execution audit trail |
| **AI** | `ai_model`, `ai_task`, `ai_user_setting` | `AITaskModel`: PENDING/PROCESSING/COMPLETED/FAILED/TIMEOUT |
| **Threat Intel** | `threat_intel_cache`, `ioc_hit` | TI cache TTL (`ti_cache_ttl_hours=168`) |
| **Correlation / UEBA** | `correlated_event`, `correlation_rule`, `event_similarity` | DSL-based correlation rules |
| **Marketplace** | `marketplace` (`marketplace_playbooks`) | Catalog: reviews, difficulty, categories |
| **Assets** | `asset` | Asset inventory for impact analysis |
| **Operations** | `audit_log`, `secret`, `monitor_history`, `monitoring_alerts`, `message_filters`, `message_queue`, `websocket_metrics`, `history`, `blocked_ip` | Audit/secret(mgmt)/monitoring/messaging/blocking |

### 4.3 Conventions
- **Primary keys**: UUID `String(36)` (e.g. `ai_task.id`); most models follow UUID-as-string.
- **Timestamps**: `created_at`/`updated_at` present on lifecycle models.
- **Tenant scoping**: `TenantMixin` + `services/tenant_query.with_tenant_scope()` for multi-tenant isolation (SQLAlchemy + Redis keys).
- **Schema-drift tolerance**: `security_alert_schema.ensure_security_alerts_schema()` runtime-patches missing columns on SQLite dev DBs.
- **Soft state**: `alert_lifecycle._normalize_status()` maps legacy statuses → enum.

---

## 5. API Analysis

### 5.1 Router inventory (38 routers, all under `/api`)

| Router | Prefix/Tag | Purpose |
|--------|-----------|---------|
| `health` | `/health` | Health check + Prometheus metrics |
| `auth` | `/auth` | Login/logout/refresh, bootstrap admin |
| `users` | `/users` | User CRUD |
| `api_keys` | `/api-keys` | API key management |
| `audit` | `/audit` | Audit log query + archive |
| `alert` | `/alert` | **Alert AI analysis** (core) |
| `alerts_lifecycle` | `/alerts/lifecycle` | Alert status/notes/timeline |
| `alert_enrichment` | `/alerts/enrichment` | Threat-intel enrichment |
| `alert_stream` | `/alerts/stream` | Wazuh alert stream ingest |
| `alerts_to_loki` | `/alerts/loki` | Forward to Loki |
| `security_alerts` | `/security-alerts` | External alert ingestion |
| `monitoring_alerts` | `/monitoring-alerts` | Alert rules CRUD |
| `report` | `/report` | LLM report generation |
| `timeline` | `/timeline` | Forensic timeline build |
| `history` | `/history` | Analysis history |
| `assets` | `/assets` | Asset inventory |
| `ioc_hits` | `/ioc-hits` | IOC hit stats |
| `threat_intel` | `/threat-intel` | OTX TI lookups |
| `threat_hunting` | `/threat-hunting` | Hypothesis-driven hunting |
| `playbook` | `/playbook` | Playbook run/execute |
| `playbook_definitions` | `/playbooks/definitions` | Playbook CRUD |
| `triggers` | `/triggers` | Webhook + cron triggers |
| `webhooks` | `/webhooks` | Webhook ingestion |
| `secrets` | `/secrets` | Encrypted secrets (Fernet) |
| `admin_settings` | `/admin/settings` | System settings |
| `ai` | `/ai` | AI Copilot chat |
| `ai_models` | `/ai-models` | Model management |
| `ai_tasks` | `/ai-tasks` | Background AI task queue |
| `ueba` | `/ueba` | UEBA analytics |
| `marketplace` | `/marketplace` | Playbook marketplace |
| `cloud_native` | `/cloud-native` | K8s/container security |
| `monitor` | `/monitor` | Real-time monitor (SSE) |
| `correlation` | `/correlation` | Event correlation engine |
| `blocked_ips` | `/blocked-ips` | IP/domain blocking |
| `security_vulnerabilities` | `/security-vulnerabilities` | Vuln tracking |
| `notifications` | `/notifications` | Channels + queue status |
| `export` | `/export` | Data export |
| `system_dashboard` | `/system/dashboard` | System health |
| `websocket` | `/ws` | WebSocket real-time alerts |
| `websocket_filters` | `/ws/filters` | WS subscription filters |
| `performance` | `/performance` | Perf metrics |

### 5.2 Schemas (24 in `backend/schemas/`)
Pydantic v2 DTOs: `ai_model`, `alert`, `alert_analysis`, `alert_lifecycle`, `alert_stream`, `api_key`, `asset`, `audit`, `blocked_ip`, `common`, `events`, `history`, `impact`, `ioc_hit`, `marketplace`, `playbook`, `playbook_dag`, `playbook_run`, `report`, `security_alert`, `threat_intel`, `timeline`, `trigger`, `user`.

### 5.3 Auth & security model
- **JWT** (`python-jose`), 12h access / 7d refresh. **Cookie-first** strategy on FE (`access_token`/`refresh_token` HttpOnly) with localStorage fallback.
- **CSRF**: `X-CSRF-Token` header on mutating methods; `csrf_token` cookie; validated by `csrf_middleware` (BE) + `lib/csrf.ts` (FE).
- **RBAC**: role-based (`models/rbac.py` `roles`), enforced via `dependencies/rbac.py` + `middleware/authorization_middleware.py`.
- **API keys**: separate `api_keys` model/router for programmatic access.
- **SSRF protection**: `core/ssrf_protection.py` + `http_request_executor` URL/host validation (`is_private_ip`, `resolve_hostname`, `validate_url`).
- **Secrets at rest**: Fernet (`services/security/secret_service.py`) requiring `SECRET_ENCRYPTION_KEY`.
- **Rate limiting**: `middleware/rate_limiter.py`.
- **Idempotency**: `middleware/idempotency_middleware.py` + webhook HMAC (`services/webhook_deduplication.py`).

### 5.4 Timeout policy (`core/config.py`)
`api_timeout_analysis_ms=120000` · `default_ms=30000` · `health_ms=5000` · `report_ms=120000` · `timeline_ms=120000` · `dag_run_ms=300000`.

---

## 6. Core Business Analysis

### 6.1 Services overview (`backend/services/`)

The **37 top-level services** + **9 subpackages** form the business core. Singleton pattern via `get_*_service()` factories; all async.

**Headline service**: `AlertService.analyze()` (`services/alerting/alert_service.py:76`) is the integration hub — orchestrates IOC extraction, LLM analysis, threat intel, impact, and history persistence.

| Concern | Service(s) |
|---------|-----------|
| **Alert pipeline** | `services/alerting/*` (dedup, aggregator, storm-suppressor, enrichment, lifecycle, evaluator, stream) |
| **AI / LLM** | `ai_providers.py` (6 providers) → `ai_service_enhanced.py` (orchestration + RAG) → `llm_retry.py` (resilience) → `ai_task_service.py` (DB-backed async queue, max_concurrent=5) |
| **RAG / Vector** | `vector_store.py` (`ChromaDBStore`, `MemoryVectorStore`, factory) |
| **Reports** | `report_service.py` (LLM-driven SOC reports) |
| **Timeline** | `timeline_service.py` (dual-engine IOC extraction) |
| **Threat intel** | `threat_intel_service.py` (OTX, internal-domain/blocked-TLD aware) |
| **Threat hunting** | `threat_hunting_service.py` (hypothesis-driven) |
| **UEBA** | `ueba_service.py` (baselines, anomaly detection, risk profiles) |
| **Event correlation** | `event_correlation_service.py` + `services/correlation/` (DSL `RuleEngine`, windowed aggregation, weighted scoring) |
| **Impact** | `impact_service.py` + `asset_service.py` |
| **Playbook lifecycle** | `services/playbook/*` (run, DAG compiler/engine/scheduler, context, versioning, import/export, replay) |
| **Playbook executors** | `services/playbook_executors/*` (per-node-type) |
| **Notifications** | `services/notifications/*` (Email, Feishu/Lark, Slack + registry/templates) |
| **Marketplace** | `marketplace_service.py` (`PlaybookMarketplace`) |
| **Cloud-native** | `cloud_native_service.py` (K8s/container findings) |
| **Run queue** | `run_queue_manager.py` (concurrency=3, idempotency, FIFO/priority) |
| **Triggers** | `trigger_service.py` + `cron_scheduler_service.py` |
| **Webhooks** | `webhook_deduplication.py` + `loki_alert_sender.py` |
| **Websocket infra** | `websocket_manager.py`, `websocket_connection_pool.py`, `websocket_compression.py`, `message_batch_service.py`, `message_filter.py`, `message_queue.py` |
| **Caching** | `query_cache.py` (`TTLCache`, `cached()` decorator) |
| **Audit/archive** | `audit_archive_service.py` (`run_scheduled_archival`) |
| **Tenant isolation** | `tenant_query.py` |
| **Event bus** | `event_bus.py` (async pub/sub over message broker) |

### 6.2 Message broker
Pluggable ABC (`services/message_broker/base.py`): `publish/consume/ack/nack/replay_dlq`. **Redis is the only live impl** (Streams + DLQ + delayed queue). Kafka stub exists but unimplemented.

### 6.3 Lifecycle management
All long-running services follow the `core/lifecycle.py` `LifecycleService` pattern; `services/lifecycle/` wraps each (ai_task_processor, cron_scheduler, database, queue_manager, rate_limiter, websocket_monitoring). Startup/shutdown wired in `main.py` lifespan.

---

## 7. Key Modules

### 7.1 Playbook Engine (`backend/playbook_engine/`)

Multiple versions coexist:
- **`dag/`** — generic DAG primitives (`engine.py`, `state_machine.py`, `retry_policy.py`, `exceptions.py`).
- **`v6_linear/`** — legacy linear pipeline engine (`engine.py`, `models.py`, `registry.py`).
- **`v7_dag/`** — **current active engine** (DAG-based). `base_node.py`, `registry.py`, plus `plugins/` (15 builtin node types).
- **`triggers/`** — `alert_triggers.py`, `cron.py`, `webhook.py`.
- **`notifications/`** — `http_callback.py`, `slack.py`.
- **`adapter.py`** — facade bridging engine versions.

**15 builtin node plugins** (`v7_dag/plugins/`): `action_plan`, `asset_enrich`, `decision`, `extract_iocs`, `generate_report`, `http_request`, `human_approval`, `normalize`, `otx_lookup`, `parse_json`, `risk_score`, `slack_notify`, `sleep`, `timeline_build`.

The higher-level orchestration lives in `services/playbook/` (compiler validates & raises `DAGValidationError`; engine handles node-readiness/rollback; scheduler runs concurrent async execution + cancel). `playbook_executors/` provides the per-node-type executors selected via `ExecutorFactory`, all subclassing `BaseExecutor` with SSRF guards.

### 7.2 AI / LLM Subsystem

```
ai_providers.LLMFactory.create_from_config()
   → LLMProvider (httpx) — Zhipu/Claude/OpenAI/NVIDIA/Moonshot/OpenRouter
   → EnhancedAIService.generate_structured(prompt, response_class)
        ├─ clean_json_content() + type coercion + retry (max_retries=3)
        └─ RAG via VectorStoreFactory (Chroma / Memory)
   → LLMRetryService wrapper (MAX_RETRIES=2)
        ├─ structured path: schema-validate → _create_correction_prompt → retry → _create_degraded_response fallback
        └─ free-form path: exponential backoff → returns ("", model, degraded=True) on total failure
   → AITaskQueueService.submit_task()
        ├─ DB row PENDING → asyncio.Queue
        ├─ _processor_loop (max_concurrent=5) → asyncio.wait_for(timeout)
        ├─ _handle_task_error → TIMEOUT/FAILED; _maybe_retry_task
        └─ status: get_task_status / cancel_task
```
**Guarantee**: callers always receive a valid typed object (degraded mode never raises).

### 7.3 Alerting Pipeline
See §3.3. Key classes: `WazuhStreamService`, `AlertDeduplicator` (SHA-256 fingerprint, strict/balanced/relaxed), `AlertAggregator`, `AlertStormSuppressor` (per-severity thresholds: critical=10/high=20/med=50/low=100/info=200, 15-min window), `AlertEnrichmentService` (OTX, 24h TTL), `AlertLifecycleService` (timeline synthesis), `AlertEvaluator` (rule → Log/Webhook/Email channels).

### 7.4 Security hardening
`core/prompt_sanitizer.py` (prompt injection guards), `core/ssrf_protection.py`, `core/sensitive_data.py`, `core/security_validators.py`, `core/token_blacklist.py`, `middleware/security_headers.py`, Fernet secret service, webhook HMAC idempotency, tenant isolation, RBAC + resource authorization, CSRF, rate limiting, idempotency.

---

## 8. Development Quickstart

### 8.1 Environment setup
```bash
# 1. Python venv (backend)
python3.11 -m venv venv && source venv/bin/activate
cd backend && pip install -r requirements.txt

# 2. Frontend deps
cd ../frontend && npm install

# 3. Configure env
cp .env.example .env          # fill in: JWT_SECRET, ZHIPU_API_KEY/ANTHROPIC_API_KEY,
                              #   SECRET_ENCRYPTION_KEY, OTX_API_KEY, REDIS_URL, DATABASE_URL
```

### 8.2 Run (dev)
```bash
# From repo root — runs backend (:8000) + frontend (:3003) concurrently
npm run dev

# Or separately:
npm run dev:backend    # uvicorn main:app --reload --port 8000
npm run dev:frontend   # next dev -p 3003
```
- Frontend proxies `/api/*` → `http://localhost:8000/api/*` (in `next.config.js`).
- DB defaults to `data/app.db` (SQLite) — set `DATABASE_URL=postgresql://...` for Postgres.

### 8.3 Database
```bash
npm run db:migrate      # alembic upgrade head
npm run db:rollback     # alembic downgrade -1
npm run db:reset        # downgrade base && upgrade head
```

### 8.4 Quality gates
```bash
npm run lint            # FE: tsc --noEmit + prettier --check | BE: ruff check .
npm run lint:fix        # FE: prettier --write | BE: ruff --fix
npm run format          # FE: prettier | BE: black + isort
npm run type-check      # FE: tsc --noEmit

npm run test            # FE: vitest | BE: pytest
npm run test:frontend   # vitest run
npm run test:backend    # pytest
npm run test:coverage   # both with coverage

# E2E (frontend/)
cd frontend && npm run test:e2e        # playwright
cd frontend && npm run test:e2e:ui     # playwright --ui
```

### 8.5 Common tasks

**Add a new API endpoint** (per `AGENTS.md`):
1. Define SQLAlchemy model in `backend/models/`
2. Create repository in `backend/repositories/`
3. Implement service in `backend/services/` (async, `get_*_service()` factory)
4. Create Pydantic schemas in `backend/schemas/`
5. Add router in `backend/routers/`, register in `backend/main.py`
6. Generate migration: `alembic revision --autogenerate -m "..."`
7. Add tests in `backend/tests/`

**Add a frontend page**:
1. Create `frontend/app/[locale]/<route>/page.tsx`
2. Gate with `loadAuthState()` / `isAdmin()` (client-side)
3. Add API module under `frontend/lib/api/` (use `apiClient`)
4. Add components under `frontend/components/<feature>/`
5. Add i18n keys under `frontend/messages/{en,zh}/<namespace>.json` + register namespace in `i18n/namespaces.ts`
6. Use `useTranslations('<namespace>')`

**Add a playbook node type**:
1. Create executor in `backend/services/playbook_executors/` (subclass `BaseExecutor`)
2. Register in `ExecutorFactory`
3. Create plugin in `backend/playbook_engine/v7_dag/plugins/`

### 8.6 Conventions to follow
- **Python**: Ruff (lint) + Black (format) + isort; 100% type annotations on public API; async-first.
- **TypeScript**: strict mode; `@/*` path alias; prefer TanStack Query for server state, Zustand for UI state.
- **Naming**: backend `snake_case.py`; frontend `PascalCase.tsx` for components, `camelCase.ts` for utils.
- **Git**: branch prefix by type (`feat/`, `fix/`, `ui/`, `refactor/`, `perf/`, `a11y/`); conventional commit messages.
- **Security**: never commit secrets — use `services/secrets` + Fernet; validate all inputs; apply RBAC deps; SSRF-guard any outbound HTTP in playbooks.

### 8.7 Key entry-point file map

| I want to... | Look at... |
|--------------|-----------|
| Understand app bootstrap | `backend/main.py` |
| Change config/env | `backend/core/config.py` + `.env` |
| Add/modify a DB table | `backend/models/` + `backend/migrations_alembic/versions/` |
| Add an API endpoint | `backend/routers/` + `backend/services/` + `backend/schemas/` |
| Change alert analysis | `backend/services/alerting/alert_service.py:76` (`AlertService.analyze`) |
| Tune LLM behavior | `backend/services/ai_service_enhanced.py` + `backend/services/llm_retry.py` + `backend/prompts/` |
| Add a playbook node | `backend/services/playbook_executors/` + `backend/playbook_engine/v7_dag/plugins/` |
| Add a notification channel | `backend/services/notifications/` |
| Frontend routing | `frontend/app/[locale]/` |
| Frontend API calls | `frontend/lib/api-client.ts` + `frontend/lib/api/` |
| Frontend real-time | `frontend/lib/alertWebSocket.ts` + `frontend/hooks/useMonitor.ts` |
| i18n | `frontend/messages/{en,zh}/` + `frontend/i18n/namespaces.ts` |
| Deploy | `docker-compose.prod.yml` + `k8s/` + `.github/workflows/ci-cd.yml` |

---

### Known tech-debt observations (from analysis)
- **Dual API clients** in FE (`lib/api-client.ts` primary vs `lib/api/client.ts` legacy) — consolidate.
- **Dual caching** in FE (TanStack Query vs `lib/cache.ts`/`useCachedQuery`) — pick one.
- **Auth store** is custom `useSyncExternalStore`, not Zustand (convertible per its own comment).
- **`next-themes`** is a dependency but unused (theming via custom Zustand `themeStore`).
- **`providers/`** dir is empty — real providers live in `components/providers/`.
- **Duplicate i18n config** (`i18n.ts` + `i18n/request.ts`).
- **Legacy compat shims** in `lib/api/legacy.ts` (`api`, `api_v7`, …) — in-progress migration.
- **`marketplace/`** backend dir is empty (logic in `services/marketplace_service.py`).
- **`integration/`** services subpackage is an empty placeholder.
- **Kafka broker** stubbed, not implemented (Redis only).
- **FE route protection is client-side** per page (no middleware-level guard).

---

*Generated 2026-06-17 from full codebase scan (Phases 1–8).*
