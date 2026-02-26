# SOC Copilot - Comprehensive API Audit Report

**Generated:** 2026-02-25
**Project:** SOC Copilot v0.8+
**Scope:** Backend APIs, Frontend Pages, Services, and Models

---

## Executive Summary

This report provides a comprehensive audit of the SOC Copilot platform, documenting all backend APIs, frontend pages, services, data models, and their interconnections. The analysis reveals:

- **37 Backend Router Files** providing **200+ API endpoints**
- **28 Frontend Pages** across the [locale] directory structure
- **55+ Service Files** implementing business logic
- **28 Data Models** defining the database schema
- **15 API endpoints without dedicated frontend pages**
- **5 major functional areas with partial frontend implementation**

---

## 1. Backend API Routes

### 1.1 Alert Management APIs

#### `/api/analyze-alert` (POST)
- **Purpose:** Analyze security alerts/logs
- **Router:** `alert.py`
- **Response:** AlertAnalysisResponse

#### `/api/v1/alerts` (GET, POST, PATCH, DELETE)
- **Purpose:** Security alert CRUD operations
- **Router:** `security_alerts.py`
- **Endpoints:**
  - `GET /` - List all security alerts with pagination
  - `GET /{alert_id}` - Get specific alert details
  - `GET /stats/summary` - Alert statistics dashboard
  - `POST /` - Create new security alert
  - `POST /alerts` - Bulk alert import
  - `PATCH /{alert_id}` - Update alert properties
  - `DELETE /{alert_id}` - Delete an alert

#### `/api/v1/alerts/lifecycle` (GET, PATCH, POST)
- **Purpose:** Alert lifecycle management
- **Router:** `alerts_lifecycle.py`
- **Endpoints:**
  - `GET /{alert_id}/lifecycle` - Get alert lifecycle info
  - `PATCH /{alert_id}/status` - Update alert status
  - `POST /{alert_id}/assign` - Assign alert to analyst
  - `POST /{alert_id}/resolve` - Mark alert as resolved
  - `POST /{alert_id}/escalate` - Escalate alert priority
  - `POST /{alert_id}/notes` - Add investigation notes
  - `POST /batch/update` - Batch update multiple alerts
  - `GET /statistics/summary` - Alert statistics
  - `GET /statistics/trends` - Alert trends over time
  - `GET /statistics/top-threats` - Top threat sources
  - `GET /statistics/threat-intel` - Threat intel stats

### 1.2 AI & Machine Learning APIs

#### `/api/ai` (POST, GET)
- **Purpose:** AI-powered analysis and chat
- **Router:** `ai.py`
- **Endpoints:**
  - `POST /analyze-alert` - AI-powered alert analysis
  - `POST /query` - Natural language query processing
  - `POST /recommend-playbooks` - AI playbook recommendations
  - `POST /chat` - Chat with AI assistant
  - `POST /generate-report` - Generate investigation reports
  - `GET /status` - AI service health status

#### `/api/ai/models` (GET, POST)
- **Purpose:** AI model management
- **Router:** `ai_models.py`
- **Endpoints:**
  - `GET /` - List available AI models
  - `GET /default` - Get default model
  - `POST /default` - Set default model
  - `POST /test` - Test model connectivity
  - `POST /refresh` - Refresh model list (admin)

#### `/ai-tasks` (POST, GET)
- **Purpose:** Background AI task management
- **Router:** `ai_tasks.py`
- **Endpoints:**
  - `POST /submit` - Submit AI task for background processing
  - `GET /{task_id}/status` - Get task status
  - `GET /{task_id}/result` - Get task result
  - `POST /{task_id}/cancel` - Cancel task
  - `GET /` - List user tasks with filters
  - `GET /types` - Get available task types

### 1.3 Authentication & User Management APIs

#### `/api/auth` (POST)
- **Purpose:** Authentication operations
- **Router:** `auth.py`
- **Endpoints:**
  - `POST /register` - User registration
  - `POST /login` - User login
  - `POST /logout` - User logout
  - `POST /refresh` - Refresh access token
  - `GET /me` - Get current user info

#### `/api/users` (GET, POST, PATCH, DELETE)
- **Purpose:** User management
- **Router:** `users.py`
- **Endpoints:**
  - `GET /` - List users (admin)
  - `GET /{user_id}` - Get user details
  - `POST /` - Create user (admin)
  - `PATCH /{user_id}` - Update user
  - `DELETE /{user_id}` - Delete user
  - `POST /{user_id}/reset-password` - Reset password (admin)
  - `POST /unlock-user/{username}` - Unlock locked account

### 1.4 API Keys Management

#### `/api/api-keys` (GET, POST, PATCH, DELETE)
- **Purpose:** API key CRUD operations
- **Router:** `api_keys.py`
- **Endpoints:**
  - `GET /` - List user's API keys
  - `POST /` - Create new API key
  - `PATCH /{api_key_id}` - Update API key
  - `DELETE /{api_key_id}` - Disable API key
  - `GET /admin/all` - List all API keys (admin)

### 1.5 Assets Management

#### `/api/assets` (GET, POST, PATCH, DELETE)
- **Purpose:** Asset inventory management
- **Router:** `assets.py`
- **Endpoints:**
  - `GET /` - List assets with search
  - `POST /` - Create asset
  - `POST /import` - Bulk import assets
  - `GET /{asset_id}` - Get asset details
  - `PATCH /{asset_id}` - Update asset
  - `DELETE /{asset_id}` - Delete asset

### 1.6 Audit & Compliance

#### `/api/audit-logs` (GET, POST)
- **Purpose:** Audit log management
- **Router:** `audit.py`
- **Endpoints:**
  - `GET /` - List audit logs with filters
  - `GET /stats/summary` - Audit statistics
  - `GET /target/{target_type}/{target_id}` - Get logs for specific target
  - `POST /cleanup` - Clean up old logs (admin)

### 1.7 Playbook Engine APIs

#### `/api/playbooks` (GET, POST, PATCH, DELETE)
- **Purpose:** Playbook execution and monitoring
- **Router:** `playbook_definitions.py`
- **Endpoints:**
  - `GET /` - List playbook definitions
  - `GET /{definition_id}` - Get playbook definition
  - `POST /` - Create playbook definition
  - `PATCH /{definition_id}` - Update playbook
  - `DELETE /{definition_id}` - Delete playbook
  - `POST /{definition_id}/execute` - Execute playbook
  - `GET /runs/{run_id}` - Get playbook run status
  - `GET /runs/{run_id}/nodes` - Get node execution details
  - `POST /runs/{run_id}/cancel` - Cancel running playbook

#### `/api/triggers` (GET, POST, PUT, DELETE)
- **Purpose:** Trigger management for automated playbook execution
- **Router:** `triggers.py`
- **Endpoints:**
  - `GET /` - List all triggers
  - `GET /{trigger_id}` - Get trigger details
  - `GET /{trigger_id}/invocations` - Get trigger invocations
  - `POST /` - Create trigger
  - `POST /cron` - Create cron trigger
  - `POST /webhook` - Create webhook trigger
  - `PUT /{trigger_id}` - Update trigger
  - `DELETE /{trigger_id}` - Delete trigger
  - `POST /{trigger_id}/test` - Test trigger
  - `POST /{trigger_id}/webhook/regenerate-secret` - Regenerate webhook secret

### 1.8 Threat Intelligence APIs

#### `/api/threat-intel` (GET, POST, DELETE)
- **Purpose:** Threat intelligence management
- **Router:** `threat_intel.py`
- **Endpoints:**
  - `GET /otx` - Query OTX threat intel
  - `POST /otx/bulk` - Bulk OTX lookup
  - `POST /manual` - Manual IOC submission
  - `GET /` - List IOC hits
  - `DELETE /cache/{ioc_type}/{ioc_value}` - Clear specific IOC cache
  - `DELETE /cache/expired` - Clear expired cache
  - `DELETE /cache/all` - Clear all cache

#### `/api/ioc-hits` (GET)
- **Purpose:** IOC hit management
- **Router:** `ioc_hits.py`
- **Endpoints:**
  - `GET /` - List all IOC hits
  - `GET /by-asset/{asset_id}` - Get IOCs for asset
  - `GET /by-history/{history_id}` - Get IOCs for history entry

### 1.9 Threat Hunting APIs

#### `/api/threat-hunting` (POST, GET)
- **Purpose:** Proactive threat hunting
- **Router:** `threat_hunting.py`
- **Endpoints:**
  - `POST /execute` - Execute hunt query
  - `GET /hypotheses` - List hunt hypotheses
  - `POST /hypotheses` - Create hunt hypothesis
  - `POST /ioc-hunt` - Hunt for specific IOCs
  - `GET /trending` - Get trending threats

### 1.10 UEBA (User Entity Behavior Analytics) APIs

#### `/api/ueba` (GET, POST)
- **Purpose:** User behavior anomaly detection
- **Router:** `ueba.py`
- **Endpoints:**
  - `GET /` - Get UEBA overview
  - `GET /risk-profile/{user_id}` - Get user risk profile
  - `GET /high-risk-users` - Get high-risk users list
  - `POST /detect` - Run anomaly detection
  - `POST /build-baseline` - Build behavior baseline

### 1.11 Event Correlation APIs

#### `/api/correlation` (POST, GET, PUT)
- **Purpose:** Event correlation and incident detection
- **Router:** `correlation.py`
- **Endpoints:**
  - `POST /correlate` - Correlate events
  - `GET /incidents` - List correlated incidents
  - `GET /incidents/{incident_id}` - Get incident details
  - `PUT /incidents/{incident_id}/status` - Update incident status
  - `GET /rules` - List correlation rules
  - `POST /rules` - Create correlation rule
  - `PUT /rules/{rule_id}` - Update rule
  - `DELETE /rules/{rule_id}` - Delete rule
  - `POST /rules/{rule_id}/toggle` - Enable/disable rule
  - `GET /rules` - List correlation rules

### 1.12 Cloud Native Security APIs

#### `/api/cloud-native` (GET, POST)
- **Purpose:** Cloud and container security
- **Router:** `cloud_native.py`
- **Endpoints:**
  - `GET /` - Cloud native overview
  - `GET /cloud/connections` - List cloud connections
  - `GET /kubernetes/resources/{resource_type}` - Get K8s resources
  - `POST /containers/scan` - Scan container images
  - `POST /kubernetes/scan` - Scan K8s cluster
  - `GET /compliance/report` - Get compliance report

### 1.13 Dify Integration APIs

#### `/api/dify` (GET, POST)
- **Purpose:** Dify LLM platform integration
- **Router:** `dify.py`
- **Endpoints:**
  - `GET /workflows` - List Dify workflows
  - `GET /workflows/{app_id}` - Get workflow details
  - `POST /workflows/{app_id}/execute` - Execute workflow
  - `POST /workflows/{app_id}/import` - Import workflow to playbook
  - `POST /workflows/sync/{definition_id}` - Sync playbook with Dify
  - `POST /playbooks/{playbook_id}/download` - Download playbook for Dify
  - `GET /playbooks` - List available playbooks
  - `GET /playbooks/{playbook_id}` - Get playbook details
  - `POST /playbooks/{playbook_id}/reviews` - Submit playbook review
  - `GET /playbooks/{playbook_id}/reviews` - Get playbook reviews
  - `GET /integration/status` - Check integration status
  - `GET /test-connection` - Test Dify connection

### 1.14 Marketplace APIs

#### `/api/marketplace` (GET, POST)
- **Purpose:** Playbook marketplace
- **Router:** `marketplace.py`
- **Endpoints:**
  - `GET /featured` - Get featured playbooks
  - `GET /categories` - Get playbook categories
  - `GET /workflows` - Browse marketplace workflows
  - `POST /workflows/{app_id}/import` - Import from marketplace
  - `GET /workflows/{app_id}` - Get workflow details
  - `POST /internal/case-update` - Internal case update endpoint
  - `POST /internal/extract-iocs` - Extract IOCs from text
  - `POST /internal/generate-report` - Generate reports
  - `POST /internal/mock-blocklist` - Mock blocklist endpoint
  - `POST /internal/normalize` - Normalize event data

### 1.15 Monitoring & Observability APIs

#### `/api/monitor` (GET, POST, DELETE)
- **Purpose:** System monitoring and health checks
- **Router:** `monitor.py`
- **Endpoints:**
  - `GET /dashboard` - Get monitoring dashboard
  - `GET /metrics` - Get system metrics
  - `GET /history` - Get metric history
  - `DELETE /history/clear` - Clear metric history
  - `DELETE /history/cleanup` - Clean up old metrics
  - `POST /process-recent` - Process recent metrics

#### `/api/health` (GET)
- **Purpose:** Health check endpoints
- **Router:** `health.py`
- **Endpoints:**
  - `GET /health` - General health check
  - `GET /health/live` - Liveness probe
  - `GET /health/ready` - Readiness probe
  - `GET /database` - Database health
  - `GET /redis` - Redis health
  - `GET /resources` - System resource usage

#### `/api/timeline` (GET, POST)
- **Purpose:** Timeline management
- **Router:** `timeline.py`
- **Endpoints:**
  - `POST /api/build-timeline` - Build event timeline
  - `GET /api/timeline/health` - Timeline service health

### 1.16 Alert Enrichment APIs

#### `/api/alert-enrichment` (POST)
- **Purpose:** Threat intelligence enrichment
- **Router:** `alert_enrichment.py`
- **Endpoints:**
  - `POST /process/{alert_id}` - Process and enrich alert
  - `POST /cache/refresh` - Refresh enrichment cache
  - `POST /test-alert` - Test enrichment with sample alert

### 1.17 Wazuh Integration APIs

#### `/api/wazuh` (GET, POST)
- **Purpose:** Wazuh SIEM integration
- **Router:** `wazuh_integration.py`
- **Endpoints:**
  - `GET /health` - Wazuh health check
  - `GET /agents` - List Wazuh agents
  - `GET /agents/{agent_id}` - Get agent details
  - `POST /receiver/configure` - Configure event receiver
  - `POST /receiver/start` - Start event receiver
  - `POST /receiver/stop` - Stop event receiver
  - `POST /receiver/restart` - Restart event receiver
  - `GET /receiver/stats` - Get receiver statistics
  - `GET /alerts/summary` - Get alerts summary
  - `POST /ingest` - Ingest Wazuh alert
  - `GET /queue-stats` - Get queue statistics

#### `/api/wazuh/webhook` (POST)
- **Purpose:** Wazuh webhook receiver
- **Router:** `wazuh_event_receiver.py`
- **Endpoints:**
  - `POST /` - Receive Wazuh webhook events

### 1.18 Security Settings Management

#### `/api/admin/settings` (GET, POST)
- **Purpose:** Admin settings management
- **Router:** `admin_settings.py`
- **Endpoints:**
  - `GET /` - Get system settings
  - `POST /` - Update system settings
  - `GET /timeouts` - Get API timeout configuration

#### `/api/secrets` (GET, POST, PATCH, DELETE)
- **Purpose:** Secret management
- **Router:** `secrets.py`
- **Endpoints:**
  - `GET /` - List secrets
  - `GET /config` - Get secrets configuration
  - `GET /{secret_name}` - Get secret value
  - `POST /` - Create secret
  - `PATCH /{secret_name}` - Update secret
  - `DELETE /{secret_name}` - Delete secret
  - `GET /key-status` - Check encryption key status

### 1.19 Reporting APIs

#### `/api/report` (POST)
- **Purpose:** Report generation
- **Router:** `report.py`
- **Endpoints:**
  - `POST /api/generate-report` - Generate investigation report

#### `/api/export` (GET)
- **Purpose:** Data export
- **Router:** `export.py`
- **Endpoints:**
  - `GET /alerts` - Export alert history
  - `GET /audit-logs` - Export audit logs
  - `GET /playbook-runs` - Export playbook runs

### 1.20 System Dashboard APIs

#### `/api/system-dashboard` (GET)
- **Purpose:** System-wide dashboard
- **Router:** `system_dashboard.py`
- **Endpoints:**
  - `GET /dashboard` - Get full system dashboard
  - `GET /stats/summary` - Get summary statistics
  - `GET /features` - Get feature flags

### 1.21 WebSocket & Real-time APIs

#### `/api/websocket/ws/alerts` (WebSocket)
- **Purpose:** Real-time alert streaming
- **Router:** `websocket.py`
- **Endpoints:**
  - `WS /ws/alerts` - WebSocket connection for alerts
  - `GET /ws/stats` - WebSocket statistics

#### `/api/notifications` (GET, POST)
- **Purpose:** Notification management
- **Router:** `notifications.py`
- **Endpoints:**
  - `GET /channels` - Get notification channels
  - `POST /test` - Send test notification

### 1.22 History Management APIs

#### `/api/history` (GET, POST, DELETE)
- **Purpose:** Historical data management
- **Router:** `history.py`
- **Endpoints:**
  - `GET /` - List history entries
  - `POST /` - Create history entry
  - `GET /{history_id}` - Get history entry
  - `DELETE /{history_id}` - Delete history entry

---

## 2. Frontend Pages

### 2.1 Main Application Pages

| Route | Page Title | Description |
|-------|-----------|-------------|
| `/` | Home | Main dashboard/landing page |
| `/login` | Login | User authentication page |
| `/ai-assistant` | AI Assistant | AI chat interface |
| `/alerts` | Alerts | Alert list and management |
| `/alerts/[id]` | Alert Details | Individual alert view |
| `/assets` | Assets | Asset inventory management |
| `/audit` | Audit Log | Audit log viewer |
| `/correlation` | Event Correlation | Correlated events and incidents |
| `/cloud-native` | Cloud Native | Cloud security monitoring |
| `/dify` | Dify Integration | Dify workflow management |
| `/marketplace` | Marketplace | Playbook marketplace |
| `/monitor` | Monitor | System monitoring dashboard |
| `/page` | Page | Generic page (placeholder) |
| `/playbooks` | Playbooks | Playbook definitions and runs |
| `/reports` | Reports | Investigation reports |
| `/settings` | Settings | User settings |
| `/test` | Test | Testing page |
| `/threat-hunting` | Threat Hunting | Threat hunting interface |
| `/threat-intel` | Threat Intel | Threat intelligence dashboard |
| `/threat-intel/dashboard` | TI Dashboard | Detailed threat intel view |
| `/triggers` | Triggers | Trigger management |
| `/triggers/cron/new` | New Cron Trigger | Create cron trigger |
| `/triggers/webhook/new` | New Webhook Trigger | Create webhook trigger |
| `/ueba` | UEBA | User behavior analytics |
| `/wazuh` | Wazuh | Wazuh integration page |

### 2.2 Settings Pages

| Route | Page Title | Description |
|-------|-----------|-------------|
| `/settings` | User Settings | General user settings |
| `/settings/api-keys` | API Keys | API key management |
| `/settings/notifications` | Notifications | Notification preferences |

### 2.3 Admin Pages

| Route | Page Title | Description |
|-------|-----------|-------------|
| `/admin/settings` | Admin Settings | System-wide settings |
| `/admin/users` | User Management | User administration |
| `/admin/secrets` | Secrets Management | Secret/key management |
| `/admin/audit` | Admin Audit | Admin audit log view |
| `/admin/health` | System Health | System health monitoring |

---

## 3. Backend Services

### 3.1 AI & Machine Learning Services

| Service File | Primary Functionality |
|--------------|---------------------|
| `ai_service.py` | Core AI service implementation |
| `ai_service_enhanced.py` | Enhanced AI with RAG capabilities |
| `ai_providers.py` | LLM provider factory (Anthropic, Zhipu, etc.) |
| `ai_task_service.py` | Background AI task management |
| `ai_queue_manager.py` | AI task queue and worker management |
| `vector_store.py` | Vector database for RAG |

### 3.2 Alert Services

| Service File | Primary Functionality |
|--------------|---------------------|
| `alert_service.py` | Alert analysis and processing |
| `alert_lifecycle.py` | Alert lifecycle management |
| `alert_enrichment.py` | Threat intelligence enrichment |

### 3.3 Playbook Engine Services

| Service File | Primary Functionality |
|--------------|---------------------|
| `playbook_service.py` | Core playbook operations |
| `playbook_run_service.py` | Playbook execution |
| `playbook_dag_compiler.py` | DAG compilation from definitions |
| `playbook_dag_scheduler.py` | Playbook scheduling |
| `playbook_dag_engine.py` | DAG execution engine |
| `playbook_context_service.py` | Playbook context management |
| `playbook_version_service.py` | Playbook versioning |
| `playbook_import_export_service.py` | Import/export functionality |
| `playbook_replay_service.py` | Playbook replay |
| `run_queue_manager.py` | Run queue management |

### 3.4 Playbook Executors

Located in `services/playbook_executors/`:
- `executor_base.py` - Base executor class
- `human_approval_executor.py` - Human approval steps
- `ti_lookup_otx_executor.py` - OTX threat intel lookups

### 3.5 Threat Intelligence Services

| Service File | Primary Functionality |
|--------------|---------------------|
| `threat_intel_service.py` | Core threat intel operations |
| `ioc_hits_service.py` | IOC hit tracking |

### 3.6 Integration Services

| Service File | Primary Functionality |
|--------------|---------------------|
| `dify_service.py` | Dify platform integration |
| `dify_adapter.py` | Dify API adapter |
| `wazuh_client.py` | Wazuh API client |
| `wazuh_alert_mapper.py` | Wazuh alert mapping |
| `wazuh_log_receiver.py` | Wazuh log ingestion |
| `wazuh_event_receiver.py` | Wazuh event handling |

### 3.7 Correlation & Detection Services

| Service File | Primary Functionality |
|--------------|---------------------|
| `event_correlation_service.py` | Event correlation logic |
| `trigger_service.py` | Trigger management |
| `cron_scheduler_service.py` | Cron-based scheduling |

### 3.8 Analysis & Hunting Services

| Service File | Primary Functionality |
|--------------|---------------------|
| `threat_hunting_service.py` | Threat hunting operations |
| `ueba_service.py` | User behavior analytics |
| `timeline_service.py` | Timeline construction |
| `impact_service.py` | Impact analysis |

### 3.9 Security & Monitoring Services

| Service File | Primary Functionality |
|--------------|---------------------|
| `audit_archive_service.py` | Audit log archival |
| `notification_service.py` | Notification handling |
| `webhook_deduplication.py` | Webhook deduplication |
| `websocket_manager.py` | WebSocket connection management |

### 3.10 Messaging & Queue Services

Located in `services/message_broker/`:
- Message broker integration

Located in `services/notifications/`:
- Notification channel implementations

Located in `services/correlation/`:
- Correlation-specific messaging

### 3.11 Utility Services

| Service File | Primary Functionality |
|--------------|---------------------|
| `secret_service.py` | Secret management |
| `asset_service.py` | Asset management |
| `history_service.py` | Historical data |
| `report_service.py` | Report generation |
| `cloud_native_service.py` | Cloud operations |
| `cookie_auth.py` | Cookie-based authentication |
| `message_queue_manager.py` | Queue management |
| `event_bus.py` | Event bus implementation |
| `offline_cache.py` | Offline caching |
| `llm_retry.py` | LLM retry logic |

---

## 4. Backend Data Models

### 4.1 Core Models

| Model | Description |
|-------|-------------|
| `user.py` | User accounts and authentication |
| `api_key.py` | API key management |
| `asset.py` | Asset inventory |
| `audit_log.py` | Audit trail |

### 4.2 Security Models

| Model | Description |
|-------|-------------|
| `security_alert.py` | Security alerts |
| `correlated_event.py` | Correlated security events |
| `correlation_rule.py` | Event correlation rules |
| `event_similarity.py` | Event similarity metrics |
| `root_cause_analysis.py` | Root cause analysis results |

### 4.3 Threat Intelligence Models

| Model | Description |
|-------|-------------|
| `ioc_hit.py` | IOC matches |
| `threat_intel_cache.py` | Cached threat intel |

### 4.4 Playbook Engine Models

| Model | Description |
|-------|-------------|
| `playbook_definition.py` | Playbook definitions |
| `playbook_run.py` | Playbook execution runs |
| `playbook_node_run.py` | Node execution status |
| `playbook_node_attempt.py` | Node execution attempts |
| `playbook_output.py` | Playbook outputs |
| `playbook_approval.py` | Human approval records |
| `trigger.py` | Trigger configurations |

### 4.5 Monitoring & History Models

| Model | Description |
|-------|-------------|
| `history.py` | Historical data |
| `monitor_history.py` | Monitoring metrics history |

### 4.6 AI Models

| Model | Description |
|-------|-------------|
| `ai_model.py` | AI model definitions |
| `ai_task.py` | AI task tracking |
| `ai_user_setting.py` | User AI preferences |

### 4.7 Other Models

| Model | Description |
|-------|-------------|
| `secret.py` | Secret storage |
| `rbac.py` | Role-based access control |
| `tenant_mixin.py` | Multi-tenancy support |

---

## 5. Gap Analysis

### 5.1 Backend APIs WITHOUT Dedicated Frontend Pages

The following backend APIs lack dedicated frontend pages:

#### High Priority Gaps

1. **AI Task Management** (`/ai-tasks`)
   - **APIs:** Submit, status, result, cancel, list tasks
   - **Status:** No dedicated UI
   - **Impact:** Users cannot monitor background AI tasks

2. **AI Models Management** (`/api/ai/models`)
   - **APIs:** List, test, set default models
   - **Status:** Partial integration in AI Assistant
   - **Impact:** No dedicated model management interface

3. **Export Functionality** (`/api/export`)
   - **APIs:** Export alerts, audit logs, playbook runs
   - **Status:** No dedicated UI
   - **Impact:** Data export not accessible from UI

4. **System Dashboard** (`/api/system-dashboard`)
   - **APIs:** Full system dashboard
   - **Status:** Partially implemented in home page
   - **Impact:** No comprehensive system view

5. **Correlation Rules Management** (`/api/correlation/rules`)
   - **APIs:** CRUD for correlation rules
   - **Status:** No dedicated rule management UI
   - **Impact:** Cannot manage correlation rules from UI

#### Medium Priority Gaps

6. **Cloud Native Security** (Partial)
   - **APIs:** Full cloud security monitoring
   - **Status:** Page exists but likely incomplete
   - **Impact:** Limited cloud visibility

7. **Alert Enrichment** (`/api/alert-enrichment`)
   - **APIs:** Process and enrich alerts
   - **Status:** Integrated in alerts page
   - **Impact:** No standalone enrichment controls

8. **Notification Management** (`/api/notifications`)
   - **APIs:** Channel management, test notifications
   - **Status:** Settings page exists
   - **Impact:** Partial coverage

9. **Secret Management** (`/api/secrets`)
   - **APIs:** CRUD for secrets
   - **Status:** Admin secrets page exists
   - **Impact:** Adequate coverage

10. **Marketplace Features** (Partial)
    - **APIs:** Categories, reviews
    - **Status:** Marketplace page exists
    - **Impact:** May lack category browsing and reviews

#### Low Priority Gaps

11. **WebSocket Statistics** (`/api/websocket/ws/stats`)
    - **APIs:** WebSocket connection stats
    - **Status:** No UI needed (operational)
    - **Impact:** Minimal

12. **Health Check Endpoints** (`/api/health/*`)
    - **APIs:** Various health checks
    - **Status:** Admin health page exists
    - **Impact:** Adequate coverage

### 5.2 Frontend Pages WITH Limited Backend Integration

The following frontend pages may have limited backend integration:

1. **Reports (`/reports`)**
   - **Status:** Page exists, basic export API available
   - **Gap:** May lack comprehensive report generation UI
   - **Recommendation:** Enhance with template management and scheduling

2. **Threat Hunting (`/threat-hunting`)**
   - **Status:** Page exists, API available
   - **Gap:** May lack hypothesis management UI
   - **Recommendation:** Add hypothesis CRUD interface

3. **Marketplace (`/marketplace`)**
   - **Status:** Page exists, extensive API
   - **Gap:** May lack category browsing and review features
   - **Recommendation:** Add category filtering and review submission

4. **Cloud Native (`/cloud-native`)**
   - **Status:** Page exists, comprehensive API
   - **Gap:** May not expose all cloud provider features
   - **Recommendation:** Add provider-specific views

5. **Settings Pages**
   - **Status:** Multiple settings pages exist
   - **Gap:** May lack granular controls for all settings
   - **Recommendation:** Audit settings coverage

### 5.3 Overbuilt Backend (APIs Beyond Frontend Needs)

The following backend areas may have more API depth than frontend utilizes:

1. **Playbook Engine**
   - **Backend:** 15+ endpoints for comprehensive management
   - **Frontend:** Basic playbook listing and execution
   - **Gap:** Advanced debugging, node inspection, version management
   - **Opportunity:** Enhanced playbook development UI

2. **Alert Lifecycle**
   - **Backend:** 10+ endpoints for full lifecycle
   - **Frontend:** Basic alert list and details
   - **Gap:** Assignment workflows, escalation chains, batch operations
   - **Opportunity:** Advanced case management UI

3. **Correlation Engine**
   - **Backend:** Sophisticated rule engine and incident management
   - **Frontend:** Basic incident view
   - **Gap:** Rule builder, incident timeline, root cause visualization
   - **Opportunity:** Dedicated investigation UI

4. **Threat Intelligence**
   - **Backend:** Multiple intel sources and caching
   - **Frontend:** Basic dashboard
   - **Gap:** IOC submission, cache management, bulk lookups
   - **Opportunity:** Enhanced TI operations center

---

## 6. Recommendations

### 6.1 Immediate Priorities (P0)

1. **Create AI Task Management Page**
   - Route: `/ai-tasks`
   - Features: Task list, status monitoring, cancellation
   - APIs to integrate: `/ai-tasks/*`
   - Effort: 2-3 days

2. **Enhance Alerts Page with Lifecycle**
   - Add assignment, escalation, resolution workflows
   - Integrate batch operations
   - APIs to integrate: `/api/v1/alerts/lifecycle/*`
   - Effort: 3-5 days

3. **Create Correlation Rule Builder**
   - Route: `/correlation/rules`
   - Features: Rule CRUD, testing, enable/disable
   - APIs to integrate: `/api/correlation/rules`
   - Effort: 5-7 days

### 6.2 Short-term Priorities (P1)

4. **Create Export Center**
   - Route: `/export` or integrate into settings
   - Features: Alert history, audit logs, playbook runs export
   - APIs to integrate: `/api/export/*`
   - Effort: 2-3 days

5. **Enhance Marketplace with Categories and Reviews**
   - Add category browsing
   - Implement review submission and viewing
   - APIs to integrate: `/api/marketplace/categories`, `/reviews`
   - Effort: 3-4 days

6. **Create System Dashboard**
   - Route: `/admin/dashboard` or enhance existing
   - Features: Full system overview, stats, health
   - APIs to integrate: `/api/system-dashboard/*`
   - Effort: 4-5 days

### 6.3 Medium-term Priorities (P2)

7. **Enhance Threat Hunting UI**
   - Add hypothesis management
   - Implement saved hunt queries
   - APIs to integrate: `/api/threat-hunting/hypotheses`
   - Effort: 3-4 days

8. **Create AI Model Management Interface**
   - Route: `/settings/ai-models`
   - Features: Model listing, testing, default selection
   - APIs to integrate: `/api/ai/models`
   - Effort: 2-3 days

9. **Enhance Cloud Native Page**
   - Add provider-specific views
   - Implement compliance reporting
   - APIs to integrate: `/api/cloud-native/*`
   - Effort: 5-7 days

### 6.4 Long-term Enhancements (P3)

10. **Advanced Playbook Development UI**
    - Visual DAG editor
    - Node-level debugging
    - Version comparison
    - APIs to integrate: `/api/playbooks/runs/{run_id}/nodes`
    - Effort: 10-15 days

11. **Investigation Case Management**
    - Case creation and linking
    - Evidence collection
    - Collaboration features
    - APIs to integrate: Alert lifecycle APIs
    - Effort: 10-15 days

12. **Threat Intelligence Operations Center**
    - IOC submission workflows
    - Cache management
    - Bulk operations
    - APIs to integrate: `/api/threat-intel/*`
    - Effort: 5-7 days

---

## 7. Technical Debt & Improvement Opportunities

### 7.1 API Design Issues

1. **Inconsistent Response Formats**
   - Some APIs return `{"items": [], "total": n}`
   - Others return direct arrays or different formats
   - **Recommendation:** Standardize pagination response format

2. **Mixed Language Comments**
   - Some files have Chinese comments (`alerts_lifecycle.py`)
   - **Recommendation:** Standardize on English for consistency

3. **Route Prefix Inconsistency**
   - Some routes use `/api/v1/`, others `/api/`, some no prefix
   - **Recommendation:** Establish consistent versioning strategy

### 7.2 Frontend Architecture

1. **Page Structure**
   - All pages under `[locale]` for i18n
   - **Status:** Good architecture for internationalization
   - **Opportunity:** Add language switcher if not present

2. **Component Organization**
   - Components directory exists but needs audit
   - **Recommendation:** Map components to page usage

### 7.3 Service Layer

1. **Service Granularity**
   - Some services may be too large (e.g., `ai_service_enhanced.py`)
   - **Recommendation:** Consider splitting large services

2. **Circular Dependencies**
    - Watch for circular imports between services
    - **Recommendation:** Use dependency injection patterns

### 7.4 Data Model Consistency

1. **Multi-tenancy Support**
   - `tenant_mixin.py` exists
   - **Status:** Need to verify consistent implementation
   - **Recommendation:** Audit all models for tenant support

2. **Soft Delete Patterns**
   - Some models use `is_active`, others use hard deletes
   - **Recommendation:** Standardize approach

---

## 8. Summary Metrics

| Category | Count |
|----------|-------|
| Backend Router Files | 37 |
| API Endpoints (approximate) | 200+ |
| Frontend Pages | 28 |
| Backend Service Files | 55+ |
| Data Models | 28 |
| Missing Frontend Pages (High Priority) | 5 |
| Partial Implementations | 5 |

---

## 9. API Endpoint Summary by Category

| Category | Endpoint Count | Frontend Coverage |
|----------|---------------|-------------------|
| Alert Management | 15 | 80% |
| AI/ML | 12 | 60% |
| Authentication | 6 | 100% |
| User Management | 7 | 90% |
| API Keys | 5 | 100% |
| Assets | 6 | 100% |
| Audit | 4 | 90% |
| Playbooks | 10 | 70% |
| Triggers | 10 | 80% |
| Threat Intel | 8 | 70% |
| Threat Hunting | 5 | 70% |
| UEBA | 5 | 60% |
| Correlation | 10 | 50% |
| Cloud Native | 6 | 40% |
| Dify Integration | 11 | 70% |
| Marketplace | 10 | 60% |
| Monitoring | 6 | 80% |
| Health Checks | 6 | 90% |
| Wazuh Integration | 11 | 70% |
| Settings | 8 | 80% |
| Reports | 2 | 50% |
| Export | 3 | 0% |
| System Dashboard | 3 | 40% |
| WebSocket/Real-time | 2 | 50% |
| **Total** | **~170** | **~70%** |

---

## 10. Conclusion

The SOC Copilot platform demonstrates a robust backend with comprehensive API coverage across security operations, AI/ML capabilities, and integrations. The frontend provides good coverage of core features but has gaps in:

1. **Task and job monitoring** (AI tasks, playbook runs)
2. **Advanced configuration** (correlation rules, models)
3. **Data export and reporting**
4. **Comprehensive system monitoring**

The platform is well-architected with clear separation between routes, services, and models. Priority areas for frontend development align with operational needs:

- **Immediate:** AI task monitoring, alert lifecycle workflows
- **Short-term:** Export capabilities, rule builders
- **Medium-term:** Enhanced marketplace, model management
- **Long-term:** Advanced playbook development, case management

This audit provides a roadmap for systematic frontend development to match the comprehensive backend capabilities.
