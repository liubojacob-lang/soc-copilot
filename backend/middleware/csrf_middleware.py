"""CSRF Protection Middleware.

Validates CSRF tokens for mutating requests (POST, PUT, DELETE, PATCH).
Uses double-submit cookie pattern for protection.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from core.logger import get_logger
from services.cookie_auth import validate_csrf_token

logger = get_logger(__name__)

# Paths that don't require CSRF validation
CSRF_EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/refresh",
    "/api/auth/logout",
    "/api/health",
    "/api/ready",
    "/metrics",
    "/docs",
    "/openapi.json",
}

# Methods that don't require CSRF validation
CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware for CSRF protection using double-submit cookie pattern.
    
    For mutating requests (POST, PUT, DELETE, PATCH):
    1. Reads CSRF token from cookie
    2. Reads CSRF token from X-CSRF-Token header
    3. Validates they match
    
    If validation fails, returns 403 Forbidden.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exempt_paths: set = None,
        safe_methods: set = None,
    ):
        """Initialize CSRF middleware.
        
        Args:
            app: ASGI application
            exempt_paths: Paths that don't require CSRF validation
            safe_methods: HTTP methods that don't require CSRF validation
        """
        super().__init__(app)
        self.exempt_paths = exempt_paths or CSRF_EXEMPT_PATHS
        self.safe_methods = safe_methods or CSRF_SAFE_METHODS
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request through CSRF validation.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response from handler or 403 if CSRF validation fails
        """
        # Skip CSRF for safe methods
        if request.method in self.safe_methods:
            return await call_next(request)
        
        # Skip CSRF for exempt paths
        path = request.url.path
        if path in self.exempt_paths:
            return await call_next(request)
        
        # Skip CSRF for paths starting with exempt prefixes
        for exempt_path in self.exempt_paths:
            if path.startswith(exempt_path):
                return await call_next(request)
        
        # Skip CSRF for webhook endpoints (they have their own validation)
        if path.startswith("/api/webhooks/"):
            return await call_next(request)
        
        # Skip CSRF for API key authenticated requests
        # API keys are sent via header, not cookie
        if request.headers.get("X-API-Key"):
            return await call_next(request)
        
        # Validate CSRF token
        if not validate_csrf_token(request):
            logger.warning(
                f"CSRF validation failed",
                extra={
                    "path": path,
                    "method": request.method,
                    "client_ip": request.client.host if request.client else None,
                }
            )
            
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={
                    "error": "csrf_validation_failed",
                    "message": "CSRF token validation failed. Please refresh the page and try again.",
                },
            )
        
        return await call_next(request)


def setup_csrf_middleware(app, exempt_paths: set = None):
    """Setup CSRF middleware on the FastAPI app.
    
    Args:
        app: FastAPI application
        exempt_paths: Additional paths to exempt from CSRF validation
    """
    all_exempt_paths = CSRF_EXEMPT_PATHS.copy()
    if exempt_paths:
        all_exempt_paths.update(exempt_paths)
    
    app.add_middleware(CSRFMiddleware, exempt_paths=all_exempt_paths)
    logger.info(f"CSRF middleware enabled with {len(all_exempt_paths)} exempt paths")
