# SOC Copilot - Complete API Endpoint Reference

**Companion document to COMPREHENSIVE_API_AUDIT.md**
**Generated:** 2026-02-25

---

## Quick Reference Table

| API Endpoint                                             | Method | Frontend Page             | Status      |
| -------------------------------------------------------- | ------ | ------------------------- | ----------- |
| **Authentication & Users**                               |
| `/api/auth/register`                                     | POST   | `/login`                  | ✅ Complete |
| `/api/auth/login`                                        | POST   | `/login`                  | ✅ Complete |
| `/api/auth/logout`                                       | POST   | `/login`                  | ✅ Complete |
| `/api/auth/refresh`                                      | POST   | `/login`                  | ✅ Complete |
| `/api/auth/me`                                           | GET    | Multiple                  | ✅ Complete |
| `/api/users`                                             | GET    | `/admin/users`            | ✅ Complete |
| `/api/users/{user_id}`                                   | GET    | `/admin/users`            | ✅ Complete |
| `/api/users`                                             | POST   | `/admin/users`            | ✅ Complete |
| `/api/users/{user_id}`                                   | PATCH  | `/admin/users`            | ✅ Complete |
| `/api/users/{user_id}`                                   | DELETE | `/admin/users`            | ✅ Complete |
| `/api/users/{user_id}/reset-password`                    | POST   | `/admin/users`            | ✅ Complete |
| `/api/unlock-user/{username}`                            | POST   | `/admin/users`            | ✅ Complete |
| **Alerts & Security Events**                             |
| `/api/analyze-alert`                                     | POST   | `/alerts`                 | ✅ Complete |
| `/api/v1/alerts`                                         | GET    | `/alerts`                 | ✅ Complete |
| `/api/v1/alerts/{alert_id}`                              | GET    | `/alerts/[id]`            | ✅ Complete |
| `/api/v1/alerts`                                         | POST   | `/alerts`                 | ✅ Complete |
| `/api/v1/alerts/{alert_id}`                              | PATCH  | `/alerts/[id]`            | ✅ Complete |
| `/api/v1/alerts/{alert_id}`                              | DELETE | `/alerts/[id]`            | ✅ Complete |
| `/api/v1/alerts/stats/summary`                           | GET    | `/alerts`                 | ✅ Complete |
| `/api/v1/alerts/alerts`                                  | POST   | `/alerts`                 | ✅ Complete |
| `/api/v1/alerts/{alert_id}/lifecycle`                    | GET    | `/alerts/[id]`            | ✅ Complete |
| `/api/v1/alerts/{alert_id}/status`                       | PATCH  | `/alerts/[id]`            | ⚠️ Partial  |
| `/api/v1/alerts/{alert_id}/assign`                       | POST   | `/alerts/[id]`            | ⚠️ Partial  |
| `/api/v1/alerts/{alert_id}/resolve`                      | POST   | `/alerts/[id]`            | ⚠️ Partial  |
| `/api/v1/alerts/{alert_id}/escalate`                     | POST   | `/alerts/[id]`            | ⚠️ Partial  |
| `/api/v1/alerts/{alert_id}/notes`                        | POST   | `/alerts/[id]`            | ⚠️ Partial  |
| `/api/v1/alerts/batch/update`                            | POST   | `/alerts`                 | ❌ Missing  |
| `/api/v1/alerts/statistics/summary`                      | GET    | `/alerts`                 | ✅ Complete |
| `/api/v1/alerts/statistics/trends`                       | GET    | `/alerts`                 | ✅ Complete |
| `/api/v1/alerts/statistics/top-threats`                  | GET    | `/alerts`                 | ✅ Complete |
| `/api/v1/alerts/statistics/threat-intel`                 | GET    | `/alerts`                 | ✅ Complete |
| **AI & Machine Learning**                                |
| `/api/ai/analyze-alert`                                  | POST   | `/ai-assistant`           | ✅ Complete |
| `/api/ai/query`                                          | POST   | `/ai-assistant`           | ✅ Complete |
| `/api/ai/recommend-playbooks`                            | POST   | `/ai-assistant`           | ✅ Complete |
| `/api/ai/chat`                                           | POST   | `/ai-assistant`           | ✅ Complete |
| `/api/ai/generate-report`                                | POST   | `/ai-assistant`           | ✅ Complete |
| `/api/ai/status`                                         | GET    | `/ai-assistant`           | ✅ Complete |
| `/api/ai/models`                                         | GET    | `/ai-assistant`           | ⚠️ Partial  |
| `/api/ai/models/default`                                 | GET    | `/ai-assistant`           | ⚠️ Partial  |
| `/api/ai/models/default`                                 | POST   | `/ai-assistant`           | ⚠️ Partial  |
| `/api/ai/models/test`                                    | POST   | `/ai-assistant`           | ⚠️ Partial  |
| `/api/ai/models/refresh`                                 | POST   | `/ai-assistant`           | ⚠️ Partial  |
| `/ai-tasks/submit`                                       | POST   | ❌ None                   | ❌ Missing  |
| `/ai-tasks/{task_id}/status`                             | GET    | ❌ None                   | ❌ Missing  |
| `/ai-tasks/{task_id}/result`                             | GET    | ❌ None                   | ❌ Missing  |
| `/ai-tasks/{task_id}/cancel`                             | POST   | ❌ None                   | ❌ Missing  |
| `/ai-tasks`                                              | GET    | ❌ None                   | ❌ Missing  |
| `/ai-tasks/types`                                        | GET    | ❌ None                   | ❌ Missing  |
| **Assets**                                               |
| `/api/assets`                                            | GET    | `/assets`                 | ✅ Complete |
| `/api/assets`                                            | POST   | `/assets`                 | ✅ Complete |
| `/api/assets/import`                                     | POST   | `/assets`                 | ✅ Complete |
| `/api/assets/{asset_id}`                                 | GET    | `/assets`                 | ✅ Complete |
| `/api/assets/{asset_id}`                                 | PATCH  | `/assets`                 | ✅ Complete |
| `/api/assets/{asset_id}`                                 | DELETE | `/assets`                 | ✅ Complete |
| **API Keys**                                             |
| `/api/api-keys`                                          | GET    | `/settings/api-keys`      | ✅ Complete |
| `/api/api-keys`                                          | POST   | `/settings/api-keys`      | ✅ Complete |
| `/api/api-keys/{api_key_id}`                             | PATCH  | `/settings/api-keys`      | ✅ Complete |
| `/api/api-keys/{api_key_id}`                             | DELETE | `/settings/api-keys`      | ✅ Complete |
| `/api/api-keys/admin/all`                                | GET    | `/admin/users`            | ✅ Complete |
| **Audit & Compliance**                                   |
| `/api/audit-logs`                                        | GET    | `/audit`                  | ✅ Complete |
| `/api/audit-logs/stats/summary`                          | GET    | `/audit`                  | ✅ Complete |
| `/api/audit-logs/target/{target_type}/{target_id}`       | GET    | `/audit`                  | ✅ Complete |
| `/api/audit-logs/cleanup`                                | POST   | `/admin/audit`            | ✅ Complete |
| **Playbooks & Automation**                               |
| `/api/playbooks`                                         | GET    | `/playbooks`              | ✅ Complete |
| `/api/playbooks/{definition_id}`                         | GET    | `/playbooks`              | ✅ Complete |
| `/api/playbooks`                                         | POST   | `/playbooks`              | ✅ Complete |
| `/api/playbooks/{definition_id}`                         | PATCH  | `/playbooks`              | ✅ Complete |
| `/api/playbooks/{definition_id}`                         | DELETE | `/playbooks`              | ✅ Complete |
| `/api/playbooks/{definition_id}/execute`                 | POST   | `/playbooks`              | ✅ Complete |
| `/api/playbooks/runs/{run_id}`                           | GET    | `/playbooks`              | ✅ Complete |
| `/api/playbooks/runs/{run_id}/nodes`                     | GET    | `/playbooks`              | ⚠️ Partial  |
| `/api/playbooks/runs/{run_id}/cancel`                    | POST   | `/playbooks`              | ✅ Complete |
| **Triggers**                                             |
| `/api/triggers`                                          | GET    | `/triggers`               | ✅ Complete |
| `/api/triggers/{trigger_id}`                             | GET    | `/triggers`               | ✅ Complete |
| `/api/triggers`                                          | POST   | `/triggers`               | ✅ Complete |
| `/api/triggers/cron`                                     | POST   | `/triggers/cron/new`      | ✅ Complete |
| `/api/triggers/webhook`                                  | POST   | `/triggers/webhook/new`   | ✅ Complete |
| `/api/triggers/{trigger_id}`                             | PUT    | `/triggers`               | ✅ Complete |
| `/api/triggers/{trigger_id}`                             | DELETE | `/triggers`               | ✅ Complete |
| `/api/triggers/{trigger_id}/test`                        | POST   | `/triggers`               | ✅ Complete |
| `/api/triggers/{trigger_id}/invocations`                 | GET    | `/triggers`               | ⚠️ Partial  |
| `/api/triggers/{trigger_id}/webhook/regenerate-secret`   | POST   | `/triggers`               | ⚠️ Partial  |
| **Threat Intelligence**                                  |
| `/api/threat-intel/otx`                                  | GET    | `/threat-intel`           | ✅ Complete |
| `/api/threat-intel/otx/bulk`                             | POST   | `/threat-intel`           | ✅ Complete |
| `/api/threat-intel/manual`                               | POST   | `/threat-intel`           | ✅ Complete |
| `/api/threat-intel`                                      | GET    | `/threat-intel`           | ✅ Complete |
| `/api/threat-intel/cache/{ioc_type}/{ioc_value}`         | DELETE | `/threat-intel`           | ⚠️ Partial  |
| `/api/threat-intel/cache/expired`                        | DELETE | `/threat-intel`           | ⚠️ Partial  |
| `/api/threat-intel/cache/all`                            | DELETE | `/threat-intel`           | ⚠️ Partial  |
| `/api/ioc-hits`                                          | GET    | `/threat-intel`           | ✅ Complete |
| `/api/ioc-hits/by-asset/{asset_id}`                      | GET    | `/threat-intel`           | ✅ Complete |
| `/api/ioc-hits/by-history/{history_id}`                  | GET    | `/threat-intel`           | ✅ Complete |
| **Threat Hunting**                                       |
| `/api/threat-hunting/execute`                            | POST   | `/threat-hunting`         | ✅ Complete |
| `/api/threat-hunting/hypotheses`                         | GET    | `/threat-hunting`         | ⚠️ Partial  |
| `/api/threat-hunting/hypotheses`                         | POST   | `/threat-hunting`         | ⚠️ Partial  |
| `/api/threat-hunting/ioc-hunt`                           | POST   | `/threat-hunting`         | ✅ Complete |
| `/api/threat-hunting/trending`                           | GET    | `/threat-hunting`         | ✅ Complete |
| **UEBA**                                                 |
| `/api/ueba`                                              | GET    | `/ueba`                   | ✅ Complete |
| `/api/ueba/risk-profile/{user_id}`                       | GET    | `/ueba`                   | ✅ Complete |
| `/api/ueba/high-risk-users`                              | GET    | `/ueba`                   | ✅ Complete |
| `/api/ueba/detect`                                       | POST   | `/ueba`                   | ✅ Complete |
| `/api/ueba/build-baseline`                               | POST   | `/ueba`                   | ✅ Complete |
| **Event Correlation**                                    |
| `/api/correlation/correlate`                             | POST   | `/correlation`            | ✅ Complete |
| `/api/correlation/incidents`                             | GET    | `/correlation`            | ✅ Complete |
| `/api/correlation/incidents/{incident_id}`               | GET    | `/correlation`            | ✅ Complete |
| `/api/correlation/incidents/{incident_id}/status`        | PUT    | `/correlation`            | ✅ Complete |
| `/api/correlation/rules`                                 | GET    | ❌ None                   | ❌ Missing  |
| `/api/correlation/rules`                                 | POST   | ❌ None                   | ❌ Missing  |
| `/api/correlation/rules/{rule_id}`                       | PUT    | ❌ None                   | ❌ Missing  |
| `/api/correlation/rules/{rule_id}`                       | DELETE | ❌ None                   | ❌ Missing  |
| `/api/correlation/rules/{rule_id}/toggle`                | POST   | ❌ None                   | ❌ Missing  |
| **Cloud Native Security**                                |
| `/api/cloud-native`                                      | GET    | `/cloud-native`           | ✅ Complete |
| `/api/cloud-native/cloud/connections`                    | GET    | `/cloud-native`           | ⚠️ Partial  |
| `/api/cloud-native/kubernetes/resources/{resource_type}` | GET    | `/cloud-native`           | ⚠️ Partial  |
| `/api/cloud-native/containers/scan`                      | POST   | `/cloud-native`           | ⚠️ Partial  |
| `/api/cloud-native/kubernetes/scan`                      | POST   | `/cloud-native`           | ⚠️ Partial  |
| `/api/cloud-native/compliance/report`                    | GET    | `/cloud-native`           | ⚠️ Partial  |
| **Dify Integration**                                     |
| `/api/dify/workflows`                                    | GET    | `/dify`                   | ✅ Complete |
| `/api/dify/workflows/{app_id}`                           | GET    | `/dify`                   | ✅ Complete |
| `/api/dify/workflows/{app_id}/execute`                   | POST   | `/dify`                   | ✅ Complete |
| `/api/dify/workflows/{app_id}/import`                    | POST   | `/dify`                   | ✅ Complete |
| `/api/dify/workflows/sync/{definition_id}`               | POST   | `/dify`                   | ✅ Complete |
| `/api/dify/playbooks/{playbook_id}/download`             | POST   | `/dify`                   | ✅ Complete |
| `/api/dify/playbooks`                                    | GET    | `/dify`                   | ✅ Complete |
| `/api/dify/playbooks/{playbook_id}`                      | GET    | `/dify`                   | ✅ Complete |
| `/api/dify/playbooks/{playbook_id}/reviews`              | POST   | `/dify`                   | ⚠️ Partial  |
| `/api/dify/playbooks/{playbook_id}/reviews`              | GET    | `/dify`                   | ⚠️ Partial  |
| `/api/dify/integration/status`                           | GET    | `/dify`                   | ✅ Complete |
| `/api/dify/test-connection`                              | GET    | `/dify`                   | ✅ Complete |
| **Marketplace**                                          |
| `/api/marketplace/featured`                              | GET    | `/marketplace`            | ✅ Complete |
| `/api/marketplace/categories`                            | GET    | `/marketplace`            | ⚠️ Partial  |
| `/api/marketplace/workflows`                             | GET    | `/marketplace`            | ✅ Complete |
| `/api/marketplace/workflows/{app_id}`                    | GET    | `/marketplace`            | ✅ Complete |
| `/api/marketplace/workflows/{app_id}/import`             | POST   | `/marketplace`            | ✅ Complete |
| **Monitoring & Health**                                  |
| `/api/monitor/dashboard`                                 | GET    | `/monitor`                | ✅ Complete |
| `/api/monitor/metrics`                                   | GET    | `/monitor`                | ✅ Complete |
| `/api/monitor/history`                                   | GET    | `/monitor`                | ✅ Complete |
| `/api/monitor/history/clear`                             | DELETE | `/monitor`                | ✅ Complete |
| `/api/monitor/history/cleanup`                           | DELETE | `/monitor`                | ✅ Complete |
| `/api/monitor/process-recent`                            | POST   | `/monitor`                | ✅ Complete |
| `/api/health`                                            | GET    | `/admin/health`           | ✅ Complete |
| `/api/health/live`                                       | GET    | `/admin/health`           | ✅ Complete |
| `/api/health/ready`                                      | GET    | `/admin/health`           | ✅ Complete |
| `/api/health/database`                                   | GET    | `/admin/health`           | ✅ Complete |
| `/api/health/redis`                                      | GET    | `/admin/health`           | ✅ Complete |
| `/api/health/resources`                                  | GET    | `/admin/health`           | ✅ Complete |
| **Wazuh Integration**                                    |
| `/api/wazuh/health`                                      | GET    | `/wazuh`                  | ✅ Complete |
| `/api/wazuh/agents`                                      | GET    | `/wazuh`                  | ✅ Complete |
| `/api/wazuh/agents/{agent_id}`                           | GET    | `/wazuh`                  | ✅ Complete |
| `/api/wazuh/alerts/summary`                              | GET    | `/wazuh`                  | ✅ Complete |
| `/api/wazuh/ingest`                                      | POST   | `/wazuh`                  | ✅ Complete |
| `/api/wazuh/queue-stats`                                 | GET    | `/wazuh`                  | ⚠️ Partial  |
| `/api/wazuh/receiver/configure`                          | POST   | `/wazuh`                  | ⚠️ Partial  |
| `/api/wazuh/receiver/start`                              | POST   | `/wazuh`                  | ⚠️ Partial  |
| `/api/wazuh/receiver/stop`                               | POST   | `/wazuh`                  | ⚠️ Partial  |
| `/api/wazuh/receiver/restart`                            | POST   | `/wazuh`                  | ⚠️ Partial  |
| `/api/wazuh/receiver/stats`                              | GET    | `/wazuh`                  | ⚠️ Partial  |
| `/api/wazuh/webhook`                                     | POST   | Internal                  | ✅ Complete |
| **Settings & Configuration**                             |
| `/api/admin/settings`                                    | GET    | `/admin/settings`         | ✅ Complete |
| `/api/admin/settings`                                    | POST   | `/admin/settings`         | ✅ Complete |
| `/api/admin/settings/timeouts`                           | GET    | `/admin/settings`         | ✅ Complete |
| `/api/secrets`                                           | GET    | `/admin/secrets`          | ✅ Complete |
| `/api/secrets/config`                                    | GET    | `/admin/secrets`          | ✅ Complete |
| `/api/secrets/{secret_name}`                             | GET    | `/admin/secrets`          | ✅ Complete |
| `/api/secrets`                                           | POST   | `/admin/secrets`          | ✅ Complete |
| `/api/secrets/{secret_name}`                             | PATCH  | `/admin/secrets`          | ✅ Complete |
| `/api/secrets/{secret_name}`                             | DELETE | `/admin/secrets`          | ✅ Complete |
| `/api/secrets/key-status`                                | GET    | `/admin/secrets`          | ✅ Complete |
| **Timeline & History**                                   |
| `/api/timeline/build-timeline`                           | POST   | `/alerts/[id]`            | ✅ Complete |
| `/api/timeline/health`                                   | GET    | `/admin/health`           | ✅ Complete |
| `/api/history`                                           | GET    | Various                   | ✅ Complete |
| `/api/history`                                           | POST   | Various                   | ✅ Complete |
| `/api/history/{history_id}`                              | GET    | Various                   | ✅ Complete |
| `/api/history/{history_id}`                              | DELETE | Various                   | ✅ Complete |
| **Reports & Export**                                     |
| `/api/report/generate-report`                            | POST   | `/reports`                | ✅ Complete |
| `/api/export/alerts`                                     | GET    | ❌ None                   | ❌ Missing  |
| `/api/export/audit-logs`                                 | GET    | ❌ None                   | ❌ Missing  |
| `/api/export/playbook-runs`                              | GET    | ❌ None                   | ❌ Missing  |
| **Alert Enrichment**                                     |
| `/api/alert-enrichment/process/{alert_id}`               | POST   | Integrated                | ✅ Complete |
| `/api/alert-enrichment/cache/refresh`                    | POST   | `/threat-intel`           | ⚠️ Partial  |
| `/api/alert-enrichment/test-alert`                       | POST   | `/threat-intel`           | ⚠️ Partial  |
| **System Dashboard**                                     |
| `/api/system-dashboard/dashboard`                        | GET    | `/admin/health`           | ⚠️ Partial  |
| `/api/system-dashboard/stats/summary`                    | GET    | `/`                       | ⚠️ Partial  |
| `/api/system-dashboard/features`                         | GET    | `/`                       | ⚠️ Partial  |
| **WebSocket & Notifications**                            |
| `/api/websocket/ws/alerts`                               | WS     | Various                   | ✅ Complete |
| `/api/websocket/ws/stats`                                | GET    | `/admin/health`           | ⚠️ Partial  |
| `/api/notifications/channels`                            | GET    | `/settings/notifications` | ✅ Complete |
| `/api/notifications/test`                                | POST   | `/settings/notifications` | ✅ Complete |

---

## Legend

| Symbol      | Meaning                                    |
| ----------- | ------------------------------------------ |
| ✅ Complete | Fully implemented in frontend              |
| ⚠️ Partial  | Partially implemented or could be enhanced |
| ❌ Missing  | No dedicated frontend page/interface       |

---

## Gap Summary by Priority

### High Priority Gaps (No Frontend Implementation)

1. **AI Task Management** - 6 endpoints
   - `/ai-tasks/submit`
   - `/ai-tasks/{task_id}/status`
   - `/ai-tasks/{task_id}/result`
   - `/ai-tasks/{task_id}/cancel`
   - `/ai-tasks`
   - `/ai-tasks/types`

2. **Export Functionality** - 3 endpoints
   - `/api/export/alerts`
   - `/api/export/audit-logs`
   - `/api/export/playbook-runs`

3. **Correlation Rules Management** - 5 endpoints
   - `/api/correlation/rules` (GET)
   - `/api/correlation/rules` (POST)
   - `/api/correlation/rules/{rule_id}` (PUT)
   - `/api/correlation/rules/{rule_id}` (DELETE)
   - `/api/correlation/rules/{rule_id}/toggle`

### Medium Priority Gaps (Partial Implementation)

4. **AI Models Management** - 4 endpoints
   - Integrated in AI Assistant but no dedicated interface

5. **Alert Lifecycle Workflows** - 5 endpoints
   - Basic status updates exist, but missing assignment/escalation UI

6. **Marketplace Features** - 2 endpoints
   - Categories and reviews need UI enhancement

7. **Cloud Native Security** - 4 endpoints
   - Page exists but provider-specific features not fully exposed

8. **Wazuh Advanced Features** - 6 endpoints
   - Basic integration exists, receiver controls need UI

---

## Frontend Pages Summary

| Page                      | Backend APIs Used        | Coverage |
| ------------------------- | ------------------------ | -------- |
| `/`                       | System dashboard, stats  | 70%      |
| `/login`                  | Auth endpoints           | 100%     |
| `/ai-assistant`           | AI chat, models          | 80%      |
| `/alerts`                 | Alert CRUD, lifecycle    | 85%      |
| `/alerts/[id]`            | Alert details, lifecycle | 80%      |
| `/assets`                 | Asset CRUD               | 100%     |
| `/audit`                  | Audit logs               | 100%     |
| `/correlation`            | Incidents                | 60%      |
| `/cloud-native`           | Cloud security           | 50%      |
| `/dify`                   | Dify workflows           | 90%      |
| `/marketplace`            | Marketplace              | 75%      |
| `/monitor`                | Monitoring               | 90%      |
| `/playbooks`              | Playbook definitions     | 75%      |
| `/reports`                | Report generation        | 60%      |
| `/settings`               | User settings            | 80%      |
| `/settings/api-keys`      | API keys                 | 100%     |
| `/settings/notifications` | Notifications            | 80%      |
| `/threat-hunting`         | Hunting operations       | 80%      |
| `/threat-intel`           | Threat intel             | 85%      |
| `/threat-intel/dashboard` | TI dashboard             | 90%      |
| `/triggers`               | Trigger management       | 85%      |
| `/triggers/cron/new`      | Cron creation            | 100%     |
| `/triggers/webhook/new`   | Webhook creation         | 100%     |
| `/ueba`                   | Behavior analytics       | 80%      |
| `/wazuh`                  | Wazuh integration        | 70%      |
| `/admin/settings`         | Admin settings           | 100%     |
| `/admin/users`            | User management          | 100%     |
| `/admin/secrets`          | Secrets                  | 100%     |
| `/admin/audit`            | Admin audit              | 100%     |
| `/admin/health`           | Health monitoring        | 100%     |

---

## Implementation Recommendations

### Quick Wins (1-2 days each)

1. **Add export buttons to existing pages**
   - Add export functionality to Alerts, Audit, and Playbooks pages
   - Reuse existing `/api/export/*` endpoints

2. **Create AI Tasks page**
   - Simple table view of tasks
   - Status polling and cancellation
   - Use existing `/ai-tasks/*` endpoints

3. **Add lifecycle action buttons to Alert details**
   - Assign, Escalate, Resolve buttons
   - Use existing `/api/v1/alerts/{alert_id}/*` endpoints

### Medium Effort (3-5 days each)

4. **Create Correlation Rules page**
   - Rule builder interface
   - Rule list and testing
   - Use existing `/api/correlation/rules` endpoints

5. **Enhance Marketplace**
   - Add category filtering
   - Add review submission and viewing
   - Use existing `/api/marketplace/*` endpoints

6. **Create Model Management page**
   - Model listing and testing
   - Default model selection
   - Use existing `/api/ai/models` endpoints

---

## API Versioning Notes

- **Version 1 APIs:** `/api/v1/*` (Alerts lifecycle)
- **Unversioned APIs:** `/api/*` (Most current APIs)
- **Legacy APIs:** No prefix (Being phased out)

**Recommendation:** Establish consistent API versioning strategy for future development.

---

## Authentication Requirements

| API Pattern                                  | Authentication Required  |
| -------------------------------------------- | ------------------------ |
| `/api/auth/*`                                | Public (except `/me`)    |
| `/api/health/*`                              | Public                   |
| `/api/websocket/*`                           | Required after handshake |
| All other `/api/*`                           | Required                 |
| Admin endpoints (`/admin/*`, `/api/admin/*`) | Admin role required      |

---

## Rate Limiting & Throttling

Status: **Not documented in code audit**

**Recommendation:**

- Document rate limits for each endpoint
- Implement rate limiting middleware
- Add rate limit headers to responses

---

## WebSocket Endpoints

| Endpoint                   | Purpose                   | Status         |
| -------------------------- | ------------------------- | -------------- |
| `/api/websocket/ws/alerts` | Real-time alert streaming | ✅ Implemented |
| `/api/websocket/ws/stats`  | WebSocket statistics      | ⚠️ No UI       |

---

## File Upload Endpoints

Status: **Not found in audit**

**Recommendation:**

- Consider adding file upload support for:
  - IOC lists (CSV, JSON)
  - Asset imports
  - Report templates
  - Playbook exports

---

## Pagination Patterns

Most list endpoints use:

- `page` (default: 1)
- `page_size` or `limit` (default: 20-50, max: 100-500)
- Response format: `{"items": [...], "total": n}`

**Exceptions exist** - standardization recommended.

---

## Filtering & Sorting

Common patterns:

- Date ranges: `date_from`, `date_to`
- Status filters: `status`, `is_active`
- Search: `query`, `q`
- Sorting: Usually by `created_at DESC`

**Recommendation:** Document all available filters for each endpoint.

---

## Error Response Formats

Status: **Inconsistent**

Common patterns:

- `{"detail": "error message"}` (FastAPI default)
- `{"error": "error message"}`
- `{"success": false, "error": "..."}`

**Recommendation:** Standardize error response format across all endpoints.

---

## Internationalization

- Backend: Mixed English and Chinese comments
- Frontend: Full i18n support with `[locale]` routing
- **Recommendation:** Standardize all backend content to English

---

## This Document

Generated by automated scan of:

- `/Users/levent/Desktop/sec/backend/routers/` (37 files)
- `/Users/levent/Desktop/sec/frontend/app/[locale]/` (28 pages)
- `/Users/levent/Desktop/sec/backend/services/` (55+ files)
- `/Users/levent/Desktop/sec/backend/models/` (28 files)

**Last Updated:** 2026-02-25
