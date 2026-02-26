"""Middleware package."""

from middleware.audit_middleware import AuditMiddleware
from middleware.trace_middleware import (
    TraceIDMiddleware,
    TraceIDFilter,
    get_trace_id,
    set_trace_id,
    setup_trace_logging,
)
from middleware.exception_handler import (
    ErrorResponse,
    setup_exception_handlers,
)
from middleware.idempotency_middleware import IdempotencyMiddleware
from middleware.authorization_middleware import (
    ResourceAuthorizationMiddleware,
    ResourceOwnerChecker,
    check_resource_ownership,
    require_resource_ownership,
)
from middleware.csrf_middleware import (
    CSRFMiddleware,
    setup_csrf_middleware,
)
from middleware.request_context_middleware import RequestContextMiddleware
from middleware.observability_middleware import ObservabilityMiddleware
from middleware.exception_middleware import ExceptionCaptureMiddleware

__all__ = [
    "AuditMiddleware",
    "TraceIDMiddleware",
    "TraceIDFilter",
    "get_trace_id",
    "set_trace_id",
    "setup_trace_logging",
    "ErrorResponse",
    "setup_exception_handlers",
    "IdempotencyMiddleware",
    "ResourceAuthorizationMiddleware",
    "ResourceOwnerChecker",
    "check_resource_ownership",
    "require_resource_ownership",
    "CSRFMiddleware",
    "setup_csrf_middleware",
    "RequestContextMiddleware",
    "ObservabilityMiddleware",
    "ExceptionCaptureMiddleware",
]
