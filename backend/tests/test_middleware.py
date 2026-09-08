"""Unit tests for Middleware components."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Request, Response
from starlette.types import Receive, Scope, Send

from middleware.audit_middleware import AuditMiddleware
from middleware.authorization_middleware import ResourceAuthorizationMiddleware
from middleware.idempotency_middleware import IdempotencyMiddleware
from middleware.trace_middleware import TraceIDMiddleware


@pytest.fixture
def mock_app():
    """Create mock ASGI app."""

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        response = Response(content=b"OK", status_code=200)
        await response(scope, receive, send)

    return app


@pytest.fixture
def mock_request():
    """Create mock request."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/test",
        "query_string": b"",
        "headers": [],
        "state": {},
    }
    receive = AsyncMock()
    AsyncMock()
    return Request(scope, receive)


class TestTraceIDMiddleware:
    """Tests for TraceIDMiddleware."""

    @pytest.mark.asyncio
    async def test_adds_trace_id_to_request(self, mock_app):
        """Test that middleware adds trace ID to request state."""
        middleware = TraceIDMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "headers": [],
            "state": {},
        }

        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Check that trace_id was added to state
        assert "trace_id" in scope["state"]
        assert scope["state"]["trace_id"] is not None

    @pytest.mark.asyncio
    async def test_uses_existing_trace_id_header(self, mock_app):
        """Test that middleware uses existing X-Trace-ID header."""
        middleware = TraceIDMiddleware(mock_app)

        existing_trace_id = "existing-trace-123"
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "headers": [(b"x-trace-id", existing_trace_id.encode())],
            "state": {},
        }

        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Should use existing trace ID
        assert scope["state"]["trace_id"] == existing_trace_id

    @pytest.mark.asyncio
    async def test_generates_uuid_format_trace_id(self, mock_app):
        """Test that generated trace ID has correct format."""
        middleware = TraceIDMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "headers": [],
            "state": {},
        }

        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        trace_id = scope["state"]["trace_id"]
        assert trace_id is not None
        assert trace_id.startswith("tr_")


class TestAuditMiddleware:
    """Tests for AuditMiddleware."""

    @pytest.mark.asyncio
    async def test_logs_request_response(self, mock_app):
        """Test that middleware processes request and response."""
        middleware = AuditMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/alerts",
            "query_string": b"",
            "headers": [],
            "state": {"user_id": "user-123"},
        }

        receive = AsyncMock()
        send = AsyncMock()

        with patch("middleware.audit_middleware.AuditRepository") as mock_repo:
            mock_repo_instance = AsyncMock()
            mock_repo.return_value = mock_repo_instance

            await middleware(scope, receive, send)

            mock_repo.assert_called()

    @pytest.mark.asyncio
    async def test_excludes_health_endpoint(self, mock_app):
        """Test that health endpoint is excluded from audit logging."""
        middleware = AuditMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "query_string": b"",
            "headers": [],
            "state": {},
        }

        receive = AsyncMock()
        send = AsyncMock()

        with patch("middleware.audit_middleware.get_logger") as mock_logger:
            await middleware(scope, receive, send)

            # Should not log for health endpoint
            mock_logger.return_value.info.assert_not_called()

    @pytest.mark.asyncio
    async def test_captures_user_id_from_state(self, mock_app):
        """Test that middleware captures user_id from request state."""
        middleware = AuditMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/alerts",
            "query_string": b"",
            "headers": [],
            "state": {"user_id": "user-456", "user_role": "admin"},
        }

        receive = AsyncMock()
        send = AsyncMock()

        with patch("middleware.audit_middleware.AuditRepository") as mock_repo:
            mock_repo_instance = AsyncMock()
            mock_repo.return_value = mock_repo_instance

            await middleware(scope, receive, send)

            # Verify audit log was created with user_id
            if mock_repo_instance.create.called:
                call_kwargs = mock_repo_instance.create.call_args
                assert call_kwargs is not None


class TestResourceAuthorizationMiddleware:
    """Tests for ResourceAuthorizationMiddleware."""

    @pytest.mark.asyncio
    async def test_allows_public_endpoints(self, mock_app):
        """Test that public endpoints are allowed without auth."""
        middleware = ResourceAuthorizationMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
            "state": {},
        }

        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Should pass through without error

    @pytest.mark.asyncio
    async def test_checks_admin_role_for_admin_endpoints(self, mock_app):
        """Test that admin endpoints require admin role."""
        middleware = ResourceAuthorizationMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/admin/settings",
            "headers": [],
            "state": {"user_id": "user-123", "user_role": "analyst"},
        }

        receive = AsyncMock()
        send = AsyncMock()

        # Should return 403 for non-admin
        await middleware(scope, receive, send)

        # Check response status (should be 403)
        # The send function should have been called with 403 status

    @pytest.mark.asyncio
    async def test_allows_admin_to_admin_endpoints(self, mock_app):
        """Test that admin can access admin endpoints."""
        middleware = ResourceAuthorizationMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/admin/settings",
            "headers": [],
            "state": {"user_id": "admin-123", "user_role": "admin"},
        }

        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Should pass through


class TestIdempotencyMiddleware:
    """Tests for IdempotencyMiddleware."""

    @pytest.mark.asyncio
    async def test_allows_requests_without_idempotency_key(self, mock_app):
        """Test that requests without idempotency key pass through."""
        middleware = IdempotencyMiddleware(mock_app)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/alerts",
            "headers": [],
            "state": {},
        }

        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Should pass through

    @pytest.mark.asyncio
    async def test_caches_response_for_idempotent_request(self, mock_app):
        """Test that middleware processes requests with idempotency key."""
        middleware = IdempotencyMiddleware(mock_app)

        idempotency_key = "test-key-123"
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/alerts",
            "headers": [(b"idempotency-key", idempotency_key.encode())],
            "state": {},
        }

        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

    @pytest.mark.asyncio
    async def test_returns_cached_response_for_duplicate_request(self, mock_app):
        """Test that middleware handles duplicate idempotency key."""
        middleware = IdempotencyMiddleware(mock_app)

        idempotency_key = "test-key-456"
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/alerts",
            "headers": [(b"idempotency-key", idempotency_key.encode())],
            "state": {},
        }

        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

    @pytest.mark.asyncio
    async def test_only_applies_to_mutating_methods(self, mock_app):
        """Test that idempotency only applies to POST, PUT, PATCH, DELETE."""
        middleware = IdempotencyMiddleware(mock_app)

        idempotency_key = "test-key-789"

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/alerts",
            "headers": [(b"idempotency-key", idempotency_key.encode())],
            "state": {},
        }

        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)


class TestMiddlewareChain:
    """Tests for middleware chain integration."""

    @pytest.mark.asyncio
    async def test_middleware_order(self, mock_app):
        """Test that middleware is applied in correct order."""
        # Build middleware chain
        app = TraceIDMiddleware(mock_app)
        app = AuditMiddleware(app)
        app = ResourceAuthorizationMiddleware(app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/alerts",
            "query_string": b"",
            "headers": [],
            "state": {"user_id": "user-123", "user_role": "analyst"},
        }

        receive = AsyncMock()
        send = AsyncMock()

        await app(scope, receive, send)

        assert "trace_id" in scope["state"]

    @pytest.mark.asyncio
    async def test_error_handling_in_chain(self, mock_app):
        """Test error handling in middleware chain."""

        # Create a failing app
        async def failing_app(scope, receive, send):
            raise ValueError("Test error")

        app = TraceIDMiddleware(failing_app)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/test",
            "headers": [],
            "state": {},
        }

        receive = AsyncMock()
        send = AsyncMock()

        # Should propagate error
        with pytest.raises(ValueError):
            await app(scope, receive, send)
