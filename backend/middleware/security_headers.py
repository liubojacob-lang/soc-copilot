"""Security headers middleware for HTTP responses."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from core.logger import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security-related HTTP headers to all responses.

    Headers added:
    - Content-Security-Policy: Prevents XSS and data injection attacks
    - X-Frame-Options: Prevents clickjacking
    - X-Content-Type-Options: Prevents MIME type sniffing
    - Strict-Transport-Security: Forces HTTPS connections
    - X-XSS-Protection: Legacy XSS protection (deprecated but still useful)
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Restricts browser features
    """

    def __init__(
        self,
        app: ASGIApp,
        csp_policy: str | None = None,
        hsts_max_age: int = 31536000,
        frame_options: str = "DENY",
        enable_hsts: bool = True,
    ):
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.frame_options = frame_options
        self.enable_hsts = enable_hsts

        if csp_policy:
            self.csp_policy = csp_policy
        else:
            self.csp_policy = self._get_default_csp()

    def _get_default_csp(self) -> str:
        return (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss: https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "object-src 'none'; "
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = self.frame_options
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )

        if "Content-Security-Policy" not in response.headers:
            response.headers["Content-Security-Policy"] = self.csp_policy

        if self.enable_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            )

        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        logger.debug(f"Security headers added for {request.url.path}")

        return response


class APISecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Simplified security headers middleware for API-only responses.
    Less restrictive CSP for API endpoints.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"

        return response
