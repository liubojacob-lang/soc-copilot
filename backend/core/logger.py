"""
Structured JSON Logger for SOC Copilot.

v0.8.5: Enhanced structured logging with:
- JSON format output for all logs
- Request tracing with trace_id
- User context (user_id, user_role)
- Performance metrics (duration_ms)
- Environment and version info
- Configurable log levels per module
"""

import logging
import sys
import os
from contextvars import ContextVar
from typing import Any, Optional
from datetime import datetime, timezone
try:
    from pythonjsonlogger.json import JsonFormatter
except ImportError:
    from pythonjsonlogger import jsonlogger
    JsonFormatter = jsonlogger.JsonFormatter

# Context variables for request-scoped data
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
user_role_var: ContextVar[str] = ContextVar("user_role", default="")
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="default")


class StructuredLogFilter(logging.Filter):
    """Filter that adds structured context to log records."""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add request context
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.user_role = user_role_var.get()
        record.trace_id = trace_id_var.get()
        record.tenant_id = tenant_id_var.get()
        
        # Add timestamp in ISO format
        record.timestamp = datetime.now(timezone.utc).isoformat()
        
        # Add environment info
        record.environment = os.getenv("ENVIRONMENT", "development")
        record.service = "soc-copilot"
        
        return True


class StructuredJsonFormatter(JsonFormatter):
    """Custom JSON formatter with structured fields."""
    
    def __init__(self, *args, **kwargs):
        # Define the fields to include in JSON output
        json_fields = [
            "timestamp",
            "level",
            "logger",
            "message",
            "request_id",
            "trace_id",
            "user_id",
            "user_role",
            "tenant_id",
            "environment",
            "service",
            "duration_ms",
            "extra",
        ]
        super().__init__(
            " ".join(f"%({field})s" for field in json_fields),
            *args,
            **kwargs
        )
    
    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict):
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Ensure level is uppercase
        log_record["level"] = record.levelname
        
        # Use logger name as the module
        log_record["logger"] = record.name
        
        # Handle extra fields from extra parameter
        if hasattr(record, "extra") and record.extra:
            log_record["extra"] = record.extra


class StructuredLogger(logging.Logger):
    """Custom logger with structured logging support."""
    
    def _log_with_context(
        self,
        level: int,
        msg: str,
        *args,
        duration_ms: Optional[float] = None,
        **kwargs
    ):
        """Log with additional context."""
        extra = kwargs.pop("extra", {})
        
        if duration_ms is not None:
            extra["duration_ms"] = duration_ms
        
        # Create log record with extra
        record = self.makeRecord(
            self.name, level, "", 0, msg, args, None, None
        )
        record.extra = extra
        
        self.handle(record)
    
    def info_with_context(self, msg: str, **kwargs):
        """Log info with context."""
        self._log_with_context(logging.INFO, msg, **kwargs)
    
    def warning_with_context(self, msg: str, **kwargs):
        """Log warning with context."""
        self._log_with_context(logging.WARNING, msg, **kwargs)
    
    def error_with_context(self, msg: str, **kwargs):
        """Log error with context."""
        self._log_with_context(logging.ERROR, msg, **kwargs)
    
    def debug_with_context(self, msg: str, **kwargs):
        """Log debug with context."""
        self._log_with_context(logging.DEBUG, msg, **kwargs)


def setup_logger(name: str = "soc_copilot", level: str = "INFO") -> logging.Logger:
    """Set up a structured JSON logger.
    
    Args:
        name: Logger name (typically __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    # Set custom logger class
    logging.setLoggerClass(StructuredLogger)
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    if not logger.handlers:
        # Create stdout handler with JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        handler.addFilter(StructuredLogFilter())
        logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get or create a structured logger.
    
    Args:
        name: Logger name, typically __name__
    
    Returns:
        Logger instance with structured output
    """
    return setup_logger(name)


def set_request_context(
    request_id: str,
    user_id: Optional[str] = None,
    user_role: Optional[str] = None,
    trace_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
):
    """Set context variables for the current request.
    
    This should be called at the beginning of each request.
    
    Args:
        request_id: Unique request identifier
        user_id: Current user ID (if authenticated)
        user_role: Current user role (if authenticated)
    """
    request_id_var.set(request_id)
    user_id_var.set(user_id or "")
    user_role_var.set(user_role or "")
    trace_id_var.set(trace_id or "")
    tenant_id_var.set(tenant_id or "default")


def clear_request_context():
    """Clear context variables at the end of a request."""
    request_id_var.set("")
    user_id_var.set("")
    user_role_var.set("")
    trace_id_var.set("")
    tenant_id_var.set("default")


# Convenience functions for structured logging
def log_api_request(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
):
    """Log an API request with structured data."""
    logger.info_with_context(
        f"API Request: {method} {path}",
        extra={
            "type": "api_request",
            "method": method,
            "path": path,
            "status_code": status_code,
        },
        duration_ms=duration_ms,
    )


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    description: str,
    user_id: Optional[str] = None,
    details: Optional[dict] = None,
):
    """Log a security-related event."""
    logger.warning_with_context(
        f"Security Event: {event_type} - {description}",
        extra={
            "type": "security_event",
            "event_type": event_type,
            "details": details or {},
        },
    )


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration_ms: float,
    threshold_ms: float = 200.0,
):
    """Log a performance metric."""
    level = logging.WARNING if duration_ms > threshold_ms else logging.INFO
    logger._log_with_context(
        level,
        f"Performance: {operation} took {duration_ms:.2f}ms",
        extra={
            "type": "performance",
            "operation": operation,
        },
        duration_ms=duration_ms,
    )
