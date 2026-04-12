"""Middleware package."""

from middleware.audit_middleware import AuditMiddleware
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
from middleware.exception_handler import (
    api_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    setup_exception_handlers,
    sqlalchemy_exception_handler,
    validation_exception_handler,
)
from middleware.exception_middleware import ExceptionCaptureMiddleware
from middleware.idempotency_middleware import IdempotencyMiddleware
from middleware.observability_middleware import ObservabilityMiddleware
from middleware.request_context_middleware import RequestContextMiddleware
from middleware.trace_middleware import (
    TraceIDFilter,
    TraceIDMiddleware,
    get_trace_id,
    set_trace_id,
    setup_trace_logging,
)

__all__ = [
    "AuditMiddleware",
    "CSRFMiddleware",
    "ExceptionCaptureMiddleware",
    "IdempotencyMiddleware",
    "ObservabilityMiddleware",
    "RequestContextMiddleware",
    "ResourceAuthorizationMiddleware",
    "ResourceOwnerChecker",
    "TraceIDFilter",
    "TraceIDMiddleware",
    "api_exception_handler",
    "check_resource_ownership",
    "generic_exception_handler",
    "get_trace_id",
    "http_exception_handler",
    "require_resource_ownership",
    "set_trace_id",
    "setup_csrf_middleware",
    "setup_exception_handlers",
    "setup_trace_logging",
    "sqlalchemy_exception_handler",
    "validation_exception_handler",
]
