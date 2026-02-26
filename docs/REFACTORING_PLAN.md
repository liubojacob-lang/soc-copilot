# SOC Copilot - Structure Compression & Technical Debt Cleanup Plan

> **Version**: 1.0  
> **Date**: 2026-02-15  
> **Author**: Architecture Review  
> **Status**: Draft for Review

---

## Table of Contents

1. [Module Map](#1-module-map)
2. [Structure Issues](#2-structure-issues)
3. [P0/P1/P2 Optimization List](#3-p0p1p2-optimization-list)
4. [Phased Refactoring Plan](#4-phased-refactoring-plan)
5. [New Directory Structure](#5-new-directory-structure)
6. [Verification Standards](#6-verification-standards)

---

## 1. Module Map

### 1.1 Backend Module Map

| Domain | Router | Service | Repository | Model | Schema |
|--------|--------|---------|------------|-------|--------|
| **Alert** | `routers/alert.py` | `services/alert_service.py` | `repositories/history_repository.py` | `models/history.py` | `schemas/alert.py` |
| **Asset** | `routers/assets.py` | `services/asset_service.py` | `repositories/asset_repository.py` | `models/asset.py` | `schemas/asset.py` |
| **Threat Intel** | `routers/threat_intel.py` | `services/threat_intel_service.py` | `repositories/threat_intel_repository.py` | `models/threat_intel_cache.py` | `schemas/threat_intel.py` |
| **Playbook Run** | `routers/playbook.py` | `services/playbook_run_service.py` | `repositories/playbook_run_repository.py` | `models/playbook_run.py` | `schemas/playbook_run.py` |
| **Playbook Definition** | `routers/playbook_definitions.py` | `services/playbook_dag_scheduler.py` | `repositories/playbook_definition_repository.py` | `models/playbook_definition.py` | `schemas/playbook_dag.py` |
| **Trigger** | `routers/triggers.py` | `services/trigger_service.py` | `repositories/trigger_repository.py` | `models/trigger.py` | - |
| **AI** | `routers/ai.py`, `routers/ai_models.py` | `services/ai_service.py`, `services/ai_providers.py` | `repositories/ai_model_repository.py` | `models/ai_model.py` | `schemas/ai_model.py` |
| **User/Auth** | `routers/auth.py`, `routers/users.py` | `services/cookie_auth.py` | `repositories/user_repository.py` | `models/user.py` | `schemas/user.py` |

### 1.2 Playbook Engine Architecture

```
playbook_engine/
+-- __init__.py              # Exports: PlaybookEngineAdapter, PlaybookExecutionEngine
+-- adapter.py               # v6/v7 compatibility layer (119 lines)
+-- v6_linear/               # Legacy linear execution
|   +-- engine.py            # PlaybookExecutionEngine (438 lines)
|   +-- registry.py          # Step registry
|   +-- steps/               # 5 step implementations
+-- v7_dag/                  # DAG-based execution
|   +-- base_node.py         # BaseNodePlugin abstract class
|   +-- registry.py          # NodeRegistry for plugins
|   +-- plugins/             # 14 node plugins
+-- dag/                     # Core DAG engine
|   +-- engine.py            # DAGExecutor (870+ lines) - TOO LARGE
|   +-- exceptions.py        # Exception hierarchy (400+ lines)
|   +-- retry_policy.py      # RetryPolicy, RetryExecutor
|   +-- state_machine.py     # NodeStateMachine
+-- triggers/                # Trigger handlers
|   +-- alert_triggers.py
|   +-- cron.py
|   +-- webhook.py
+-- notifications/           # Notification handlers
    +-- http_callback.py
    +-- slack.py
```

### 1.3 Frontend Module Map

| Domain | Page Entry | API Module | Key Components |
|--------|------------|------------|----------------|
| **Alert Analysis** | `app/page.tsx` | `api.analyzeAlert()` | `AlertAnalyzerTab`, `IOCSummaryCard` |
| **Assets** | `app/assets/page.tsx` | `api.listAssets()` | - |
| **Playbook Runs** | `app/playbooks/page.tsx` | `api.createPlaybookRun()` | `PlaybookPanel` |
| **Playbook Definitions** | `app/playbooks/definitions/[id]/page.tsx` | `api_v7.getDefinition()` | `DAGCanvas`, `DAGNode` |
| **Triggers** | `app/triggers/page.tsx` | `api_triggers.listTriggers()` | - |
| **AI Assistant** | `app/ai-assistant/page.tsx` | `api.ai.*` | `AIAssistant` |

### 1.4 Key Data Flows

#### Alert Analysis Flow
```
POST /api/analyze-alert
  -> AlertService.analyze()
     -> LLMRetryService.call_with_retry()
        -> AIProviders.call_model()
     -> ThreatIntelService.lookup_iocs() [optional]
     -> ImpactService.analyze()
  -> HistoryRepository.create()
  -> Response with history_id
```

#### DAG Playbook Execution Flow
```
POST /api/playbook-definitions/{id}/run
  -> PlaybookDefinitionRepository.get_by_id()
  -> DAGCompiler.validate_and_compile()
  -> RunQueueManager.can_start_run()
  -> PlaybookRunRepository.create()
  -> DAGScheduler.execute()
     -> NodeRegistry.get_plugin()
     -> BaseNodePlugin.execute()
     -> PlaybookNodeRunRepository.create/update()
  -> Response with run_id
```

---

## 2. Structure Issues

### 2.1 Duplicate Schemas

| Issue | Files | Impact |
|-------|-------|--------|
| `PlaybookDefinitionCreate` defined twice | `schemas/playbook_run.py:133`, `schemas/playbook_dag.py:78` | Confusion, potential drift |
| `PlaybookDefinitionResponse` defined twice | `schemas/playbook_run.py:151`, `schemas/playbook_dag.py:97` | Maintenance burden |
| `DAGPlaybookRunCreate` vs `PlaybookRunCreateRequest` | Different naming conventions | API inconsistency |

**Recommendation**: Consolidate into `schemas/playbook.py` for shared types.

### 2.2 Duplicate Executors

| Node Type | v7_dag/plugins/ | services/playbook_executors/ |
|-----------|-----------------|------------------------------|
| ti_lookup_otx | `builtin_otx_lookup.py` | `ti_lookup_otx_executor.py` |
| decision | `builtin_decision.py` | `decision_executor.py` |
| http_request | `builtin_http_request.py` | `http_request_executor.py` |
| extract_iocs | `builtin_extract_iocs.py` | `extract_iocs_executor.py` |
| human_approval | `builtin_human_approval.py` | `human_approval_executor.py` |
| sleep | `builtin_sleep.py` | `sleep_executor.py` |

**Recommendation**: Deprecate `services/playbook_executors/`, use only `v7_dag/plugins/`.

### 2.3 Naming Inconsistencies

| Current | Issue | Recommended |
|---------|-------|--------------|
| `playbooks/playbook_engine.py` | Conflicts with `playbook_engine/` directory | Rename to `siem_query_generator.py` |
| `definition_json` vs `dag_json` | Model uses `definition_json`, API returns `dag` | Standardize to `dag_json` |
| `PlaybookRunModel.steps` vs `PlaybookRunModel.node_runs` | Two different step tracking systems | Document v6 vs v7 distinction |
| `step_id` vs `node_id` | v6 uses steps, v7 uses nodes | Keep for backward compatibility |

### 2.4 Overly Large Files

| File | Lines | Size | Issue |
|------|-------|------|-------|
| `frontend/lib/api.ts` | 1700+ | 49KB | All API types and methods in one file |
| `backend/playbook_engine/dag/engine.py` | 870+ | 32KB | Complex DAG execution logic |
| `backend/playbooks/query_templates.py` | 600+ | 25KB | SIEM query templates |
| `backend/routers/playbook_definitions.py` | 700+ | 31KB | CRUD + execution endpoints |

### 2.5 Deep Directory Structures

| Path | Depth | Recommendation |
|------|-------|----------------|
| `playbook_engine/v7_dag/plugins/` | 4 | Flatten to `playbook_engine/plugins/` after v6 deprecation |
| `services/playbook_executors/` | 3 | Remove entirely (deprecated) |

### 2.6 Boundary Confusion: playbook_engine vs services

| File | Current Location | Should Be |
|------|------------------|-----------|
| `playbook_dag_compiler.py` | `services/` | `playbook_engine/dag/compiler.py` |
| `playbook_dag_scheduler.py` | `services/` | `playbook_engine/dag/scheduler.py` |
| `playbook_run_service.py` | `services/` | Keep (business logic) |
| `run_queue_manager.py` | `services/` | Keep (infrastructure) |

---

## 3. P0/P1/P2 Optimization List

### P0 - Critical (Must Fix First)

| ID | Issue | Workload | Files Affected |
|----|-------|----------|----------------|
| P0-1 | **500 Error Observability** - traceback in `extra` field may not be indexed | S | `middleware/exception_handler.py` |
| P0-2 | **DAGCanvas Infinite Loop Risk** - `nodeStatusesHash` could be unstable | S | `frontend/components/dag/DAGCanvas.tsx` |
| P0-3 | **Run Queue Idempotency** - No request deduplication for playbook runs | M | `services/run_queue_manager.py`, `routers/playbook_definitions.py` |

### P1 - High Priority

| ID | Issue | Workload | Files Affected |
|----|-------|----------|----------------|
| P1-1 | **Duplicate Schemas** - `PlaybookDefinitionCreate` defined in 2 files | S | `schemas/playbook_run.py`, `schemas/playbook_dag.py` |
| P1-2 | **Duplicate Executors** - Two executor implementations exist | M | `services/playbook_executors/`, `playbook_engine/v7_dag/plugins/` |
| P1-3 | **api.ts Too Large** - 1700+ lines, hard to maintain | L | `frontend/lib/api.ts` |
| P1-4 | **dag/engine.py Too Large** - 870+ lines, complex logic | M | `playbook_engine/dag/engine.py` |
| P1-5 | **Naming Confusion** - `playbooks/playbook_engine.py` vs `playbook_engine/` | S | `playbooks/playbook_engine.py` |

### P2 - Medium Priority

| ID | Issue | Workload | Files Affected |
|----|-------|----------|----------------|
| P2-1 | **Repository Fragmentation** - 4 playbook-related repositories | M | `repositories/playbook_*.py` |
| P2-2 | **Missing Test Coverage** - No tests for `run_queue_manager.py` | M | `tests/` |
| P2-3 | **Config Bloat** - `core/config.py` has 50+ settings | S | `core/config.py` |
| P2-4 | **Deep Directory** - `v7_dag/plugins/` is 4 levels deep | S | `playbook_engine/` |
| P2-5 | **Type Duplication** - Frontend types duplicated in `api.ts` and `types.ts` | M | `frontend/lib/` |

---

## 4. Phased Refactoring Plan

### Phase 0: P0 Fixes (Week 1)

#### Step 0.1: Fix 500 Error Observability
**Goal**: Ensure all 500 errors have full traceback in logs

**Files Modified**:
- `backend/middleware/exception_handler.py`

**Changes**:
```python
# Before (line 233-240):
logger.error(
    f"[{trace_id}] Unhandled exception: {type(exc).__name__}: {str(exc)}",
    extra={
        "path": request.url.path,
        "traceback": traceback.format_exc(),
    },
)

# After:
logger.error(
    f"[{trace_id}] Unhandled exception: {type(exc).__name__}: {str(exc)}\n"
    f"Traceback:\n{traceback.format_exc()}",
    exc_info=True,  # Ensure traceback is captured
)
```

**Verification**: 
- Run `pytest tests/test_middleware.py -v`
- Trigger a 500 error and check log output contains full traceback

**Git Commit**: `fix(middleware): improve 500 error traceback logging with exc_info=True`

---

#### Step 0.2: Fix DAGCanvas Infinite Loop Risk
**Goal**: Add maximum update depth protection

**Files Modified**:
- `frontend/components/dag/DAGCanvas.tsx`

**Changes**:
```typescript
// Add after line 78:
const MAX_UPDATE_ITERATIONS = 100;
const updateIterationRef = useRef(0);

// Modify useLayoutEffect at line 194:
useLayoutEffect(() => {
    if (!readonly || !initializedRef.current) return;
    
    // Prevent infinite loops
    if (updateIterationRef.current >= MAX_UPDATE_ITERATIONS) {
        console.warn('[DAGCanvas] Max update iterations reached, skipping');
        return;
    }
    updateIterationRef.current += 1;
    
    // ... rest of the effect
}, [readonly, nodeStatusesHash, setNodes, setEdges]);

// Reset counter when definition changes
useLayoutEffect(() => {
    updateIterationRef.current = 0;
}, [currentDefinitionKey]);
```

**Verification**:
- Run `cd frontend && npm run build` (no errors)
- Open playbook definition page, verify DAG renders correctly
- Check browser console for no infinite loop warnings

**Git Commit**: `fix(dag-canvas): add max update depth protection to prevent infinite loops`

---

#### Step 0.3: Add Run Queue Idempotency
**Goal**: Prevent duplicate playbook run submissions

**Files Modified**:
- `backend/services/run_queue_manager.py`
- `backend/routers/playbook_definitions.py`
- `backend/schemas/playbook_run.py`

**Changes**:

1. Add idempotency key to request schema:
```python
# schemas/playbook_run.py - add to DAGPlaybookRunCreate:
idempotency_key: Optional[str] = Field(None, description="Idempotency key for deduplication")
```

2. Add idempotency check in router:
```python
# routers/playbook_definitions.py - in run_dag_definition endpoint:
if request.idempotency_key:
    existing_run = await run_repo.get_by_idempotency_key(request.idempotency_key)
    if existing_run:
        logger.info(f"[{trace_id}] Duplicate run request with idempotency key: {request.idempotency_key}")
        return DAGPlaybookRunResponse.model_validate(existing_run)
```

3. Add repository method:
```python
# repositories/playbook_run_repository.py - add method:
async def get_by_idempotency_key(self, key: str) -> Optional[PlaybookRunModel]:
    stmt = select(PlaybookRunModel).where(PlaybookRunModel.idempotency_key == key)
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```

**Verification**:
- Run `pytest tests/test_v0_7_dag.py -v`
- Test duplicate run submission with same idempotency key

**Git Commit**: `feat(run-queue): add idempotency key support for playbook run deduplication`

---

### Phase 1: Schema Consolidation (Week 2)

#### Step 1.1: Consolidate Playbook Schemas
**Goal**: Single source of truth for playbook-related schemas

**Files Modified**:
- `backend/schemas/playbook.py` (expand)
- `backend/schemas/playbook_run.py` (remove duplicates)
- `backend/schemas/playbook_dag.py` (remove duplicates)

**Changes**:
1. Move shared types to `schemas/playbook.py`:
   - `PlaybookDefinitionCreate`
   - `PlaybookDefinitionUpdate`
   - `PlaybookDefinitionResponse`
   - `DAGSchema`, `NodeSchema`, `EdgeSchema`

2. Update imports in all consumers

**Verification**:
- Run `pytest tests/ -v`
- Run `cd frontend && npm run build`

**Git Commit**: `refactor(schemas): consolidate playbook schemas into single module`

---

#### Step 1.2: Deprecate services/playbook_executors/
**Goal**: Remove duplicate executor implementation

**Files Modified**:
- `backend/services/playbook_executors/` (mark deprecated)
- `backend/services/playbook_executors/__init__.py` (add deprecation warning)

**Changes**:
```python
# services/playbook_executors/__init__.py:
import warnings
warnings.warn(
    "services.playbook_executors is deprecated. "
    "Use playbook_engine.v7_dag.plugins instead.",
    DeprecationWarning,
    stacklevel=2
)
```

**Verification**:
- Run tests, ensure no deprecation warnings in normal operation
- Verify all executors available in `v7_dag/plugins/`

**Git Commit**: `deprecate(executors): mark services/playbook_executors as deprecated`

---

### Phase 2: File Splitting (Week 3)

#### Step 2.1: Split frontend/lib/api.ts
**Goal**: Modular API client structure

**New Files**:
```
frontend/lib/api/
+-- index.ts           # Re-exports all modules
+-- client.ts          # Base fetchWithTimeout, ApiError
+-- types/
|   +-- alert.ts       # AlertAnalysisRequest, AlertAnalysisResponse
|   +-- asset.ts       # AssetCreate, AssetResponse
|   +-- playbook.ts    # PlaybookRunResponse, DAGNode
|   +-- trigger.ts     # TriggerOut, WebhookTriggerCreate
|   +-- user.ts        # User, LoginRequest
+-- modules/
    +-- alert.ts       # api.analyzeAlert, etc.
    +-- asset.ts       # api.listAssets, etc.
    +-- playbook.ts    # api_v7.*, api_v73.*
    +-- trigger.ts     # api_triggers.*
    +-- auth.ts        # api.login, etc.
```

**Migration Steps**:
1. Create new directory structure
2. Extract types to `types/`
3. Extract API methods to `modules/`
4. Update imports in all pages
5. Keep `api.ts` as re-export for backward compatibility

**Verification**:
- Run `cd frontend && npm run build`
- Run `cd frontend && npm run lint`

**Git Commit**: `refactor(api): split lib/api.ts into modular structure`

---

#### Step 2.2: Split playbook_engine/dag/engine.py
**Goal**: Smaller, focused modules

**New Files**:
```
backend/playbook_engine/dag/
+-- engine.py          # DAGExecutor main class (200 lines)
+-- executor.py        # Node execution logic (200 lines)
+-- context.py         # Context variable management (100 lines)
+-- validation.py      # DAG validation helpers (100 lines)
+-- compiler.py        # Move from services/playbook_dag_compiler.py
+-- scheduler.py       # Move from services/playbook_dag_scheduler.py
```

**Verification**:
- Run `pytest tests/test_v0_7_dag.py -v`
- Run DAG playbook execution manually

**Git Commit**: `refactor(dag-engine): split engine.py into focused modules`

---

### Phase 3: Naming Cleanup (Week 4)

#### Step 3.1: Rename playbooks/playbook_engine.py
**Goal**: Clear naming for SIEM query generation

**Files Modified**:
- `backend/playbooks/playbook_engine.py` -> `backend/playbooks/siem_query_generator.py`
- All files importing from it

**Changes**:
```python
# playbooks/siem_query_generator.py:
"""SIEM query generation module for Splunk, Elastic, Sentinel."""
```

**Verification**:
- Run `pytest tests/ -v`
- Run `grep -r "from playbooks.playbook_engine" backend/` (should be empty)

**Git Commit**: `refactor(playbooks): rename playbook_engine.py to siem_query_generator.py`

---

#### Step 3.2: Standardize dag_json vs definition_json
**Goal**: Consistent naming in API and models

**Files Modified**:
- `backend/models/playbook_definition.py`
- `backend/schemas/playbook_dag.py`
- `backend/routers/playbook_definitions.py`

**Changes**:
1. Add property alias in model (already exists)
2. Update API responses to use `dag_json`
3. Update schema field names

**Verification**:
- Run API tests
- Check OpenAPI spec shows consistent naming

**Git Commit**: `refactor(api): standardize dag_json naming across model and API`

---

### Phase 4: Test Coverage (Week 5)

#### Step 4.1: Add Tests for run_queue_manager.py
**Goal**: 80%+ coverage for queue management

**New Files**:
- `backend/tests/test_run_queue_manager.py`

**Test Cases**:
- Test `can_start_run()` with various concurrent counts
- Test `recover_runs()` with orphaned runs
- Test idempotency key handling
- Test queue overflow behavior

**Verification**:
- Run `pytest tests/test_run_queue_manager.py -v --cov=services/run_queue_manager`

**Git Commit**: `test(run-queue): add comprehensive tests for run_queue_manager`

---

#### Step 4.2: Add Tests for DAGCanvas Component
**Goal**: Key rendering scenarios covered

**New Files**:
- `frontend/components/dag/__tests__/DAGCanvas.test.tsx`

**Test Cases**:
- Renders empty DAG
- Renders nodes with statuses
- Handles definition changes
- Max update depth protection works

**Verification**:
- Run `cd frontend && npm run test`

**Git Commit**: `test(dag-canvas): add component tests for DAGCanvas`

---

## 5. New Directory Structure

### 5.1 Backend (After Refactoring)

```
backend/
+-- main.py
+-- core/
|   +-- config.py
|   +-- logger.py
|   +-- security.py
|   +-- validators.py
+-- db/
|   +-- session.py
+-- dependencies/
|   +-- auth.py
+-- middleware/
|   +-- exception_handler.py
|   +-- trace_middleware.py
+-- models/
|   +-- __init__.py
|   +-- user.py
|   +-- asset.py
|   +-- playbook.py          # Consolidated playbook models
|   +-- history.py
+-- repositories/
|   +-- playbook.py          # Consolidated playbook repos
|   +-- user.py
|   +-- asset.py
+-- schemas/
|   +-- playbook.py          # Consolidated playbook schemas
|   +-- alert.py
|   +-- asset.py
+-- services/
|   +-- alert_service.py
|   +-- asset_service.py
|   +-- playbook_run_service.py
|   +-- run_queue_manager.py
|   +-- ai_service.py
+-- routers/
|   +-- playbook.py          # Run endpoints
|   +-- playbook_definitions.py
|   +-- alert.py
|   +-- assets.py
+-- playbook_engine/
|   +-- __init__.py
|   +-- adapter.py
|   +-- plugins/             # Flattened from v7_dag/plugins
|   |   +-- builtin_*.py
|   +-- dag/
|   |   +-- engine.py        # Slimmed down
|   |   +-- executor.py      # Extracted
|   |   +-- context.py       # Extracted
|   |   +-- compiler.py      # Moved from services
|   |   +-- scheduler.py     # Moved from services
|   |   +-- exceptions.py
|   |   +-- retry_policy.py
|   +-- triggers/
|   +-- notifications/
+-- playbooks/
|   +-- siem_query_generator.py  # Renamed
|   +-- query_templates.py
+-- integrations/
|   +-- otx_client.py
+-- tests/
    +-- conftest.py
    +-- test_run_queue_manager.py  # New
    +-- test_v0_7_dag.py
```

### 5.2 Frontend (After Refactoring)

```
frontend/
+-- app/
|   +-- page.tsx
|   +-- playbooks/
|   |   +-- page.tsx
|   |   +-- definitions/
|   |       +-- [id]/
|   |           +-- page.tsx
|   +-- triggers/
|   +-- assets/
+-- components/
|   +-- dag/
|   |   +-- DAGCanvas.tsx
|   |   +-- DAGNode.tsx
|   |   +-- __tests__/
|   |       +-- DAGCanvas.test.tsx  # New
+-- lib/
|   +-- api/
|   |   +-- index.ts         # Re-exports
|   |   +-- client.ts        # Base client
|   |   +-- types/
|   |   |   +-- alert.ts
|   |   |   +-- asset.ts
|   |   |   +-- playbook.ts
|   |   |   +-- trigger.ts
|   |   +-- modules/
|   |       +-- alert.ts
|   |       +-- asset.ts
|   |       +-- playbook.ts
|   |       +-- trigger.ts
|   +-- types.ts             # Common types
|   +-- auth.ts
|   +-- errors.ts
+-- hooks/
|   +-- useAutoSave.ts
+-- e2e/
    +-- playbooks/
        +-- playbook.spec.ts
```

---

## 6. Verification Standards

### 6.1 Per-Phase Verification Checklist

#### Phase 0 (P0 Fixes)
- [ ] All 500 errors log full traceback
- [ ] DAGCanvas renders without console errors
- [ ] Idempotency key prevents duplicate runs
- [ ] `pytest tests/ -v` passes
- [ ] `npm run build` succeeds

#### Phase 1 (Schema Consolidation)
- [ ] No duplicate schema definitions
- [ ] All imports updated
- [ ] OpenAPI spec consistent
- [ ] `pytest tests/ -v` passes

#### Phase 2 (File Splitting)
- [ ] `api.ts` under 500 lines
- [ ] `engine.py` under 300 lines
- [ ] All imports work correctly
- [ ] `npm run lint` passes

#### Phase 3 (Naming Cleanup)
- [ ] No naming conflicts
- [ ] API responses consistent
- [ ] Documentation updated

#### Phase 4 (Test Coverage)
- [ ] `run_queue_manager.py` coverage > 80%
- [ ] DAGCanvas component tests pass
- [ ] All existing tests still pass

### 6.2 Global Verification Commands

```bash
# Backend
cd backend
pytest tests/ -v --cov=. --cov-report=html
ruff check .
mypy .

# Frontend
cd frontend
npm run build
npm run lint
npm run test
```

### 6.3 Regression Test Matrix

| Feature | Test Command | Expected Result |
|---------|--------------|-----------------|
| Alert Analysis | `pytest tests/test_alert_analysis.py -v` | All pass |
| DAG Execution | `pytest tests/test_v0_7_dag.py -v` | All pass |
| Auth Flow | `pytest tests/test_middleware.py -v` | All pass |
| Frontend Build | `npm run build` | No errors |
| E2E Playbook | `npx playwright test e2e/playbooks/` | All pass |

---

## Appendix A: File Change Summary

| Phase | Files Added | Files Modified | Files Removed |
|-------|-------------|----------------|---------------|
| 0 | 0 | 4 | 0 |
| 1 | 0 | 5 | 0 |
| 2 | 12 | 20 | 0 |
| 3 | 0 | 10 | 0 |
| 4 | 2 | 0 | 0 |
| **Total** | **14** | **39** | **0** |

---

## Appendix B: Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Import breakage during split | Medium | High | Run tests after each change |
| Type mismatches in frontend | Low | Medium | TypeScript strict mode |
| API contract changes | Low | High | Keep existing endpoints, add new |
| Performance regression | Low | Medium | Benchmark critical paths |

---

*End of Document*