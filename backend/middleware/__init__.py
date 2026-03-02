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
    setup_exception_handlers,
    api_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    generic_exception_handler,
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
    "setup_exception_handlers",
    "api_exception_handler",
    "validation_exception_handler",
    "http_exception_handler",
    "sqlalchemy_exception_handler",
    "generic_exception_handler",
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
