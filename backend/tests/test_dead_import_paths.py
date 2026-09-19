"""Regression tests for the three dead execution paths found in the 2026-09-18
architecture review:

1. ``services/trigger_service.py`` imported ``services.playbook_dag_scheduler``
   (nonexistent), so every webhook-triggered playbook run raised
   ``ModuleNotFoundError`` inside the try-block and reported a failed run.
2. ``playbook_engine/triggers/`` imported ``.dag`` (nonexistent inside that
   package) and nothing outside the package referenced it. The package is now
   deleted.
3. ``main.py`` mounted ``routers/websocket.router`` twice (bare and
   ``/api/v1``), registering every WebSocket ops route under two paths and the
   ``/ws/alerts`` endpoint twice.
4. ``main.py`` defined an inline ``GET /api/v1/health`` stub that the router
   mounted at import time already owned, leaving the stub unreachable and
   shadowing the ``routers.health`` module name in ``main``'s namespace.

Test 1 is generalised into a repo-wide static gate so any future typo in a
first-party import path fails CI, not just this one line.
"""

import ast
import base64
import hashlib
import hmac
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {"__pycache__", "htmlcov", ".pytest_cache", "venv", ".venv", "logs", "data"}


def _local_package_names() -> set[str]:
    return {
        p.name
        for p in BACKEND_ROOT.iterdir()
        if p.is_dir() and (p / "__init__.py").exists()
    }


def _iter_source_files():
    for path in BACKEND_ROOT.rglob("*.py"):
        if SKIP_DIRS & set(path.parts):
            continue
        yield path


def _module_target_exists(package_dir: Path, parts: list[str]) -> bool:
    """Filesystem equivalent of importlib.util.find_spec, without executing
    package ``__init__.py`` side effects during collection."""
    candidate = package_dir.joinpath(*parts)
    return candidate.with_suffix(".py").is_file() or (candidate / "__init__.py").is_file()


@pytest.mark.parametrize("source", list(_iter_source_files()), ids=lambda p: str(p.relative_to(BACKEND_ROOT)))
def test_first_party_import_paths_resolve(source: Path):
    """Every import of a first-party module must point at a real file.

    Guards against the ``ModuleNotFoundError`` class of bug that silently
    breaks lazily-imported code paths which no test exercises.
    """
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    local_packages = _local_package_names()
    broken = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom | ast.Import):
            continue

        if isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] in local_packages and len(parts) > 1:
                    if not _module_target_exists(BACKEND_ROOT, parts):
                        broken.append(alias.name)
            continue

        if node.level:
            # Relative: climb `level - 1` packages from the file's own directory.
            base = source.parent
            for _ in range(node.level - 1):
                base = base.parent
            if node.module:
                if not _module_target_exists(base, node.module.split(".")):
                    broken.append(f"{source.parent.name}.{node.module} (level={node.level})")
            continue

        if not node.module:
            continue
        parts = node.module.split(".")
        if parts[0] not in local_packages:
            continue
        if not _module_target_exists(BACKEND_ROOT, parts):
            broken.append(node.module)

    assert not broken, f"{source.relative_to(BACKEND_ROOT)} imports nonexistent modules: {broken}"


def test_playbook_engine_triggers_package_stays_deleted():
    """The superseded trigger package must not come back half-wired.

    ``services/trigger_service.py`` and ``services/cron_scheduler_service.py``
    own this behaviour now.
    """
    assert not (BACKEND_ROOT / "playbook_engine" / "triggers").exists()


def test_websocket_router_registers_each_path_once():
    from main import app

    paths = [getattr(r, "path", "") for r in app.routes]
    ws_paths = [p for p in paths if p.startswith("/ws") or p.startswith("/api/v1/ws")]

    assert ws_paths.count("/ws/alerts") == 1, "/ws/alerts must be mounted exactly once"
    assert "/api/v1/ws/monitoring/metrics" in ws_paths, (
        "MonitoringDashboard calls /api/v1/ws/monitoring/metrics"
    )
    assert "/ws/stats" not in ws_paths, (
        "ops endpoints belong under /api/v1 only; a bare duplicate means the "
        "router got mounted twice again"
    )


def test_no_route_is_registered_twice():
    """No (path, method) pair may have two handlers.

    A second registration is unreachable — Starlette matches in list order —
    so it silently shadows a real endpoint, as ``main.py`` 's inline
    ``GET /api/v1/health`` stub did against ``routers/health.py``.
    """
    from main import app

    handlers: dict[tuple[str, str], list[str]] = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        endpoint = getattr(route, "endpoint", None)
        if path is None or endpoint is None:
            continue
        for method in sorted(getattr(route, "methods", None) or ["WS"]):
            handlers.setdefault((path, method), []).append(
                f"{endpoint.__module__}.{endpoint.__name__}"
            )

    duplicated = {k: v for k, v in handlers.items() if len(v) > 1}
    assert not duplicated, f"shadowed routes: {duplicated}"


@pytest.mark.asyncio
async def test_webhook_trigger_reaches_dag_scheduler(monkeypatch):
    """A signed webhook invocation must construct and await the DAG scheduler.

    Before the fix this path died at the import statement and the run was
    recorded as failed.
    """
    import services.playbook.playbook_dag_scheduler as scheduler_module
    from services.trigger_service import TriggerService

    executed: dict[str, object] = {}

    class RecordingScheduler:
        def __init__(self, **kwargs):
            executed["init_kwargs"] = kwargs
            self.cancelled = False
            self.failed_nodes: list = []

        async def execute(self):
            executed["executed"] = True
            return {"ok": True}

    monkeypatch.setattr(scheduler_module, "DAGScheduler", RecordingScheduler)

    service = TriggerService(session=MagicMock())
    secret = "wh_test_secret"
    trigger = MagicMock(id="trig-1", definition_id="def-1", type="webhook", is_active=True, secret=secret)

    service.trigger_repo.get_by_id = AsyncMock(return_value=trigger)
    service.trigger_repo.check_idempotency = AsyncMock(return_value=None)
    service.trigger_repo.record_invocation = AsyncMock(return_value=MagicMock(id="inv-1"))
    service.trigger_repo.update_invocation = AsyncMock()
    service.trigger_repo.update_last_triggered = AsyncMock()
    service.run_repo.create = AsyncMock(return_value=MagicMock(id="run-1"))
    service.run_repo.update = AsyncMock()
    service.audit_repo.create = AsyncMock()
    service.session.commit = AsyncMock()

    from repositories.playbook_definition_repository import PlaybookDefinitionRepository
    from services.playbook.playbook_dag_compiler import DAGCompiler

    definition = MagicMock(name="phishing-triage", version="1.0.0", definition_json={"nodes": [], "edges": []})
    monkeypatch.setattr(
        PlaybookDefinitionRepository, "get_by_id", AsyncMock(return_value=definition), raising=False
    )
    monkeypatch.setattr(DAGCompiler, "validate_and_compile", AsyncMock(return_value=MagicMock()), raising=False)

    payload = b'{"alert_id": "ALT-1"}'
    signature = base64.b64encode(
        hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    ).decode()

    result = await service.handle_webhook("trig-1", payload, signature=signature)

    assert executed.get("executed") is True, "DAGScheduler.execute() was never awaited"
    assert result["run_id"] == "run-1"
    assert result["status"] == "success"
