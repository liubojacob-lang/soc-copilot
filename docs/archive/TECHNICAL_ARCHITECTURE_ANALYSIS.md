# SOC Copilot - Technical Architecture Analysis

**Companion to COMPREHENSIVE_API_AUDIT.md and API_ENDPOINT_REFERENCE.md**
**Generated:** 2026-02-25

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│  Next.js 14+ / TypeScript / Tailwind CSS / i18n                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/WebSocket
┌───────────────────────────▼─────────────────────────────────────┐
│                      API Gateway Layer                           │
│  FastAPI / Pydantic / Middleware (Auth, Audit, Rate Limit)      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌──────▼──────┐  ┌────────▼────────┐
│  Core APIs     │  │  AI/ML APIs │  │ Integration APIs│
│  - Auth        │  │  - LLM      │  │  - Wazuh        │
│  - Users       │  │  - RAG      │  │  - Dify         │
│  - Assets      │  │  - Tasks    │  │  - Cloud       │
│  - Alerts      │  │  - Vector   │  │  - Threat Intel│
└───────┬────────┘  └──────┬──────┘  └────────┬────────┘
        │                  │                   │
        └──────────────────┼───────────────────┘
                           │
┌──────────────────────────▼─────────────────────────────────────┐
│                     Service Layer                               │
│  Business Logic / Orchestration / Caching                       │
└───────────────────────────┬─────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼────────┐  ┌──────▼──────┐  ┌───────▼────────┐
│  PostgreSQL    │  │   Redis     │  │  Vector DB     │
│  - Models      │  │  - Cache    │  │  - Embeddings  │
│  - Relations   │  │  - Queue    │  │  - RAG         │
└────────────────┘  └─────────────┘  └────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼────────┐  ┌──────▼──────┐  ┌───────▼────────┐
│  Wazuh SIEM    │  │  Cloud      │  │  External APIs │
│  - Alerts      │  │  Providers  │  │  - OTX        │
│  - Agents      │  │  - K8s      │  │  - LLMs       │
└────────────────┘  └─────────────┘  └────────────────┘
```

---

## Technology Stack

### Frontend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Next.js | 14+ |
| Language | TypeScript | 5.x |
| Styling | Tailwind CSS | 3.x |
| Internationalization | next-intl | Built-in |
| State Management | React Hooks | - |
| HTTP Client | fetch | Native |
| Real-time | WebSocket | Native |

### Backend
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | Latest |
| Language | Python | 3.10+ |
| ASGI Server | Uvicorn | Latest |
| ORM | SQLAlchemy (async) | 2.x |
| Validation | Pydantic | 2.x |
| Authentication | JWT | - |
| Database | PostgreSQL | 15+ |
| Cache | Redis | 7+ |

### AI/ML
| Component | Technology |
|-----------|-----------|
| LLM Providers | Anthropic, Zhipu, NVIDIA, Moonshot, OpenRouter |
| Vector Store | Custom (likely Chroma/Weaviate) |
| Embeddings | Provider-specific |
| Task Queue | Redis-based |

### DevOps
| Component | Technology |
|-----------|-----------|
| Container | Docker |
| Orchestration | Docker Compose |
| Reverse Proxy | Nginx (implied) |
| SIEM | Wazuh |

---

## Database Schema Overview

### Core Tables

```sql
-- Users & Authentication
users (id, username, email, role, created_at)
api_keys (id, user_id, key_hash, is_active, expires_at)

-- Assets & Inventory
assets (id, hostname, ip, criticality, tags)

-- Alerts & Security Events
security_alerts (id, title, description, severity, status, source)
correlated_events (id, incident_type, severity, related_events)
event_similarity (id, event_id_1, event_id_2, similarity_score)

-- Threat Intelligence
ioc_hits (id, ioc_type, ioc_value, threat_feed, confidence)
threat_intel_cache (id, ioc_value, data, expires_at)

-- Playbooks
playbook_definitions (id, name, description, definition_json)
playbook_runs (id, definition_id, status, started_at, completed_at)
playbook_node_runs (id, run_id, node_id, status, result)
playbook_approvals (id, run_id, node_id, approver, decision)

-- Triggers
triggers (id, type, config, is_active)

-- AI & ML
ai_models (id, provider, display_name, capabilities, enabled)
ai_tasks (id, task_type, status, input_data, result, user_id)
ai_user_settings (id, user_id, default_model_id)

-- Audit & History
audit_logs (id, user_id, action, path, status_code, created_at)
history (id, entity_type, entity_id, data, created_at)

-- Monitoring
monitor_history (id, metric_name, value, timestamp)

-- Secrets
secrets (id, name, encrypted_value)

-- UEBA
(Numerous behavior analytics tables - not fully enumerated)
```

---

## API Architecture Patterns

### 1. Repository Pattern

**Usage:** Data access abstraction

```python
# Example
class PlaybookDefinitionRepository:
    async def list_definitions(self, is_active, page, page_size)
    async def get_by_id(self, definition_id)
    async def create(self, definition_data)
    async def update(self, definition_id, update_data)
    async def delete(self, definition_id)
```

**Repositories Found:**
- `PlaybookDefinitionRepository`
- `AIModelRepository`
- `AIUserSettingRepository`
- `APIKeyRepository`
- `AuditRepository`
- `UserRepository`
- `SecretRepository`

### 2. Service Layer Pattern

**Usage:** Business logic encapsulation

```python
# Example
class AlertLifecycleService:
    async def get_alert_lifecycle(self, alert_id)
    async def update_status(self, alert_id, status, user_id)
    async def assign_alert(self, alert_id, assignment, user_id)
```

**Services Found:** 55+ across multiple domains

### 3. Factory Pattern

**Usage:** AI provider instantiation

```python
class LLMFactory:
    @staticmethod
    def create_provider_for_model(model_id, provider)
    # Returns: AnthropicProvider, ZhipuProvider, etc.
```

### 4. Strategy Pattern

**Usage:** Playbook node execution

```python
# Each node type has its own executor
class HumanApprovalExecutor(ExecutorBase)
class TILookupOTXExecutor(ExecutorBase)
```

### 5. Observer Pattern

**Usage:** WebSocket real-time updates

```python
class WebSocketManager:
    async def broadcast(self, message)
    async def send_to_user(self, user_id, message)
```

---

## Authentication & Authorization

### Authentication Flow

```
1. POST /api/auth/login
   ↓
2. Validate credentials
   ↓
3. Generate JWT access token + refresh token
   ↓
4. Return tokens to client
   ↓
5. Client includes access token in Authorization header
   ↓
6. Middleware validates token on each request
   ↓
7. Current user injected into route handlers
```

### Authorization Model

**Roles:**
- `ADMIN` - Full system access
- `AUDITOR` - Read-only audit access
- `ANALYST` - Standard SOC operations
- `USER` - Basic access

**Permissions:**
- Role-based access control (RBAC)
- Resource-level permissions (user can only access their own resources)
- Admin-only endpoints marked with `@require_role(UserRole.ADMIN)`

### Security Features

1. **JWT Authentication**
   - Short-lived access tokens
   - Refresh token rotation
   - Token blacklisting on logout

2. **API Key Authentication**
   - Alternative to JWT for programmatic access
   - Key prefix for identification
   - Expiration and revocation support

3. **Middleware**
   - Authentication middleware
   - Authorization middleware
   - Audit logging middleware
   - Rate limiting (planned)
   - CSRF protection (planned)

---

## Caching Strategy

### Redis Usage

**Cache Types:**
1. **AI Model Responses** - Cache LLM responses to reduce API calls
2. **Threat Intelligence** - Cache OTX and other TI lookups
3. **Session Data** - User sessions and WebSocket connections
4. **Task Queues** - Background AI tasks
5. **Real-time Data** - WebSocket message distribution

**Cache Invalidation:**
- TTL-based expiration
- Manual invalidation endpoints
- Cache refresh on data updates

### Caching Endpoints

```
POST /api/threat-intel/cache/refresh
DELETE /api/threat-intel/cache/expired
DELETE /api/threat-intel/cache/all
```

---

## Message Queue & Background Tasks

### AI Task Queue

**Architecture:**
- Redis-based queue
- Worker pool for task processing
- Status tracking and result storage

**Task Types:**
- `alert_analysis` - Analyze security alerts
- `timeline_analysis` - Build event timelines
- `report_generation` - Generate reports
- `chat_completion` - Chat interactions
- `ioc_analysis` - Analyze IOCs

**Task Lifecycle:**
```
PENDING → PROCESSING → COMPLETED
                      → FAILED
                      → TIMEOUT
```

### Trigger-Based Execution

**Trigger Types:**
1. **Cron Triggers** - Schedule-based automation
2. **Webhook Triggers** - External event-driven automation
3. **Alert Triggers** - Alert-based automation

**Execution Flow:**
```
Trigger fires → Queue playbook run → Execute nodes → Update status
```

---

## Real-time Communication

### WebSocket Architecture

**Endpoint:** `/api/websocket/ws/alerts`

**Features:**
- Real-time alert streaming
- User-specific channels
- Connection pooling
- Automatic reconnection

**Message Types:**
- Alert created
- Alert updated
- Alert status changed
- Task status updates
- System notifications

### WebSocket Manager

```python
class WebSocketManager:
    connections: Dict[user_id, WebSocket]
    async def connect(user_id, websocket)
    async def disconnect(user_id)
    async def broadcast(message)
    async def send_to_user(user_id, message)
```

---

## Integration Patterns

### Wazuh Integration

**Architecture:**
1. **Webhook Receiver** - Accept Wazuh alerts via webhook
2. **Alert Mapper** - Transform Wazuh format to internal format
3. **Log Receiver** - Continuous log ingestion
4. **API Client** - Query Wazuh for agents, alerts, etc.

**Endpoints:**
- Webhook: `/api/wazuh/webhook` (POST)
- Management: `/api/wazuh/*` (GET, POST)

### Dify Integration

**Architecture:**
1. **Workflow Sync** - Import Dify workflows as playbooks
2. **Execution Bridge** - Execute Dify workflows from SOC Copilot
3. **Result Mapping** - Transform Dify responses to internal format

**Endpoints:**
- `/api/dify/workflows` - Browse and import
- `/api/dify/workflows/{app_id}/execute` - Execute
- `/api/dify/workflows/sync/{definition_id}` - Sync changes

### Cloud Provider Integration

**Supported Providers:**
- Kubernetes
- Container registries (implied)
- Cloud platforms (AWS, GCP, Azure - planned)

**Capabilities:**
- Container image scanning
- Kubernetes resource monitoring
- Compliance reporting

---

## Error Handling Strategy

### Exception Hierarchy

```
Exception
├── HTTPException (FastAPI)
├── ValidationError (Pydantic)
├── ServiceException (Custom)
│   ├── AlertNotFoundError
│   ├── PlaybookExecutionError
│   └── AIServiceError
└── IntegrationError
    ├── WazuhConnectionError
    └── DifyAPIError
```

### Error Response Formats

**Standard Error:**
```json
{
  "detail": "Error message"
}
```

**Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "error message",
      "type": "value_error"
    }
  ]
}
```

**Custom Error:**
```json
{
  "success": false,
  "error": "Error message",
  "traceback": "..."  # Admin only
}
```

---

## Logging & Monitoring

### Logging Strategy

**Log Levels:**
- DEBUG - Development debugging
- INFO - General operation information
- WARNING - Warning conditions
- ERROR - Error conditions
- CRITICAL - Critical failures

**Log Destinations:**
- Console output (development)
- File output (production)
- Structured logging (JSON format)

**Audit Logging:**
All significant actions logged to `audit_logs` table:
- User authentication
- CRUD operations
- Admin actions
- Playbook executions
- Configuration changes

### Monitoring Endpoints

**Health Checks:**
- `/api/health` - General health
- `/api/health/live` - Liveness probe
- `/api/health/ready` - Readiness probe
- `/api/health/database` - Database connectivity
- `/api/health/redis` - Redis connectivity
- `/api/health/resources` - System resources

**Metrics:**
- `/api/monitor/metrics` - System metrics
- `/api/monitor/dashboard` - Monitoring dashboard
- `/api/monitor/history` - Historical metrics

---

## Performance Optimization

### Database Optimization

**Indexes:**
- Primary keys on all tables
- Foreign key indexes
- Frequently queried fields (created_at, status, user_id)
- Composite indexes for common query patterns

**Query Optimization:**
- Async SQL operations
- Connection pooling
- Query result pagination
- N+1 query prevention

### API Optimization

**Strategies:**
- Response pagination
- Field selection (partial responses)
- Compression (gzip)
- HTTP caching headers
- ETag support

**Background Processing:**
- AI tasks in background queue
- Bulk operations in chunks
- Async I/O operations

---

## Scalability Considerations

### Current Architecture

**Single-Server Deployment:**
- All components on one server
- Docker Compose orchestration
- Shared database and cache

### Scalability Path

**Horizontal Scaling:**
1. **API Servers** - Multiple FastAPI instances behind load balancer
2. **Workers** - Separate worker processes for background tasks
3. **Database** - Read replicas for read-heavy operations
4. **Cache** - Redis Cluster for distributed caching

**Vertical Scaling:**
- Increase server resources
- Optimize database queries
- Implement caching layers

**Microservices Migration (Future):**
- Separate AI service
- Separate integration service
- Separate workflow engine

---

## Security Architecture

### Security Layers

1. **Network Security**
   - HTTPS/TLS encryption
   - Firewall rules
   - VPN access (implied)

2. **Application Security**
   - Input validation (Pydantic)
   - SQL injection prevention (ORM)
   - XSS prevention
   - CSRF protection (planned)

3. **Authentication Security**
   - JWT with short expiration
   - Refresh token rotation
   - Password hashing (bcrypt)
   - Account lockout after failed attempts

4. **Authorization Security**
   - RBAC implementation
   - Resource-level permissions
   - Admin-only endpoints protection

5. **Data Security**
   - Encryption at rest (secrets)
   - Encryption in transit (TLS)
   - Audit logging for compliance
   - Data retention policies

### Security Modules

Located in `/backend/security-modules/` and `/backend/middleware/`:
- `security_validators.py` - Input validation
- `authorization_middleware.py` - Authorization checks
- `csrf_middleware.py` - CSRF protection
- `rate_limiter.py` - Rate limiting
- `trace_middleware.py` - Request tracing

---

## Testing Strategy

### Test Coverage

**Unit Tests:**
- Service layer tests
- Repository tests
- Utility function tests

**Integration Tests:**
- API endpoint tests
- Database integration tests
- External API integration tests

**Test Files Found:**
- `test_auth.py`
- `test_security.py`
- `test_v0_7_dag.py`
- `test_ai_service.py`
- `test_event_correlation_service.py`
- `test_correlation_integration.py`
- `test_threat_intel.py`
- Many more...

### Test Configuration

**Pytest Configuration:**
- Async test support
- Database fixtures
- Mock external APIs
- Test environment isolation

---

## Deployment Architecture

### Development Environment

```
Docker Compose:
├── Backend (FastAPI)
├── Frontend (Next.js dev server)
├── PostgreSQL
└── Redis
```

### Production Environment

**Recommended:**
```
┌─────────────────┐
│  Nginx/Proxy    │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐  ┌─▼────────┐
│Frontend│  │  Backend │
│(Static)│  │  (Uvicorn)│
└───────┘  └─┬────────┘
             │
    ┌────────┼────────┐
    │        │        │
┌───▼──┐  ┌─▼───┐  ┌▼────┐
│  DB  │  │Redis│  │Wazuh│
└──────┘  └─────┘  └─────┘
```

### Configuration Management

**Environment Variables:**
- Database connection strings
- API keys (LLM providers, integrations)
- Secret keys (JWT, encryption)
- Feature flags
- Timeout configurations

**Settings Files:**
- `.env` - Local development
- `.env.example` - Template
- Settings loaded from `core/config.py`

---

## Documentation Status

### Existing Documentation

**Architecture Docs:**
- `docs/00-getting-started.md`
- `docs/01-architecture.md`
- `docs/02-api-overview.md`
- `docs/03-database.md`
- `docs/04-alert-analyzer.md`
- `docs/05-threat-intel.md`
- `docs/06-playbook-engine.md`
- `docs/07-frontend.md`
- `docs/08-security.md`
- `docs/09-ops-deploy.md`
- `docs/10-troubleshooting.md`
- `docs/11-roadmap.md`
- `docs/12-contributing.md`
- `docs/13-testing-guide.md`
- `docs/14-acceptance-criteria.md`

### Missing Documentation

1. **API Reference** - Comprehensive OpenAPI/Swagger documentation
2. **Component Diagrams** - Detailed component interaction diagrams
3. **Deployment Guides** - Step-by-step production deployment
4. **Runbooks** - Operational procedures
5. **Development Setup** - Local development environment setup

---

## Future Enhancements

### Short-term (3-6 months)

1. **Frontend Development**
   - Complete missing pages (AI Tasks, Exports, etc.)
   - Enhance existing pages with full API coverage
   - Improve user experience and workflows

2. **API Improvements**
   - Standardize response formats
   - Add comprehensive error handling
   - Implement rate limiting
   - Add API versioning consistency

3. **Security Enhancements**
   - Complete CSRF protection
   - Add audit log archival
   - Implement data retention policies
   - Add multi-factor authentication

### Medium-term (6-12 months)

4. **Scalability**
   - Horizontal scaling support
   - Database read replicas
   - Distributed caching
   - Load balancing

5. **Features**
   - Advanced case management
   - Collaboration features
   - Report scheduling
   - Custom alert rules

### Long-term (12+ months)

6. **Microservices Migration**
   - Separate AI service
   - Separate integration service
   - Separate workflow engine

7. **Advanced Analytics**
   - Machine learning-based anomaly detection
   - Predictive analytics
   - Threat hunting automation

8. **Ecosystem Expansion**
   - More integrations (SIEMs, cloud providers)
   - Plugin system
   - API marketplace

---

## Maintenance & Operations

### Monitoring Requirements

**Application Metrics:**
- Request rate and latency
- Error rate by endpoint
- Database query performance
- Cache hit rates
- WebSocket connection counts
- Background task queue depth

**Business Metrics:**
- Alert volume and trends
- Mean time to respond (MTTR)
- Playbook execution success rate
- User activity
- System utilization

### Backup Strategy

**Database Backups:**
- Daily full backups
- Point-in-time recovery
- Backup retention (90 days)

**Configuration Backups:**
- Version control for configuration
- Environment variable backups
- Secret backups (encrypted)

### Update Strategy

**Rolling Updates:**
- Zero-downtime deployments
- Blue-green deployments
- Database migration support
- Feature flags for gradual rollout

---

## This Document

Generated by comprehensive analysis of:
- Codebase architecture
- Technology stack
- Design patterns
- Integration strategies
- Security architecture
- Deployment patterns

**Companion Documents:**
- `COMPREHENSIVE_API_AUDIT.md` - Complete API and frontend audit
- `API_ENDPOINT_REFERENCE.md` - Quick reference for all endpoints

**Last Updated:** 2026-02-25
