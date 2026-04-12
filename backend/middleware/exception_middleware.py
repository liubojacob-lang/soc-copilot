"""Global exception interception middleware for metrics and consistent logging."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.logger import get_logger
from observability.metrics import observe_exception

logger = get_logger(__name__)


class ExceptionCaptureMiddleware(BaseHTTPMiddleware):
    """Capture unhandled exceptions for metrics before FastAPI handlers process them."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            observe_exception(type(exc).__name__, request.url.path)
            logger.error(
                "Unhandled exception intercepted",
                extra={"path": request.url.path, "error": str(exc)},
            )
            raise
