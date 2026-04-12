"""Audit middleware for automatic request logging with sensitive data redaction."""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.logger import get_logger
from core.sensitive_data import redact_dict, redact_headers, redact_request_body
from repositories.audit_repository import AuditRepository

logger = get_logger(__name__)

# Paths to exclude from audit logging
EXCLUDED_PATHS = {
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/auth/logout",
    "/api/health",
    "/health",
    "/metrics",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/audit-logs",  # Audit viewing doesn't need to be audited
    "/api/audit-logs/stats",  # Audit stats queries
    "/favicon.ico",
    "/_next",  # Next.js static files
    "/static",
}

# Paths where request body should not be logged at all
BODY_EXCLUDED_PATHS = {
    "/api/auth/login",
    "/api/auth/change-password",
    "/api/secrets",
    "/api/admin/secrets",
}

# Maximum body size to capture (in bytes)
MAX_BODY_SIZE = 100000

# Methods that typically have request bodies
METHODS_WITH_BODY = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically log all API requests with sensitive data redaction."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.excluded_paths = EXCLUDED_PATHS
        self.body_excluded_paths = BODY_EXCLUDED_PATHS

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log to audit table."""
        start_time = time.time()
        path = request.url.path
        method = request.method

        # Skip excluded paths
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)

        # Get request info
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        user_id = getattr(request.state, "user_id", None)
        trace_id = getattr(request.state, "trace_id", None)

        # Get safe query params (exclude sensitive data)
        query_params = self._sanitize_params(dict(request.query_params))

        # Capture request body for applicable methods
        request_body = None
        content_type = request.headers.get("content-type", "")

        if method in METHODS_WITH_BODY and not any(
            path.startswith(excluded) for excluded in self.body_excluded_paths
        ):
            request_body = await self._capture_request_body(request, content_type)

        try:
            response = await call_next(request)
            duration_ms = int((time.time() - start_time) * 1000)

            # Log the request
            await self._log_audit(
                request=request,
                response=response,
                user_id=user_id,
                method=method,
                path=path,
                status_code=response.status_code,
                ip_address=client_ip,
                user_agent=user_agent,
                duration_ms=duration_ms,
                query_params=query_params,
                request_body=request_body,
                trace_id=trace_id,
            )

            return response

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Request failed: {method} {path} - {e}")

            # Log failed request - never block the request due to audit logging failures
            try:
                await self._log_audit(
                    request=request,
                    response=None,
                    user_id=user_id,
                    method=method,
                    path=path,
                    status_code=500,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    duration_ms=duration_ms,
                    query_params=query_params,
                    request_body=request_body,
                    trace_id=trace_id,
                    error=str(e),
                )
            except Exception as log_error:
                # Audit logging failure should NEVER block the request
                logger.error(f"Failed to log audit (non-blocking): {log_error}")

            # Re-raise the original exception to maintain error handling
            raise

    async def _capture_request_body(
        self, request: Request, content_type: str
    ) -> str | None:
        """
        Capture and redact request body.

        Args:
            request: FastAPI request object
            content_type: Content-Type header value

        Returns:
            Redacted request body string or None
        """
        try:
            # Check content length
            content_length = int(request.headers.get("content-length", 0))
            if content_length > MAX_BODY_SIZE:
                return f"[body too large: {content_length} bytes]"

            if content_length == 0:
                return None

            # Read body
            body = await request.body()
            if not body:
                return None

            # Redact sensitive data
            return redact_request_body(body, content_type, MAX_BODY_SIZE)

        except Exception as e:
            logger.warning(f"Failed to capture request body: {e}")
            return f"[body capture failed: {e!s}]"

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for proxy headers
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _sanitize_params(self, params: dict) -> dict:
        """Remove sensitive parameters from query params."""
        return redact_dict(params)

    async def _log_audit(
        self,
        request: Request,
        response: Response | None,
        user_id: str | None,
        method: str,
        path: str,
        status_code: int,
        ip_address: str,
        user_agent: str,
        duration_ms: int,
        query_params: dict,
        request_body: str | None = None,
        trace_id: str | None = None,
        error: str | None = None,
    ) -> None:
        """Write audit log to database."""
        try:
            # Get session from app state
            from db.session import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                audit_repo = AuditRepository(session)

                # Determine action
                action = self._get_action(method, path)

                # Build extra JSON with request details
                extra_json = {
                    "query_params": query_params,
                    "trace_id": trace_id,
                }

                # Add request body if captured
                if request_body:
                    extra_json["request_body"] = request_body

                # Add response info
                if response:
                    extra_json["response_status"] = status_code

                    # Capture response headers (redacted)
                    response_headers = dict(response.headers)
                    extra_json["response_headers"] = redact_headers(response_headers)

                if error:
                    extra_json["error"] = error

                await audit_repo.create(
                    action=action,
                    method=method,
                    path=path,
                    status_code=status_code,
                    user_id=user_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    duration_ms=duration_ms,
                    extra_json=extra_json,
                )

                await session.commit()

        except Exception as e:
            # Don't fail the request if audit logging fails
            logger.error(f"Audit logging failed: {e}")

    def _get_action(self, method: str, path: str) -> str:
        """Determine audit action from method and path."""
        # Extract resource type from path
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            resource = parts[1]  # e.g., "users", "playbook"
        else:
            resource = "unknown"

        # Map to actions
        action_map = {
            "GET": f"{resource}:read",
            "POST": f"{resource}:create",
            "PATCH": f"{resource}:update",
            "PUT": f"{resource}:update",
            "DELETE": f"{resource}:delete",
        }
        return action_map.get(method, f"{resource}:{method.lower()}")
