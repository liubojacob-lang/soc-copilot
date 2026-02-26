"""Trace ID middleware for request tracking.

This middleware injects a unique trace_id into each request for:
- Request correlation across services
- Log aggregation and search
- Debugging and troubleshooting
"""

import uuid
import contextvars
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.logger import get_logger

logger = get_logger(__name__)

# Context variable to store trace_id for current request
# This allows access to trace_id anywhere in the request lifecycle
trace_id_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)


def get_trace_id() -> Optional[str]:
    """Get the current request's trace_id from context.
    
    Returns:
        The trace_id for the current request, or None if not in a request context.
    """
    return trace_id_context.get()


def set_trace_id(trace_id: str) -> None:
    """Set the trace_id for the current request context.
    
    Args:
        trace_id: The trace_id to set
    """
    trace_id_context.set(trace_id)


class TraceIDMiddleware(BaseHTTPMiddleware):
    """Middleware to inject trace_id into each request.
    
    Features:
    - Generates unique trace_id for each request
    - Accepts trace_id from X-Trace-ID header (for distributed tracing)
    - Adds trace_id to response headers
    - Sets trace_id in context variable for logging
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Trace-ID"):
        """Initialize the middleware.
        
        Args:
            app: The ASGI application
            header_name: The header name for trace_id (default: X-Trace-ID)
        """
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and inject trace_id.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            The response with trace_id header
        """
        # Check if trace_id is provided in request header (for distributed tracing)
        trace_id = request.headers.get(self.header_name)
        
        # Generate new trace_id if not provided
        if not trace_id:
            trace_id = f"tr_{uuid.uuid4().hex[:24]}"
        
        # Set trace_id in context variable
        set_trace_id(trace_id)
        
        # Store trace_id in request state for access in handlers
        request.state.trace_id = trace_id
        
        # Process request
        try:
            response = await call_next(request)
        finally:
            # Clear trace_id from context after request completes
            trace_id_context.set(None)
        
        # Add trace_id to response headers
        response.headers[self.header_name] = trace_id
        
        return response


class TraceIDFilter:
    """Logging filter to add trace_id to log records.
    
    Add this filter to your logger to automatically include trace_id
    in all log messages within a request context.
    """
    
    def filter(self, record) -> bool:
        """Add trace_id to the log record.
        
        Args:
            record: The log record to modify
            
        Returns:
            Always returns True to allow the record to be logged
        """
        record.trace_id = get_trace_id() or "no-trace"
        return True


def setup_trace_logging():
    """Configure logging to include trace_id in all log messages.
    
    This should be called during application startup to ensure
    all loggers include the trace_id filter.
    """
    import logging
    
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Add the filter to all handlers
    trace_filter = TraceIDFilter()
    for handler in root_logger.handlers:
        handler.addFilter(trace_filter)
    
    # Also add to our app logger
    app_logger = logging.getLogger("app")
    for handler in app_logger.handlers:
        handler.addFilter(trace_filter)
    
    logger.info("Trace ID logging configured")
