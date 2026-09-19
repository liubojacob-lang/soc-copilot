"""Unit tests for DAGExecutionEngine execution paths (faked session/registry)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

import playbook_engine.dag.engine as engine_module
from playbook_engine.dag.engine import DAGBuilder, DAGExecutionEngine
from playbook_engine.dag.exceptions import NodeTimeoutError
from playbook_engine.dag.retry_policy import RetryResult

pytestmark = [pytest.mark.unit]


class AsyncStep:
    """Async step implementation with canned result or error."""

    def __init__(self, result=None, error=None):
        self.result = result if result is not None else {"ok": True}
        self.error = error
        self.calls = []

    async def execute(self, inputs, mode):
        self.calls.append((inputs, mode))
        if self.error is not None:
            raise self.error
        return self.result


class SyncStep(AsyncStep):
    def execute(self, inputs, mode):
        self.calls.append((inputs, mode))
        if self.error is not None:
            raise self.error
        return self.result


class StubRegistry:
    def __init__(self, steps):
        self._steps = steps

    def get_step_implementation(self, step_id):
        if step_id not in self._steps:
            raise ValueError(f"No implementation registered for step: {step_id}")
        return self._steps[step_id]


def make_session() -> AsyncMock:
    """AsyncMock session whose selects resolve to no rows."""
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = Mock(scalar_one_or_none=Mock(return_value=None))
    return session


def one_node_definition(step_id="noop", **node_extra):
    node = {"id": "n1", "step_id": step_id, **node_extra}
    return DAGBuilder.from_json({"nodes": [node], "edges": []})


@pytest.fixture
def run_repo_update(monkeypatch):
    """Patch PlaybookRunRepository (imported inside engine methods)."""
    update_mock = AsyncMock()

    class StubRepo:
        def __init__(self, session):
            self.session = session

        async def update(self, run_id, update_data):
            await update_mock(run_id, update_data)

    monkeypatch.setattr(
        "repositories.playbook_run_repository.PlaybookRunRepository", StubRepo
    )
    return update_mock


def make_engine(session, registry):
    engine = DAGExecutionEngine(session=session)
    engine.registry = registry
    return engine


class TestExecuteDagSuccess:
    async def test_single_node_success(self, run_repo_update):
        session = make_session()
        step = AsyncStep(result={"found": 3})
        engine = make_engine(session, StubRegistry({"noop": step}))
        definition = one_node_definition()

        result = await engine.execute_dag(
            definition, "run-1", {"playbook_name": "demo", "tenant_id": "acme"}
        )

        assert result["status"] == "success"
        assert result["failed_nodes"] == []
        assert result["skipped_nodes"] == []
        assert result["outputs"]["n1"] == {"found": 3}
        assert step.calls[0][1] == "dry_run"
        run_repo_update.assert_awaited_once()
        assert run_repo_update.call_args.args[1]["status"] == "success"

    async def test_sync_step_supported(self, run_repo_update):
        session = make_session()
        step = SyncStep(result={"sync": True})
        engine = make_engine(session, StubRegistry({"noop": step}))

        result = await engine.execute_dag(
            one_node_definition(), "run-1", {"playbook_name": "demo"}
        )

        assert result["status"] == "success"
        assert result["outputs"]["n1"] == {"sync": True}

    async def test_inputs_template_rendered_for_node(
        self, run_repo_update, monkeypatch
    ):
        from services.playbook.playbook_context_service import context_service

        monkeypatch.setattr(
            context_service,
            "render_node_inputs",
            lambda template, ctx: {"rendered": template},
        )
        session = make_session()
        step = AsyncStep(result={"ok": True})
        engine = make_engine(session, StubRegistry({"noop": step}))
        definition = one_node_definition(inputs_template={"ioc": "{{input.ioc}}"})

        result = await engine.execute_dag(
            definition, "run-1", {"playbook_name": "demo", "ioc": "1.2.3.4"}
        )

        assert result["status"] == "success"
        inputs, _ = step.calls[0]
        assert inputs == {"rendered": {"ioc": "{{input.ioc}}"}}

    async def test_outputs_mapping_merges_context(self, run_repo_update, monkeypatch):
        from services.playbook.playbook_context_service import context_service

        monkeypatch.setattr(
            context_service,
            "merge_node_output",
            lambda ctx, node_id, output, mapping: {**ctx, "merged": True},
        )
        session = make_session()
        step = AsyncStep(result={"value": 1})
        engine = make_engine(session, StubRegistry({"noop": step}))
        definition = one_node_definition(outputs_mapping={"value": "ctx.value"})

        result = await engine.execute_dag(
            definition, "run-1", {"playbook_name": "demo"}
        )

        assert result["status"] == "success"
        run_repo_update.assert_awaited_once()
        assert run_repo_update.call_args.args[1]["context_json"]["merged"] is True

    async def test_retry_policy_success_after_transient_failure(self, run_repo_update):
        session = make_session()
        step = AsyncMock(spec=AsyncStep)
        step.execute = AsyncMock(side_effect=[RuntimeError("transient"), {"ok": True}])
        engine = make_engine(session, StubRegistry({"noop": step}))
        definition = one_node_definition(
            retry_policy={
                "max_attempts": 2,
                "backoff_base": 0,
                "backoff_max": 0,
                "timeout": 5,
            }
        )

        result = await engine.execute_dag(
            definition, "run-1", {"playbook_name": "demo"}
        )

        assert result["status"] == "success"
        assert step.execute.await_count == 2
        retry_result = result["outputs"]["n1"]
        assert isinstance(retry_result, RetryResult)
        assert retry_result.attempt_number == 2


class TestExecuteDagFailure:
    async def test_generic_exception_marks_run_failed(self, run_repo_update):
        session = make_session()
        step = AsyncStep(error=RuntimeError("boom"))
        engine = make_engine(session, StubRegistry({"noop": step}))

        result = await engine.execute_dag(
            one_node_definition(), "run-1", {"playbook_name": "demo"}
        )

        assert result["status"] == "failed"
        assert result["failed_nodes"] == ["n1"]
        assert result["outputs"] == {}
        run_repo_update.assert_awaited_once()
        assert run_repo_update.call_args.args[1]["status"] == "failed"

    async def test_structured_dag_error_uses_to_dict(self, run_repo_update):
        session = make_session()
        step = AsyncStep(
            error=NodeTimeoutError(node_id="n1", step_id="noop", timeout_seconds=300)
        )
        engine = make_engine(session, StubRegistry({"noop": step}))

        result = await engine.execute_dag(
            one_node_definition(), "run-1", {"playbook_name": "demo"}
        )

        assert result["status"] == "failed"
        assert result["failed_nodes"] == ["n1"]
        assert engine._node_states["n1"].state.value == "failed"

    async def test_step_timeout_error_branch(self, run_repo_update):
        session = make_session()
        step = AsyncStep(error=TimeoutError())
        engine = make_engine(session, StubRegistry({"noop": step}))

        result = await engine.execute_dag(
            one_node_definition(), "run-1", {"playbook_name": "demo"}
        )

        assert result["status"] == "failed"
        assert result["failed_nodes"] == ["n1"]

    async def test_unknown_step_id_fails_node(self, run_repo_update):
        session = make_session()
        engine = make_engine(session, StubRegistry({}))

        result = await engine.execute_dag(
            one_node_definition(step_id="missing"), "run-1", {"playbook_name": "demo"}
        )

        assert result["status"] == "failed"
        assert result["failed_nodes"] == ["n1"]


class TestExecuteDagTimeout:
    async def test_global_timeout_skips_remaining_nodes(
        self, run_repo_update, monkeypatch
    ):
        monkeypatch.setattr(engine_module, "DAG_GLOBAL_TIMEOUT_SECONDS", 0)
        session = make_session()
        step = AsyncStep()
        engine = make_engine(session, StubRegistry({"noop": step}))

        result = await engine.execute_dag(
            one_node_definition(), "run-1", {"playbook_name": "demo"}
        )

        assert result["status"] == "timeout"
        assert result["skipped_nodes"] == ["n1"]
        assert step.calls == []
        assert "Global timeout exceeded" in result["error"]

    async def test_node_skipped_when_global_timeout_already_exceeded(
        self, run_repo_update, monkeypatch
    ):
        monkeypatch.setattr(engine_module, "DAG_GLOBAL_TIMEOUT_SECONDS", 0)
        engine = make_engine(make_session(), StubRegistry({"noop": AsyncStep()}))
        start_time = datetime.now(UTC) - timedelta(seconds=10)

        result = await engine._execute_node_with_timeout(
            node_id="n1",
            definition=one_node_definition(),
            run_id="run-1",
            input_json={},
            mode="dry_run",
            start_time=start_time,
        )

        assert result.status == "skipped"
        assert "Global timeout exceeded" in result.error
