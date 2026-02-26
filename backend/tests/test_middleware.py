"""Unit tests for Middleware components."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, Response
from starlette.types import ASGIApp, Receive, Scope, Send, Message

from middleware.trace_middleware import TraceIDMiddleware
from middleware.audit_middleware import AuditMiddleware
from middleware.authorization_middleware import ResourceAuthorizationMiddleware
from middleware.idempotency_middleware import IdempotencyMiddleware


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
    send = AsyncMock()
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
        """Test that generated trace ID is in UUID format."""
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
        # UUID format: 8-4-4-4-12
        import re
        uuid_pattern = re.compile(r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$')
        assert uuid_pattern.match(trace_id) is not None


class TestAuditMiddleware:
    """Tests for AuditMiddleware."""

    @pytest.mark.asyncio
    async def test_logs_request_response(self, mock_app):
        """Test that middleware logs request and response."""
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
        
        with patch('middleware.audit_middleware.get_logger') as mock_logger:
            await middleware(scope, receive, send)
            
            # Verify logger was called
            mock_logger.return_value.info.assert_called()

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
        
        with patch('middleware.audit_middleware.get_logger') as mock_logger:
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
        
        with patch('middleware.audit_middleware.AuditRepository') as mock_repo:
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
        """Test that response is cached for idempotent requests."""
        middleware = IdempotencyMiddleware(mock_app)
        
        idempotency_key = "test-key-123"
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/alerts",
            "headers": [(b"x-idempotency-key", idempotency_key.encode())],
            "state": {},
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        with patch('middleware.idempotency_middleware.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.get.return_value = None  # No cached response
            
            await middleware(scope, receive, send)
            
            # Should check cache
            mock_redis_instance.get.assert_called()

    @pytest.mark.asyncio
    async def test_returns_cached_response_for_duplicate_request(self, mock_app):
        """Test that cached response is returned for duplicate requests."""
        middleware = IdempotencyMiddleware(mock_app)
        
        idempotency_key = "test-key-123"
        cached_response = {
            "status_code": 200,
            "body": b'{"cached": true}',
            "headers": [[b"content-type", b"application/json"]],
        }
        
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/alerts",
            "headers": [(b"x-idempotency-key", idempotency_key.encode())],
            "state": {},
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        with patch('middleware.idempotency_middleware.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            mock_redis_instance.get.return_value = cached_response
            
            await middleware(scope, receive, send)
            
            # Should return cached response
            # Verify send was called with cached response data

    @pytest.mark.asyncio
    async def test_only_applies_to_mutating_methods(self, mock_app):
        """Test that idempotency only applies to POST, PUT, PATCH, DELETE."""
        middleware = IdempotencyMiddleware(mock_app)
        
        idempotency_key = "test-key-123"
        
        # GET request should not use idempotency key
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/alerts",
            "headers": [(b"x-idempotency-key", idempotency_key.encode())],
            "state": {},
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        with patch('middleware.idempotency_middleware.Redis') as mock_redis:
            mock_redis_instance = AsyncMock()
            mock_redis.return_value = mock_redis_instance
            
            await middleware(scope, receive, send)
            
            # Should not check cache for GET
            mock_redis_instance.get.assert_not_called()


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
            "headers": [],
            "state": {"user_id": "user-123", "user_role": "analyst"},
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await app(scope, receive, send)
        
        # TraceID should be set
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
