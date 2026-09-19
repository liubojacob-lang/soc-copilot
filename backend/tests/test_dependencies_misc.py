"""Unit tests for tenant/query/siem/audit dependency helpers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from dependencies.audit import AuditContext, audit_context
from dependencies.query import paginated_query
from dependencies.siem import get_siem_service
from dependencies.tenant import get_tenant_id
from repositories.audit_repository import AuditRepository

pytestmark = [pytest.mark.unit]


def make_request(method="POST", path="/api/things", auth_header=None):
    headers = {}
    if auth_header is not None:
        headers["authorization"] = auth_header
    request = MagicMock()
    request.method = method
    request.url = Mock(path=path)
    request.headers = headers
    return request


class TestGetTenantId:
    async def test_returns_tenant_from_request_state(self):
        request = MagicMock()
        request.state = SimpleNamespace(tenant_id="acme")
        assert await get_tenant_id(request) == "acme"

    async def test_defaults_when_state_has_no_tenant(self):
        request = MagicMock()
        request.state = SimpleNamespace()
        assert await get_tenant_id(request) == "default"

    def test_client_supplied_header_is_ignored(self):
        """There is no tenant model yet, so ``x-tenant-id`` must not be trusted.

        Honouring it lets any client relabel its own logs and metrics.
        """
        from middleware.tenant_middleware import resolve_tenant_id

        request = make_request()
        request.headers["x-tenant-id"] = "victim-tenant"
        request.state = SimpleNamespace()
        assert resolve_tenant_id(request) == "default"


class TestPaginatedQuery:
    async def test_maps_explicit_values(self):
        params = await paginated_query(
            page=3, page_size=50, sort_by="created_at", sort_order="asc"
        )
        assert params.page == 3
        assert params.page_size == 50
        assert params.sort_by == "created_at"
        assert params.sort_order == "asc"

    async def test_maps_partial_values(self):
        params = await paginated_query(
            page=2, page_size=10, sort_by=None, sort_order="desc"
        )
        assert params.page == 2
        assert params.page_size == 10
        assert params.sort_by is None
        assert params.sort_order == "desc"


class TestGetSiemService:
    async def test_elasticsearch_backend_when_available(self, monkeypatch):
        check = AsyncMock(return_value=True)
        monkeypatch.setattr("dependencies.siem.check_es_availability", check)
        session = AsyncMock(spec=AsyncSession)

        result = await get_siem_service(session)

        assert result == {
            "session": session,
            "backend": "elasticsearch",
            "es_available": True,
        }
        check.assert_awaited_once()

    async def test_sqlite_backend_when_es_unavailable(self, monkeypatch):
        check = AsyncMock(return_value=False)
        monkeypatch.setattr("dependencies.siem.check_es_availability", check)
        session = AsyncMock(spec=AsyncSession)

        result = await get_siem_service(session)

        assert result["backend"] == "sqlite"
        assert result["es_available"] is False


class TestAuditContextCommit:
    def make_context(self, session):
        return AuditContext(
            repo=AuditRepository(session),
            action="user:create",
            method="POST",
            path="/api/users",
            user_id="user-1",
            target_type="user",
            extra={"source": "test"},
        )

    async def test_commit_writes_audit_record(self):
        session = AsyncMock(spec=AsyncSession)
        context = self.make_context(session)

        await context.commit(target_id="u-42", extra={"name": "alice"})

        session.add.assert_called_once()
        record = session.add.call_args.args[0]
        assert record.action == "user:create"
        assert record.method == "POST"
        assert record.path == "/api/users"
        assert record.status_code == 200
        assert record.user_id == "user-1"
        assert record.target_type == "user"
        assert record.target_id == "u-42"
        assert record.extra_json == {"source": "test", "name": "alice"}
        session.commit.assert_awaited_once()

    async def test_commit_is_idempotent(self):
        session = AsyncMock(spec=AsyncSession)
        context = self.make_context(session)

        await context.commit()
        await context.commit(status_code=500, extra={"later": True})

        assert session.add.call_count == 1
        session.commit.assert_awaited_once()

    async def test_commit_status_code_override(self):
        session = AsyncMock(spec=AsyncSession)
        context = self.make_context(session)

        await context.commit(status_code=201)

        record = session.add.call_args.args[0]
        assert record.status_code == 201


class TestAuditContextFactory:
    async def test_extracts_user_from_bearer_token(self, monkeypatch):
        monkeypatch.setattr(
            "core.security.decode_token",
            lambda token: {"sub": "user-123"},
        )
        create = audit_context("user:create", target_type="user")

        context = await create(
            make_request(auth_header="Bearer valid-token"),
            AsyncMock(spec=AsyncSession),
        )

        assert context.user_id == "user-123"
        assert context.action == "user:create"
        assert context.target_type == "user"
        assert context.method == "POST"
        assert context.path == "/api/things"

    async def test_missing_auth_header_yields_anonymous(self, monkeypatch):
        monkeypatch.setattr(
            "core.security.decode_token",
            lambda token: {"sub": "user-123"},
        )
        create = audit_context("playbook:run")

        context = await create(
            make_request(), AsyncMock(spec=AsyncSession)
        )

        assert context.user_id is None

    async def test_decode_failure_is_swallowed(self, monkeypatch):
        def boom(token):
            raise ValueError("bad token")

        monkeypatch.setattr("core.security.decode_token", boom)
        create = audit_context("playbook:run")

        context = await create(
            make_request(auth_header="Bearer garbage"),
            AsyncMock(spec=AsyncSession),
        )

        assert context.user_id is None

    async def test_none_payload_yields_anonymous(self, monkeypatch):
        monkeypatch.setattr("core.security.decode_token", lambda token: None)
        create = audit_context("playbook:run")

        context = await create(
            make_request(auth_header="Bearer token"),
            AsyncMock(spec=AsyncSession),
        )

        assert context.user_id is None
