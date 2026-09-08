"""
Comprehensive tests for Playbook DAG Compiler, DAG Execution Service,
and DAG validation & scheduling mechanics.
"""

from __future__ import annotations

import uuid

import pytest

from db.session import AsyncSessionLocal, init_db
from models.playbook_definition import PlaybookDefinitionModel
from repositories.playbook_definition_repository import PlaybookDefinitionRepository
from repositories.playbook_run_repository import PlaybookRunRepository
from schemas.playbook_run import (
    DAGPlaybookRunCreate,
    DAGPlaybookRunResponse,
    PlaybookRunErrorResponse,
)
from services.playbook.dag_execution_service import DAGExecutionService
from services.playbook.playbook_dag_compiler import DAGCompiler, DAGValidationError


@pytest.fixture(autouse=True)
async def setup_database():
    await init_db()


@pytest.fixture(autouse=True)
async def seed_reference_users(setup_database, client):
    """Create users referenced by created_by_user_id / created_by columns.

    Depends on the session-scoped client so the app lifespan (and its
    bootstrap admin creation) always runs before extra users are inserted —
    bootstrap is skipped when the users table is not empty.
    """
    import secrets

    from sqlalchemy import select

    from models.user import UserModel

    async with AsyncSessionLocal() as session:
        for user_id in ("admin-user", "analyst-user", "test-user"):
            exists = await session.scalar(
                select(UserModel.id).where(UserModel.id == user_id)
            )
            if exists:
                continue
            # Non-login fixture user: runtime-generated placeholder hash —
            # authentication never runs in this suite.
            credentials = {"hashed_password": secrets.token_urlsafe(16)}
            session.add(
                UserModel(
                    id=user_id,
                    username=user_id,
                    email=f"{user_id}@example.com",
                    role="admin",
                    is_active=True,
                    **credentials,
                )
            )
        await session.commit()
    yield


# ─────────────────────────────────────────────────────────────
# 1. DAGCompiler Unit Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dag_compiler_valid_dag():
    valid_dag = {
        "nodes": [
            {"id": "node_1", "type": "extract_iocs", "name": "Extract IOCs"},
            {"id": "node_2", "type": "ti_lookup_otx", "name": "Threat Intel Lookup"},
            {"id": "node_3", "type": "decision", "name": "Evaluate Severity"},
            {"id": "node_4", "type": "slack_notify", "name": "Alert SOC Channel"},
        ],
        "edges": [
            {"source": "node_1", "target": "node_2"},
            {"source": "node_2", "target": "node_3"},
            {"source": "node_3", "target": "node_4"},
        ],
    }

    compiled = await DAGCompiler.validate_and_compile(valid_dag)
    assert compiled is not None
    assert compiled["node_count"] == 4
    assert compiled["edge_count"] == 3
    # Check root and leaf nodes
    assert "node_1" in compiled["root_nodes"]
    assert "node_4" in compiled["leaf_nodes"]


@pytest.mark.asyncio
async def test_dag_compiler_missing_nodes_or_edges():
    with pytest.raises(DAGValidationError, match="DAG must contain 'nodes' array"):
        await DAGCompiler.validate_and_compile({"edges": []})

    with pytest.raises(DAGValidationError, match="DAG must contain 'edges' array"):
        await DAGCompiler.validate_and_compile({"nodes": []})


@pytest.mark.asyncio
async def test_dag_compiler_duplicate_node_ids():
    invalid_dag = {
        "nodes": [
            {"id": "duplicate_id", "type": "extract_iocs"},
            {"id": "duplicate_id", "type": "decision"},
        ],
        "edges": [],
    }
    with pytest.raises(DAGValidationError, match="Duplicate node ID"):
        await DAGCompiler.validate_and_compile(invalid_dag)


@pytest.mark.asyncio
async def test_dag_compiler_unknown_node_type():
    invalid_dag = {
        "nodes": [
            {"id": "node_unknown", "type": "unsupported_crypto_miner"},
        ],
        "edges": [],
    }
    with pytest.raises(DAGValidationError, match="Unknown node type"):
        await DAGCompiler.validate_and_compile(invalid_dag)


@pytest.mark.asyncio
async def test_dag_compiler_missing_edge_target():
    invalid_dag = {
        "nodes": [
            {"id": "node_a", "type": "sleep"},
        ],
        "edges": [
            {"source": "node_a", "target": "node_b"},  # node_b does not exist
        ],
    }
    with pytest.raises(DAGValidationError, match="Edge target node not found: node_b"):
        await DAGCompiler.validate_and_compile(invalid_dag)


@pytest.mark.asyncio
async def test_dag_compiler_cycle_detection():
    cyclic_dag = {
        "nodes": [
            {"id": "n1", "type": "http_request"},
            {"id": "n2", "type": "decision"},
            {"id": "n3", "type": "risk_score"},
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n2", "target": "n3"},
            {"source": "n3", "target": "n1"},  # Creates cycle: n1 -> n2 -> n3 -> n1
        ],
    }
    with pytest.raises(DAGValidationError, match="Cyclic dependency detected"):
        await DAGCompiler.validate_and_compile(cyclic_dag)


# ─────────────────────────────────────────────────────────────
# 2. DAGExecutionService Unit & Integration Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dag_execution_service_permission_check():
    async with AsyncSessionLocal() as session:
        service = DAGExecutionService(session)

        req = DAGPlaybookRunCreate(
            mode="apply",
            input_context={"alert_id": "ALT-123"},
            failure_strategy="fail_fast",
        )

        # Non-admin executing in apply mode should be rejected
        resp = await service.execute(
            definition_id="fake-def-id",
            data=req,
            current_user_id="analyst-user",
            current_username="analyst",
            current_user_role="analyst",
        )

        assert isinstance(resp, PlaybookRunErrorResponse)
        assert resp.success is False
        assert resp.error_code == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_dag_execution_service_definition_not_found():
    async with AsyncSessionLocal() as session:
        service = DAGExecutionService(session)

        req = DAGPlaybookRunCreate(
            mode="dry_run",
            input_context={},
            failure_strategy="fail_fast",
        )

        resp = await service.execute(
            definition_id="def-nonexistent",
            data=req,
            current_user_id="admin-user",
            current_username="admin",
            current_user_role="admin",
        )

        assert isinstance(resp, PlaybookRunErrorResponse)
        assert resp.success is False
        assert resp.error_code == "DEFINITION_NOT_FOUND"


@pytest.mark.asyncio
async def test_dag_execution_service_inactive_definition():
    async with AsyncSessionLocal() as session:
        defn_repo = PlaybookDefinitionRepository(session)
        created_defn = await defn_repo.create(
            name="Inactive Quarantine Playbook",
            description="Quarantine infected endpoint",
            dag_json={
                "nodes": [{"id": "step1", "type": "extract_iocs"}],
                "edges": [],
            },
            version="1.0.0",
            is_active=False,  # Inactive!
            created_by_user_id="admin-user",
        )
        await session.commit()

        service = DAGExecutionService(session)
        req = DAGPlaybookRunCreate(
            mode="dry_run",
            input_context={},
            failure_strategy="fail_fast",
        )

        resp = await service.execute(
            definition_id=created_defn.id,
            data=req,
            current_user_id="admin-user",
            current_username="admin",
            current_user_role="admin",
        )

        assert isinstance(resp, PlaybookRunErrorResponse)
        assert resp.success is False
        assert resp.error_code == "DEFINITION_INACTIVE"


@pytest.mark.asyncio
async def test_dag_execution_service_dry_run_success():
    async with AsyncSessionLocal() as session:
        defn_repo = PlaybookDefinitionRepository(session)
        valid_dag = {
            "nodes": [
                {"id": "step_ioc", "type": "extract_iocs", "name": "Extract IOCs"},
                {"id": "step_score", "type": "risk_score", "name": "Calculate Risk"},
            ],
            "edges": [
                {"source": "step_ioc", "target": "step_score"},
            ],
        }

        defn = await defn_repo.create(
            name="Automated Triage Playbook",
            description="Triage alerts with risk score",
            dag_json=valid_dag,
            version="1.0.0",
            is_active=True,
            created_by_user_id="admin-user",
        )
        await session.commit()

        service = DAGExecutionService(session)
        req = DAGPlaybookRunCreate(
            mode="dry_run",
            input_context={"alert_title": "Suspicious PowerShell Execution"},
            failure_strategy="continue",
        )

        resp = await service.execute(
            definition_id=defn.id,
            data=req,
            current_user_id="analyst-user",
            current_username="analyst",
            current_user_role="analyst",  # dry_run is allowed for analysts!
        )

        assert isinstance(resp, DAGPlaybookRunResponse)
        assert resp.mode == "dry_run"
        assert resp.playbook_name == "Automated Triage Playbook"
        assert resp.status in ("completed", "dry_run", "success")
        assert resp.total_nodes == 2
        assert resp.completed_nodes == 2


# ─────────────────────────────────────────────────────────────
# 3. PlaybookRunRepository Unit Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_playbook_run_repository_crud(seed_reference_users):
    async with AsyncSessionLocal() as session:
        # definition_id carries an FK to playbook_definitions — create a real one
        definition = PlaybookDefinitionModel(
            id=str(uuid.uuid4()),
            name="FK Fixture Definition",
            description="repository crud test fixture",
            definition_json={"nodes": [], "edges": []},
            created_by="test-user",
            is_active=True,
        )
        session.add(definition)
        await session.commit()

        repo = PlaybookRunRepository(session)

        run = await repo.create(
            playbook_name="Firewall Block Playbook",
            playbook_version="1.0.0",
            mode="dry_run",
            input_json={"ip": "1.2.3.4"},
            created_by_user_id="test-user",
            engine_version="v0.7",
            execution_mode="dag",
            definition_id=definition.id,
            failure_strategy="fail_fast",
        )
        await session.commit()
        await session.commit()

        assert run.id is not None
        assert run.playbook_name == "Firewall Block Playbook"
        assert run.mode == "dry_run"

        fetched = await repo.get_by_id(run.id)
        assert fetched is not None
        assert fetched.id == run.id

        runs, total = await repo.list_runs(limit=10)
        assert total >= 1
        assert any(r.id == run.id for r in runs)
