# Changelog

All notable changes to SOC Copilot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
