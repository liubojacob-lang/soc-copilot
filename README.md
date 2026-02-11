# SOC Copilot - Security Operations Center Intelligent Analysis Platform

[![Version](https://img.shields.io/badge/version-v0.7.4-blue.svg)](./CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/)
[![Node.js](https://img.shields.io/badge/node.js-18+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15.1-black.svg)](https://nextjs.org/)

SOC Copilot is an intelligent analysis workbench designed for Security Operations Center (SOC) teams, providing alert analysis, event timeline reconstruction, report generation, asset management, threat intelligence queries, and **Playbook automation orchestration** capabilities.

---

## Table of Contents

1. [Core Features](#core-features)
2. [Quick Start](#quick-start)
3. [Technical Architecture](#technical-architecture)
4. [API Endpoints](#api-endpoints)
5. [Project Structure](#project-structure)
6. [Version History](#version-history)
7. [Security Notes](#security-notes)

---

## Core Features

### 1. Alert Analyzer
- Event classification (supports 9 security event types)
- Severity assessment
- **Dual-engine IOC extraction** (Local regex + AI for IPs, domains, URLs, hashes)
- Entity recognition (users, hosts, processes)
- Evidence extraction and remediation recommendations
- Impact analysis panel (risk score, associated assets)

### 2. Timeline Builder
- Automatic event timeline reconstruction
- Intelligent suspicious event ranking (Top 5)
- Next investigation step recommendations

### 3. Report Writer
- Ticket templates
- Daily report templates
- Post-incident analysis templates

### 4. Asset Management
- Full CRUD operations
- Bulk import (JSON format)
- Multi-dimensional search (hostname, IP, owner, business line, tags)
- Asset criticality grading (Low/Medium/High/Critical)

### 5. Threat Intelligence
- AlienVault OTX integration
- Local cache (7-day TTL)
- Compliance filtering (private IP, internal domain blocking)

### 6. Playbook Automation Engine

#### v0.7.4 New Features
- **Node Plugin System**: Dynamic node type registration with auto-loading from `plugins/` directory
- **Secrets Management**: Encrypted secret storage (Fernet) with `{{secret.xxx}}` variable references
- **Run Recovery**: Automatic orphaned run detection and recovery after server restart
- **Execution Queue**: System-level concurrency control (max_concurrent=3) with FIFO policy
- **HTTP Sandbox**: Hostname whitelist for security (blocks localhost, private IPs)
- **5 Built-in Plugins**: HTTP Request, OTX Lookup, Decision, Slack Notify, Human Approval

#### v0.7.3 New Features
- **Version Management**: Draft → Published → Archived lifecycle management
- **Context Variable System**: Supports `{{context.xxx}}`, `{{input.xxx}}`, `{{node.<id>.field}}` template variables
- **Run Replay**: Re-execute based on historical inputs
- **Import/Export**: JSON/YAML format support

#### v0.7.2 New Features
- **Manual Approval Node**: Execution pauses for human approval
- **Approval Inbox**: Dedicated approval management interface
- **Slack Notifications**: Real-time notifications to Slack channels
- **Failure Alerts**: Automatic notifications on execution failures

#### v0.7.1 New Features
- **Trigger System**: Webhook and Cron scheduled triggers
- **Idempotency**: Duplicate trigger invocation prevention
- **Auto Migration**: Alembic database migration support

#### v0.7.0 New Features
- **DAG Engine**: Topological sort with concurrent execution
- **Retry Policy**: Exponential backoff for failed nodes
- **Visual DAG Editor**: React Flow-based workflow editor

#### DAG Workflow Engine
- Visual DAG editor (React Flow)
- Multiple node types:
  - **Triggers**: Webhook, Scheduled tasks (Cron)
  - **Process**: IOC extraction, threat intelligence lookup, asset enrichment
  - **Decision**: Conditional branching
  - **Action**: HTTP requests, Slack notifications
  - **Control**: Manual approval, delay
- Execution modes: `dry_run` (simulation) / `apply` (actual execution)

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
venv\Scripts\activate
# Activate virtual environment (Linux/Mac)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start server (database auto-initializes)
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 3. Access Application

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| Frontend | http://localhost:8080 | admin / admin123 |
| Backend API | http://localhost:8000 | - |
| API Documentation | http://localhost:8000/docs | - |
| Database | `data/app.db` (auto-created) | - |

---

## Technical Architecture

### Backend Tech Stack
| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.10+ | Language |
| FastAPI | 0.115.0 | Web Framework |
| SQLAlchemy | 2.0.36 | ORM |
| aiosqlite | 0.20.0 | Async SQLite |
| Alembic | 1.14.0 | Database Migration |
| Pydantic | 2.9.2 | Data Validation |
| python-jose | 3.3.0 | JWT Authentication |
| passlib | 1.7.4 | Password Encryption |
| croniter | 3.0.3 | Cron Expression Parser |
| anthropic | 0.40.0 | Claude AI |

### Frontend Tech Stack
| Technology | Version | Purpose |
|------------|---------|---------|
| Next.js | 15.1 | React Framework |
| React | 19.0 | UI Library |
| TypeScript | 5.x | Type System |
| Tailwind CSS | 3.4.17 | CSS Framework |
| React Flow | 11.11.4 | DAG Visualization |
| Lucide React | 0.563.0 | Icon Library |

---

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze-alert` | Alert Analysis |
| POST | `/api/build-timeline` | Build Timeline |
| POST | `/api/generate-report` | Generate Report |
| GET | `/api/health` | Health Check |

### Asset Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/assets` | Asset list (with search) |
| POST | `/api/assets` | Create asset |
| GET | `/api/assets/{id}` | Asset details |
| PATCH | `/api/assets/{id}` | Update asset |
| DELETE | `/api/assets/{id}` | Delete asset |
| POST | `/api/assets/import` | Bulk import |

### Playbook Definition Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/playbook/definitions` | Definition list |
| POST | `/api/playbook/definitions` | Create definition |
| GET | `/api/playbook/definitions/{id}` | Definition details |
| POST | `/api/playbook/definitions/{id}/run` | Execute definition |
| POST | `/api/playbook/definitions/{id}/publish` | Publish version |
| GET | `/api/playbook/definitions/{id}/versions` | Version history |
| POST | `/api/playbook/definitions/{id}/restore/{version_no}` | Rollback version |
| GET | `/api/playbook/definitions/{id}/export` | Export definition |
| POST | `/api/playbook/definitions/import` | Import definition |

### Playbook Execution Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/playbook/runs` | Execution history |
| GET | `/api/playbook/runs/{run_id}` | Execution details |
| GET | `/api/playbook/runs/{run_id}/nodes` | Node execution details |
| POST | `/api/playbook/runs/{run_id}/replay` | Replay execution |
| GET | `/api/playbook/runs/{run_id}/replay-chain` | Replay chain |

### Approval Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/playbook/approvals` | Approval list |
| POST | `/api/playbook/approvals/{id}/approve` | Approve request |
| POST | `/api/playbook/approvals/{id}/reject` | Reject request |
| GET | `/api/playbook/approvals/pending/count` | Pending approval count |

### Trigger Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/triggers` | Trigger list |
| POST | `/api/triggers` | Create trigger |
| GET | `/api/triggers/{id}` | Trigger details |
| PATCH | `/api/triggers/{id}` | Update trigger |
| DELETE | `/api/triggers/{id}` | Delete trigger |

### Secrets Management (v0.7.4)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/secrets` | List secrets (admin only) |
| POST | `/api/secrets` | Create secret (admin only) |
| GET | `/api/secrets/{name}` | Get secret details |
| PATCH | `/api/secrets/{name}` | Update secret (admin only) |
| DELETE | `/api/secrets/{name}` | Delete secret (admin only) |
| GET | `/api/secrets/key-status` | Check encryption key status |

### Queue Management (v0.7.4)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/playbook-definitions/queue-stats` | Queue statistics |

---

## Project Structure

```
soc-copilot/
├── backend/                    # Backend Service
│   ├── core/                   # Core Configuration
│   │   ├── config.py           # App Configuration
│   │   ├── logger.py           # Logging Configuration
│   │   └── security.py         # Security Utilities
│   ├── db/                     # Database
│   │   └── session.py          # Session Management
│   ├── models/                 # SQLAlchemy Models
│   │   ├── user.py             # User Model
│   │   ├── asset.py            # Asset Model
│   │   ├── playbook_definition.py  # Playbook Definition
│   │   ├── playbook_run.py     # Playbook Execution
│   │   ├── playbook_approval.py    # Approval Record
│   │   ├── trigger.py          # Trigger
│   │   ├── secret.py           # v0.7.4: Secret Model
│   │   └── audit_log.py        # Audit Log
│   ├── routers/                # API Routes
│   │   ├── auth.py             # Authentication
│   │   ├── assets.py           # Assets
│   │   ├── playbook_definitions.py # Playbook Definitions
│   │   ├── playbook.py         # Playbook Execution
│   │   ├── triggers.py         # Triggers
│   │   └── audit.py            # Audit
│   ├── services/               # Business Logic
│   │   ├── playbook_dag_compiler.py    # DAG Compiler
│   │   ├── playbook_dag_scheduler.py   # DAG Scheduler
│   │   ├── playbook_executors/         # Node Executors
│   │   ├── playbook_version_service.py # Version Management
│   │   ├── playbook_replay_service.py  # Replay Service
│   │   ├── secret_service.py           # v0.7.4: Secrets Encryption
│   │   └── run_queue_manager.py        # v0.7.4: Queue Manager
│   ├── playbook_engine/        # Playbook Engine
│   │   ├── dag/                # DAG Engine (v0.7.0)
│   │   │   ├── engine.py       # Execution Engine
│   │   │   ├── state_machine.py    # State Machine
│   │   │   └── retry_policy.py     # Retry Policy
│   │   ├── v7_dag/             # v0.7.4: DAG Plugin System
│   │   │   ├── base_node.py    # Base Node Plugin
│   │   │   ├── registry.py     # Node Registry
│   │   │   └── plugins/        # Built-in Plugins
│   │   │       ├── builtin_http_request.py
│   │   │       ├── builtin_otx_lookup.py
│   │   │       ├── builtin_decision.py
│   │   │       ├── builtin_slack_notify.py
│   │   │       └── builtin_human_approval.py
│   │   └── notifications/      # Notifications Module
│   │       └── slack.py        # Slack Notifications
│   ├── repositories/           # Data Access Layer
│   ├── schemas/                # Pydantic Models
│   └── main.py                 # Application Entry
├── frontend/                   # Frontend Application
│   ├── app/                    # Next.js App Router
│   │   ├── page.tsx            # Home Page (Alert Analysis)
│   │   ├── assets/             # Asset Management
│   │   ├── playbooks/          # Playbook Management
│   │   │   ├── definitions/    # Definition Management
│   │   │   └── approvals/      # Approval Management
│   │   ├── triggers/           # Trigger Management
│   │   ├── admin/              # Admin
│   │   │   ├── users/          # User Management
│   │   │   └── secrets/        # v0.7.4: Secrets Management
│   │   └── settings/           # Settings
│   ├── components/             # Components
│   │   ├── dag/                # DAG Editor
│   │   │   ├── DAGCanvas.tsx   # Canvas
│   │   │   └── DAGNode.tsx     # Node
│   │   ├── Navigation.tsx      # Navigation Bar
│   │   └── playbook/           # Playbook Components
│   └── package.json
├── data/                       # Data Directory
│   └── app.db                  # SQLite Database
├── docs/                       # Documentation
├── MANUAL_TEST.md              # Manual Test Documentation
├── TEST_CASES.md               # Test Cases
└── README.md                   # Project Description
```

---

## Environment Variables

### Backend Configuration (backend/.env)

```ini
# AI Provider (anthropic or zhipu)
AI_PROVIDER=zhipu

# Zhipu AI Configuration
ZHIPU_API_KEY=your_api_key_here

# Threat Intelligence (OTX)
OTX_API_KEY=your_otx_api_key_here
ALLOW_EXTERNAL_TI=false      # Disabled by default, compliance requirement
TI_CACHE_TTL_HOURS=168       # Cache TTL (default 7 days)

# Log Level
LOG_LEVEL=INFO

# Retry Configuration
MAX_RETRIES=2

# v0.7.4: Secrets & Queue Management
# Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
SECRET_ENCRYPTION_KEY=your_fernet_key_here
RUN_QUEUE_MAX=3              # Maximum concurrent playbook runs
RUN_QUEUE_POLICY=fifo        # Queue policy: fifo or priority
HTTP_ALLOWED_HOSTS=otx.alienvault.com,hooks.slack.com  # HTTP sandbox whitelist
```

---

## Version History

### v0.7.4 (Current Version)
- ✨ **Added**: Node plugin system with dynamic auto-loading
- ✨ **Added**: Secrets management with Fernet encryption
- ✨ **Added**: Template variable `{{secret.xxx}}` support
- ✨ **Added**: Run queue management (max_concurrent=3, FIFO)
- ✨ **Added**: Orphaned run recovery on server restart
- ✨ **Added**: HTTP sandbox with hostname whitelist
- ✨ **Added**: 5 built-in node plugins
- ✨ **Added**: Queue status API endpoint
- ✨ **Added**: Secrets management UI (`/admin/secrets`)
- ✨ **Added**: Queue status display on playbooks page
- 🐛 **Fixed**: Queue stats endpoint routing

### v0.7.3
- ✨ **Added**: Playbook version management (draft/published/archived)
- ✨ **Added**: Version history tracking and rollback
- ✨ **Added**: Global context variable system (JSONPath mapping)
- ✨ **Added**: Template variable rendering (context/input/node references)
- ✨ **Added**: Run replay functionality
- ✨ **Added**: Import/Export support (JSON/YAML)
- ✨ **Added**: Responsive navigation and mobile adaptation
- ✨ **Added**: 20+ curl API examples

### v0.7.2
- ✨ **Added**: Manual approval node
- ✨ **Added**: Approval inbox UI
- ✨ **Added**: Slack Webhook notifications
- ✨ **Added**: Execution failure alerts

### v0.7.1
- ✨ **Added**: Trigger system (Webhook/Cron)
- ✨ **Added**: Scheduled task dispatcher
- ✨ **Added**: Automatic database migration (Alembic)

### v0.7.0
- ✨ **Added**: DAG Playbook engine
- ✨ **Added**: Visual workflow editor
- ✨ **Added**: Multi-node type support

<details>
<summary>View More Historical Versions</summary>

### v0.6.1
- ✨ **Added**: Playbook execution engine
- ✨ **Added**: 5 built-in steps
- ✨ **Added**: 3 Playbook templates
- ✨ **Added**: Execution history and step details
- ✨ **Added**: Failure recovery capability
- 🐛 **Fixed**: Timezone issues (using local time)
- 🐛 **Fixed**: Step data passing

### v0.5.0
- ✨ **Added**: SIEM query generation (Splunk, Elastic, Sentinel)
- ✨ **Added**: Remediation action generator

### v0.4.0
- ✨ **Added**: OTX threat intelligence integration
- ✨ **Added**: Threat intelligence caching

### v0.3.0
- ✨ **Added**: Asset management module
- ✨ **Added**: IOC hit tracking
- ✨ **Added**: Impact analysis

</details>

---

## Security Notes

- All remediation recommendations are defensive operations
- All endpoints have input validation
- CORS enabled by default (restrict in production)
- API keys stored in environment variables
- Request ID tracking for auditing
- Playbook execution:
  - dry_run mode enabled by default (no external changes)
  - apply mode requires explicit authorization
  - All executions logged with timestamps
  - Step-level audit trail
  - Failed steps can be reviewed before resuming

---

## Related Documentation

- [MANUAL_TEST.md](./MANUAL_TEST.md) - Manual Test Documentation
- [TEST_CASES.md](./TEST_CASES.md) - Test Cases
- [API Documentation](http://localhost:8000/docs) - Interactive API Documentation (backend must be running)

---

## License

This project is an internal security operations tool for authorized users only.

---

**Version**: v0.7.4
**Last Updated**: 2026-02-10
**Maintainer**: SOC Team
