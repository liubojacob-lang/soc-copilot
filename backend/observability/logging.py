"""Global JSON logging bootstrap for backend services."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime

from observability.context import get_request_id, get_tenant_id, get_trace_id


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", None) or get_trace_id(),
            "request_id": getattr(record, "request_id", None) or get_request_id(),
            "tenant_id": getattr(record, "tenant_id", None) or get_tenant_id(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class ContextInjectFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id()
        record.request_id = get_request_id()
        record.tenant_id = get_tenant_id()
        return True


def setup_json_logging(level: str | None = None) -> None:
    """Configure root logger to JSON format with context fields.

    v1.0: Delegates to core/logger.py for unified logging configuration.
    The standalone JsonLogFormatter/ContextInjectFilter are kept for backward
    compatibility but core/logger.py is the canonical implementation.
    """
    from core.logger import setup_logger as _setup_logger

    log_level = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    _setup_logger(log_level)
