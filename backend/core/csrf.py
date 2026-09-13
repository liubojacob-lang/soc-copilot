"""CSRF protection using double-submit cookie pattern."""

import hashlib
import secrets

from fastapi import HTTPException, Request, status
from fastapi.responses import Response

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# CSRF cookie name
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"

# Method types that require CSRF protection
CSRF_PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def hash_csrf_token(token: str) -> str:
    """Hash CSRF token for storage in cookie."""
    return hashlib.sha256(token.encode()).hexdigest()


def set_csrf_cookie(response: Response, token: str) -> None:
    """Set CSRF cookie (not httpOnly so JavaScript can read it)."""
    secure = (
        settings.cookie_secure
        if getattr(settings, "cookie_secure", None) is not None
        else (settings.environment == "production")
    )
    expire_minutes = getattr(settings, "jwt_expire_minutes", 720)
    max_age = int(expire_minutes * 60)

    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=hash_csrf_token(token),
        httponly=False,  # Must be readable by JavaScript
        secure=secure,
        samesite="lax",
        max_age=max_age,
        path="/",
    )


async def validate_csrf(request: Request) -> None:
    """Validate CSRF token for protected methods.

    Uses double-submit pattern:
    1. Server sends CSRF token to client (in cookie or response body)
    2. Client includes token in X-CSRF-Token header
    3. Server validates header matches cookie hash
    """
    # Only validate for state-changing methods
    if request.method not in CSRF_PROTECTED_METHODS:
        return

    # Skip CSRF for API key authentication (API keys are their own security)
    if "x-api-key" in request.headers:
        return

    # Skip Bearer token authenticated requests (CSRF is only needed for cookie-based auth)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return

    # Get CSRF token from header
    csrf_token = request.headers.get(CSRF_HEADER_NAME)
    if not csrf_token:
        logger.warning(
            f"CSRF token missing from header for {request.method} {request.url.path}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token missing. Include X-CSRF-Token header.",
        )

    # Get CSRF cookie hash
    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    if not csrf_cookie:
        logger.warning(f"CSRF cookie missing for {request.method} {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF cookie missing. Ensure cookies are enabled.",
        )

    # Validate token matches hash (support both hashed cookie and raw cookie fallback)
    expected_hash = hash_csrf_token(csrf_token)
    if not (
        secrets.compare_digest(expected_hash, csrf_cookie)
        or secrets.compare_digest(csrf_token, csrf_cookie)
    ):
        logger.warning(f"CSRF token mismatch for {request.method} {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token validation failed.",
        )


def get_csrf_middleware(exempt_paths: set[str] | None = None):
    """Create CSRF middleware dependency.

    Args:
        exempt_paths: Set of paths to exempt from CSRF validation
    """
    exempt_paths = exempt_paths or {
        "/api/auth/login",
        "/api/v1/auth/login",
        "/api/auth/login-2fa",
        "/api/v1/auth/login-2fa",
        "/api/auth/refresh",
        "/api/v1/auth/refresh",
        "/api/health",
        "/api/v1/health",
        "/docs",
        "/openapi.json",
    }

    async def csrf_protected(request: Request) -> None:
        """CSRF protection middleware."""
        # Skip exempt paths
        if request.url.path in exempt_paths:
            return

        # Skip GET, HEAD, OPTIONS (safe methods)
        if request.method not in CSRF_PROTECTED_METHODS:
            return

        # Skip API key authentication
        if "x-api-key" in request.headers:
            return

        await validate_csrf(request)

    return csrf_protected
