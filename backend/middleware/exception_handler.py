"""Global exception handlers for unified error responses.

This module provides:
- Unified error response format using schemas.common.ErrorResponse
- Proper HTTP status codes
- Trace ID inclusion for debugging
- Sensitive information filtering
- APIException integration with error codes
"""

import traceback
from typing import Union, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

from core.logger import get_logger
from core.exceptions import APIException
from middleware.trace_middleware import get_trace_id
from schemas.common import ErrorResponse, ErrorDetail

logger = get_logger(__name__)


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


async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """Handle APIException with unified error response format.
    
    Args:
        request: The request that caused error
        exc: The APIException
        
    Returns:
        JSON response with error details using ErrorResponse format
    """
    trace_id = get_trace_id()
    
    # Extract error details from APIException
    error_code = str(exc.code)
    error_message = exc.detail.get("message", "Error") if isinstance(exc.detail, dict) else str(exc.detail)
    error_detail = exc.details if hasattr(exc, 'details') else None
    
    # Sanitize error details
    if error_detail:
        error_detail = sanitize_error_detail(error_detail)
    
    # Log based on status code severity
    if exc.status_code >= 500:
        logger.error(
            f"[{trace_id}] API Exception: {error_code} - {error_message}",
            extra={"path": request.url.path, "code": error_code, "detail": error_detail}
        )
    elif exc.status_code >= 400:
        logger.warning(
            f"[{trace_id}] API Exception: {error_code} - {error_message}",
            extra={"path": request.url.path, "code": error_code}
        )
    
    error = ErrorResponse(
        code=error_code,
        message=error_message,
        detail=error_detail,
        trace_id=trace_id,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error.model_dump(mode='json'),
        headers={"X-Trace-ID": trace_id} if trace_id else None
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors.
    
    Args:
        request: The request that caused the error
        exc: The validation error
        
    Returns:
        JSON response with validation error details using ErrorResponse format
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
        code="VALIDATION_ERROR",
        message="Request validation failed",
        detail=errors,
        trace_id=trace_id,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error.model_dump(mode='json'),
        headers={"X-Trace-ID": trace_id} if trace_id else None
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions.
    
    Args:
        request: The request that caused error
        exc: The HTTP exception
        
    Returns:
        JSON response with error details using ErrorResponse format
    """
    trace_id = get_trace_id()
    
    # Map status codes to error types
    error_type_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
    }
    
    error_code = error_type_map.get(exc.status_code, "HTTP_ERROR")
    
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
        code=error_code,
        message=str(exc.detail) if exc.detail else "HTTP error",
        trace_id=trace_id,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error.model_dump(mode='json'),
        headers={"X-Trace-ID": trace_id} if trace_id else None
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy database errors.
    
    Args:
        request: The request that caused error
        exc: The SQLAlchemy error
        
    Returns:
        JSON response with generic database error message using ErrorResponse format
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
        code="DATABASE_ERROR",
        message="A database error occurred. Please try again later.",
        trace_id=trace_id,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error.model_dump(mode='json'),
        headers={"X-Trace-ID": trace_id} if trace_id else None
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions.
    
    This is the catch-all handler for any exception not caught by more specific handlers.
    
    Args:
        request: The request that caused error
        exc: The exception
        
    Returns:
        JSON response with generic error message using ErrorResponse format
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
        code="INTERNAL_ERROR",
        message="An unexpected error occurred. Please try again later.",
        trace_id=trace_id,
        request_id=request.headers.get("X-Request-ID")
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error.model_dump(mode='json'),
        headers={"X-Trace-ID": trace_id} if trace_id else None
    )


def setup_exception_handlers(app):
    """Register all exception handlers with the FastAPI app.
    
    Handlers are registered in order of specificity:
    1. APIException - Custom application exceptions with error codes
    2. RequestValidationError - Pydantic validation errors
    3. HTTPException - FastAPI HTTP exceptions
    4. SQLAlchemyError - Database errors
    5. Exception - Catch-all for unhandled exceptions
    
    Args:
        app: FastAPI application instance
    """
    # Register handlers in order of specificity
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Global exception handlers registered (including APIException handler)")
