"""Global exception handlers for unified error responses.

This module provides:
- Unified error response format
- Proper HTTP status codes
- Trace ID inclusion for debugging
- Sensitive information filtering
"""

import traceback
from typing import Union, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from core.logger import get_logger
from middleware.trace_middleware import get_trace_id

logger = get_logger(__name__)


class ErrorResponse:
    """Standard error response format.
    
    Attributes:
        error: Error type identifier
        message: Human-readable error message
        detail: Additional error details (optional)
        trace_id: Request trace ID for debugging
        status_code: HTTP status code
    """
    
    def __init__(
        self,
        error: str,
        message: str,
        status_code: int,
        detail: Any = None,
        trace_id: str = None,
    ):
        self.error = error
        self.message = message
        self.status_code = status_code
        self.detail = detail
        self.trace_id = trace_id or get_trace_id()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response."""
        result = {
            "error": self.error,
            "code": self.error,
            "message": self.message,
            "trace_id": self.trace_id,
            "request_id": getattr(self, "request_id", None),
        }
        if self.detail is not None:
            result["detail"] = self.detail
        return result
    
    def to_response(self) -> JSONResponse:
        """Create JSON response."""
        return JSONResponse(
            status_code=self.status_code,
            content=self.to_dict(),
            headers={"X-Trace-ID": self.trace_id} if self.trace_id else None,
        )


def sanitize_error_detail(detail: Any) -> Any:
    """Sanitize error details to remove sensitive information.
    
    Args:
        detail: Original error detail
        
    Returns:
        Sanitized detail safe for client display
    """
    if isinstance(detail, str):
        # Remove potential sensitive patterns
        sensitive_patterns = [
            "password",
            "secret",
            "token",
            "api_key",
            "authorization",
            "credential",
        ]
        detail_lower = detail.lower()
        for pattern in sensitive_patterns:
            if pattern in detail_lower:
                return "Sensitive information redacted"
        return detail
    
    if isinstance(detail, dict):
        return {k: sanitize_error_detail(v) for k, v in detail.items()}
    
    if isinstance(detail, list):
        return [sanitize_error_detail(item) for item in detail]
    
    return detail


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors.
    
    Args:
        request: The request that caused the error
        exc: The validation error
        
    Returns:
        JSON response with validation error details
    """
    trace_id = get_trace_id()
    
    # Extract validation errors
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    
    logger.warning(
        f"[{trace_id}] Validation error: {len(errors)} errors",
        extra={"errors": errors, "path": request.url.path},
    )
    
    error = ErrorResponse(
        error="validation_error",
        message="Request validation failed",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=errors,
        trace_id=trace_id,
    )
    error.request_id = request.headers.get("X-Request-ID")
    return error.to_response()


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions.
    
    Args:
        request: The request that caused the error
        exc: The HTTP exception
        
    Returns:
        JSON response with error details
    """
    trace_id = get_trace_id()
    
    # Map status codes to error types
    error_type_map = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        405: "method_not_allowed",
        409: "conflict",
        422: "unprocessable_entity",
        429: "rate_limited",
        500: "internal_error",
        502: "bad_gateway",
        503: "service_unavailable",
    }
    
    error_type = error_type_map.get(exc.status_code, "http_error")
    
    # Log based on status code severity
    if exc.status_code >= 500:
        logger.error(
            f"[{trace_id}] HTTP {exc.status_code}: {exc.detail}",
            extra={"path": request.url.path, "method": request.method},
        )
    elif exc.status_code >= 400:
        logger.warning(
            f"[{trace_id}] HTTP {exc.status_code}: {exc.detail}",
            extra={"path": request.url.path, "method": request.method},
        )
    
    error = ErrorResponse(
        error=error_type,
        message=str(exc.detail) if exc.detail else "HTTP error",
        status_code=exc.status_code,
        trace_id=trace_id,
    )
    error.request_id = request.headers.get("X-Request-ID")
    return error.to_response()


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors.
    
    Args:
        request: The request that caused the error
        exc: The SQLAlchemy error
        
    Returns:
        JSON response with generic database error message
    """
    trace_id = get_trace_id()
    
    # Log full error for debugging (not exposed to client)
    logger.error(
        f"[{trace_id}] Database error: {type(exc).__name__}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc(),
        },
    )
    
    # Return generic message to avoid exposing database details
    error = ErrorResponse(
        error="database_error",
        message="A database error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        trace_id=trace_id,
    )
    error.request_id = request.headers.get("X-Request-ID")
    return error.to_response()


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions.
    
    This is the catch-all handler for any exception not caught by more specific handlers.
    
    Args:
        request: The request that caused the error
        exc: The exception
        
    Returns:
        JSON response with generic error message
    """
    trace_id = get_trace_id()
    
    # P0-1: Improved error logging with full traceback in message
    # This ensures traceback is visible in all log aggregation systems
    tb_str = traceback.format_exc()
    logger.error(
        f"[{trace_id}] Unhandled exception: {type(exc).__name__}: {str(exc)}\n"
        f"Path: {request.url.path} | Method: {request.method}\n"
        f"Traceback:\n{tb_str}",
        exc_info=True,  # Ensure traceback is captured by logging handlers
    )
    
    # Return generic message to avoid exposing internal details
    error = ErrorResponse(
        error="internal_error",
        message="An unexpected error occurred. Please try again later.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        trace_id=trace_id,
    )
    error.request_id = request.headers.get("X-Request-ID")
    return error.to_response()


def setup_exception_handlers(app):
    """Register all exception handlers with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    # Register handlers in order of specificity
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Global exception handlers registered")
