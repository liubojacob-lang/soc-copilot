# Changelog

All notable changes to SOC Copilot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.4] - 2026-09-19

### Security
- **Eliminate AI heuristic hallucination**: Remove fake alert triage synthesis (`_build_heuristic_alert_response`) with simulated metrics, entropy and domains; enforce honest degraded state with clear `[AI 分析不可用]` status
- **Trivy mock removal**: Disable mock vulnerability generation in `TrivyService.scan_image()`; raise `TrivyNotInstalledError` (503 `SCANNER_NOT_INSTALLED`) when scanner CLI is missing
- **Dev admin backdoor removal**: Remove hardcoded backdoor credentials in `auth_service.py`
- **Backup script hardening**: Exclude `.env*` from automated filesystem and tarball backups to prevent plaintext secret leaks; document secret exclusion by design
- **Audit middleware fix**: Prefix `/api/v1/` to login/auth exclusion paths preventing plaintext credential leaks in audit logs

### Fixed & Database
- **Database constraints (0006)**: Add UniqueConstraint on `blocked_ips (value, type)` and `trigger_invocations.idempotency_key`; add timestamp indexes on `correlated_events` and run_id index on `playbook_approvals`
- **Model exports**: Export `SecurityVulnerability` and `VulnerabilityNote` in `models.__init__` and `__all__`
- **AI triage pipeline feedback loop**: Backfill asynchronous AI triage conclusions into `alert.raw_data.pipeline.ai_triage` and extract suggested severity
- **API path alignment**: Correct broken unversioned `/api/ai/*` routes in `lib/api/ai.ts` to `/api/v1/ai/*`
- **Schema-valid degraded payload**: Degraded alert responses used invalid enum/None values that failed `AlertAnalysisResponse` validation — turning "LLM down" into an HTTP 500 instead of a graceful degraded response; placeholders are now schema-valid (severity=medium, confidence=0) and the dead re-validating fallback raises an explicit programming-error signal
- **Error redaction**: `security_alerts` ingest and `system_dashboard` terminate-connection no longer echo internal exception text to clients (logged with traceback instead)

### Added & UI
- **Frontend triage indicators**: Add "AI 已分诊" badge in alert lists and dedicated automated triage conclusions card in alert detail view
- **External TI status**: Explicitly surface `provider_status: unconfigured` when OTX is not configured, displaying alert banner in UI
- **Cases E2E test suite**: Add Playwright test coverage for security cases management flow with CI trigger workflow
- **Cloud-Native roadmap freeze**: Freeze cloud-native features with "Demo" navigation badge and roadmap documentation
- **Root cause analysis closed loop (T2.4)**: Wire the previously orphaned `root_cause_analyses` table and CoT prompt into an end-to-end flow — `POST /api/v1/alerts/{id}/root-cause-analysis` (refuses with 503 when the LLM is degraded instead of fabricating), history listing, analyst verdict feedback; new Root Cause tab on the alert detail page with reasoning/evidence/verification rendering (en/zh-CN)
- **Prompt registry runtime wiring (T3.2)**: `resolve_prompt()` consults the active registry row for the mapped environment and falls back to builtins on any miss/outage; the four runtime templates (alert analysis, auto triage, report, timeline) now resolve through it, plus an idempotent seed script into dev/staging (`make db-seed`)
- **LLM token usage metrics (T3.3)**: All six providers record `soc_llm_tokens_total{provider,model,direction}` and `soc_llm_requests_total` from API `usage` payloads that were previously discarded
- **AI task queue hardening (T3.4)**: PriorityQueue consumption honours the persisted `priority` column (FIFO within a level); startup crash recovery re-enqueues orphaned `pending` rows and fails stale `processing` rows with an explicit reason
- **Backend Sentry (T4.1)**: conditional `sentry-sdk` init when `SENTRY_DSN` is set, aligned with the frontend's release tag
- **RBAC system-role seeding (T3.6)**: idempotent startup seeding of roles/permissions/role_permissions with `is_system=True`, matching the hardcoded permission matrix

### Infrastructure
- **E2E backend URL**: `global.setup.ts` honours `E2E_BACKEND_URL` instead of assuming the backend shares the frontend host on :8000; e2e workflow triggers on `release/**` push/PR
- **Version alignment**: docker-compose `IMAGE_TAG`, k8s image tags/labels and Sentry release fallbacks unified to 0.9.4; README dead links (`MANUAL_TEST.md`/`TEST_CASES.md`) removed
- **Prod compose limits (T4.5)**: every non-profile service now carries `deploy.resources` limits (postgres 2CPU/2G, redis 1CPU/768M above its maxmemory, nginx 1CPU/512M); full render validated with all `${VAR:?}` secret gates intact
- **Coverage floor**: 47% → 50% (measured 51%)

### Removed
- Remove opaque binary `Scripts/email_validator.exe`
- Remove unused components (`QuickActions.tsx`, `authStore.ts`, `notificationStore.ts`, `MonitoringDashboard.tsx`, `FilterConfig.tsx`, `PlaceholderPage.tsx`)
- **Dead code sweep (T3.5, migration 0007)**: drop tables `event_similarities`, `on_call_schedules`, `playbook_nodes`, `playbook_edges` (zero producers/readers, downgrade recreates bare schemas); remove `kafka_broker` stub (MESSAGE_BROKER=kafka now raises a clear error), `tenant_mixin`/`tenant_query` (multi-tenant prep with no adopters), unmounted `IdempotencyMiddleware`, zero-caller resource-ownership helpers, sigma engine's fabricated-event generator, 7 never-collected backend-root test files, legacy `backend/migrations/` SQL and stray server logs

## [0.9.3] - 2026-09-13


### Added
- **TOTP two-factor authentication** (RFC 6238): enroll/verify/disable, backup codes and a sudo-mode policy, so sensitive operations can require a second factor without forcing it on every login
- Short-lived `pre_2fa` token (5 min) for the login challenge and `sudo` token (10 min) for sensitive operations
- Migration `0005_user_2fa_totp`: `users` gains `totp_secret`, `is_totp_enabled`, `totp_policy`, `totp_backup_codes`
- Frontend `OtpInput` component, settings 2FA panel and en/zh-CN catalogs
- `get_bulk_counts` on the case repository: per-case alert and comment counts collapse from N+1 into 2 queries
- Test suites for the playbook DAG, RBAC dependencies and the MISP/Trivy/VirusTotal clients

### Fixed
- **Secret leak**: `.gitignore` matches `.env.*` instead of enumerating names, closing the `.env.local-sim` gap (example templates stay whitelisted)
- Cookie `Secure` flag is driven by the new `cookie_secure` setting (None = auto: on in production, off in development)
- Timezone-aware timestamps: `history`, `ioc_hit` and `correlated_event` default to `datetime.now(UTC)`, and the dashboard derives its day boundary from the column's own tz-awareness
- Account lockout parses `locked_until` as a datetime and reports the remaining minutes
- Playbook DAG sends PENDING nodes through QUEUED before RUNNING
- WebSocket manager tells "redis not supplied" apart from an explicit `None`, so pubsub no longer degrades silently
- Lint gate restored: 4 ruff findings (F401/UP017) in `services/auth_service.py` cleared

### Changed
- Data-retention cleanup is composed from a job table and deletes child rows before parents
- Coverage floor raised 30% → 47% (measured 49.6%)
- Frontend: shared layout/header/timeline/navigation components, `UserMenu` extracted, design tokens consolidated in `tailwind.config.ts` against a committed baseline
- AI assistant streams over real SSE with a fallback to the previous behaviour

### Removed
- `workers/alert_consumer.py`, unused alert components and the `/test` page (dead code)

## [0.9.2] - 2026-09-08

### Fixed
- **Assets**: create/update/delete never committed the session (phantom writes — 201 responses whose rows vanished); legacy plain-text tags 500'd the list endpoint for all users
- **Cases**: creation returned 500 (lazy-load `MissingGreenlet`) and all ten write paths silently rolled back
- **Broken pages**: approvals inbox called a nonexistent route; report generation died on a missing `GET /api/alerts/{id}`; alert import had no backend at all (new `POST /api/alerts/import[/batch][/preview]`)
- **RBAC regression**: any authenticated user could trigger `/ai/models/refresh` and wipe the model catalog (admin check restored)
- **Model seeding**: startup seed no longer DELETEs admin-created custom models; user defaults only reset when the referenced model is gone
- **ai-tasks**: router 500'd at runtime (dict-typed `current_user`); task status/result/cancel now enforce per-user ownership

### Security
- JWT access lifetime default 720 → 60 minutes
- Server-side page gate in `proxy.ts` (anonymous visitors redirected before page HTML is served)
- AI chat: input cap (20k chars), per-IP rate limits on all AI endpoints, `role:"system"` injection blocked, real SSE streaming
- Audit-log listing restricted to owner/admin/auditor (was any authenticated user)
- Secrets governance: full credentials removed from docs; test script credentials moved to env vars; git history contains legacy blobs (rotate values; scrub before external exposure)
- HTTP request node pins SSRF-validated addresses at connect time (DNS rebinding closed)

### Added
- Forced password change flow for flagged accounts (frontend + login interception)
- Alert import API (CEF/Syslog/JSON/CSV) with idempotent content-hash dedup
- RBAC matrix, assets, and cases integration test suites (419+ backend tests, 43.9% coverage)
- Backup/restore: `make db-backup` / `make db-restore FILE=`, k8s backup CronJob, deploy.sh fixes, certbot service, k8s alert-worker manifest, monitoring provisioning mounts
- PROJECT_FINAL_AUDIT.md + FUTURE_BACKLOG.md acceptance documents

## [0.9.0] - 2026-04-13

### Added

- **Marketplace DB Persistence**: Playbook marketplace now persists data to PostgreSQL with full CRUD, search, approval workflow, and user reviews (replaces in-memory hardcoded data)
- **Security Headers Middleware**: CSP, X-Frame-Options, HSTS, X-Content-Type-Options, and API-specific security headers
- **Frontend Unit Tests**: 8 new test files (Button, Card, Input, LoadingSpinner, useRetryFetch, useAutoSave, usePermission, useIsClient)
- **E2E Test Suite**: 30+ new Playwright test cases for dashboard, marketplace admin, i18n locale switching, and security headers validation
- **Phase 2 - AI Copilot**: AI chat assistant, threat investigation workflow, anomaly detection UI
- **Phase 3 - Advanced Analytics**: UEBA dashboard, risk scoring, compliance reporting pages
- **Phase 4 - Ecosystem & Cloud Native**: Cloud integration, API gateway, multi-tenant scaffolding

### Changed

- **Version Unification**: All version references (backend, frontend, docs) aligned to v0.9.0
- **Roadmap Updated**: Reflects 2026 timeline and current feature status

### Fixed

- **Alert Stream Filtering**: WebSocket subscriptions now correctly filter alerts per-client based on severity/type/source criteria (previously stored but ignored)
- **AI Chat conversation_id**: Changed from user message content to proper UUID
- **datetime.utcnow() deprecation**: Replaced with `datetime.now(UTC)` across backend
- **Frontend import**: Fixed `require()` usage in `useAIChat.ts` to proper ES import
- **Test alert count**: Limited test-alert endpoint to prevent flooding

### Refactored

- **Backend Cleanup**: 390 files reorganized, 14 deprecated test files archived to `_archived/`
- **Frontend Cleanup**: 253 files reformatted and optimized
- **Infrastructure**: Documentation reorganized, CI/CD pipeline setup

## [0.8.4] - 2026-04-10

### Added

- Idempotency controls in run queue to prevent duplicate task execution
- Frontend pages for Phase 2-4 features
- Flat navigation layout for debugging
- Dropdown menu navigation

### Fixed

- Marketplace page debugging and error handling improvements

### Changed

- Migrated monitoring from Wazuh to Grafana + Loki
- Converted new feature pages to English (i18n)

## [0.7.4] - 2026-03-15

### Added

- Node Plugin System with dynamic type registration and auto-loading
- Secrets Management with Fernet encryption and `{{secret.xxx}}` variable references
- Run Recovery for orphaned run detection after server restart
- Execution Queue with system-level concurrency control (max 3 concurrent)
- HTTP Sandbox with hostname whitelist (blocks localhost, private IPs)
- 5 built-in plugins: HTTP Request, OTX Lookup, Decision, Slack Notify, Human Approval

## [0.7.3] - 2026-03-01

### Added

- Version management (Draft → Published → Archived lifecycle)
- Context variable system (`{{context.xxx}}`, `{{input.xxx}}`, `{{node.<id>.field}}`)
- Run replay based on historical inputs
- Import/Export in JSON/YAML format

## [0.7.2] - 2026-02-15

### Added

- Manual Approval Node with execution pause
- Approval Inbox management interface
- Slack notifications for real-time alerts
- Failure alerts with automatic notifications

## [0.7.1] - 2026-02-01

### Added

- Webhook and Cron trigger system
- Idempotency for duplicate trigger prevention
- Alembic database migration support

## [0.7.0] - 2026-01-15

### Added

- DAG Engine with topological sort and concurrent execution
- Retry policy with exponential backoff
- Visual DAG editor using React Flow
- Dry run and apply execution modes

## [0.6.0] - 2025-12-01

### Added

- AI-powered alert analysis with dual-engine IOC extraction
- Event timeline reconstruction
- Report generation (ticket, daily, post-incident)
- Asset management with bulk import
- AlienVault OTX threat intelligence integration
- i18n support (English + Chinese)

[0.9.0]: https://github.com/example/soc-copilot/compare/v0.8.4...v0.9.0
[0.8.4]: https://github.com/example/soc-copilot/compare/v0.7.4...v0.8.4
[0.7.4]: https://github.com/example/soc-copilot/compare/v0.7.3...v0.7.4
[0.7.3]: https://github.com/example/soc-copilot/compare/v0.7.2...v0.7.3
[0.7.2]: https://github.com/example/soc-copilot/compare/v0.7.1...v0.7.2
[0.7.1]: https://github.com/example/soc-copilot/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/example/soc-copilot/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/example/soc-copilot/releases/tag/v0.6.0
