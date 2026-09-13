"""Cookie-based Authentication Service.

Provides secure token storage using HttpOnly cookies to prevent XSS attacks.
Includes CSRF protection for cross-site request forgery prevention.
"""

import hashlib
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, Request, Response, status
from pydantic import BaseModel

from core.config import settings
from core.logger import get_logger
from core.security import create_access_token, create_refresh_token

logger = get_logger(__name__)

# Cookie names
ACCESS_TOKEN_COOKIE = "access_token"
REFRESH_TOKEN_COOKIE = "refresh_token"
CSRF_TOKEN_COOKIE = "csrf_token"

# Cookie settings
COOKIE_MAX_AGE_ACCESS = getattr(settings, "jwt_expire_minutes", 720) * 60
COOKIE_MAX_AGE_REFRESH = getattr(settings, "jwt_refresh_expire_minutes", 10080) * 60
COOKIE_MAX_AGE_CSRF = getattr(settings, "jwt_expire_minutes", 720) * 60

# Security settings
COOKIE_SECURE = (
    settings.cookie_secure
    if getattr(settings, "cookie_secure", None) is not None
    else (settings.environment == "production")
)
COOKIE_HTTPONLY = True
COOKIE_SAMESITE = "lax"  # Protect against CSRF


class CSRFToken(BaseModel):
    """CSRF token model."""

    token: str
    expires_at: datetime


class CookieAuthConfig(BaseModel):
    """Cookie authentication configuration."""

    domain: str | None = None
    secure: bool = COOKIE_SECURE
    httponly: bool = COOKIE_HTTPONLY
    samesite: str = COOKIE_SAMESITE


def get_cookie_domain(request: Request) -> str | None:
    """Get cookie domain based on request host."""
    host = request.headers.get("host", "")
    # In development, don't set domain
    if "localhost" in host or "127.0.0.1" in host:
        return None
    # In production, use the configured domain or extract from host
    if settings.cors_origins:
        # Extract domain from first CORS origin
        first_origin = settings.cors_origins.split(",")[0].strip()
        if "://" in first_origin:
            domain = first_origin.split("://")[1].split("/")[0]
            # Remove port if present
            if ":" in domain:
                domain = domain.split(":")[0]
            return domain
    return None


def generate_csrf_token() -> str:
    """Generate a secure CSRF token."""
    return secrets.token_urlsafe(32)


def hash_csrf_token(token: str) -> str:
    """Hash CSRF token for storage comparison."""
    return hashlib.sha256(token.encode()).hexdigest()


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
    request: Request | None = None,
) -> None:
    """Set authentication cookies on response.

    Args:
        response: FastAPI response object
        access_token: JWT access token
        refresh_token: JWT refresh token
        csrf_token: CSRF token for header validation
        request: Optional request for domain detection
    """
    domain = get_cookie_domain(request) if request else None

    # Set access token cookie (HttpOnly for XSS protection)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        max_age=COOKIE_MAX_AGE_ACCESS,
        domain=domain,
        secure=COOKIE_SECURE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
    )

    # Set refresh token cookie (HttpOnly for XSS protection)
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        max_age=COOKIE_MAX_AGE_REFRESH,
        domain=domain,
        secure=COOKIE_SECURE,
        httponly=COOKIE_HTTPONLY,
        samesite=COOKIE_SAMESITE,
    )

    # Set CSRF token cookie (NOT HttpOnly - needs JS access for headers)
    response.set_cookie(
        key=CSRF_TOKEN_COOKIE,
        value=hash_csrf_token(csrf_token),
        max_age=COOKIE_MAX_AGE_CSRF,
        domain=domain,
        secure=COOKIE_SECURE,
        httponly=False,  # Must be accessible to JavaScript
        samesite=COOKIE_SAMESITE,
    )


def clear_auth_cookies(response: Response, request: Request | None = None) -> None:
    """Clear authentication cookies on logout.

    Args:
        response: FastAPI response object
        request: Optional request for domain detection
    """
    domain = get_cookie_domain(request) if request else None

    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        domain=domain,
    )
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE,
        domain=domain,
    )
    response.delete_cookie(
        key=CSRF_TOKEN_COOKIE,
        domain=domain,
    )


def get_token_from_cookie(request: Request, token_type: str = "access") -> str | None:
    """Get token from cookie.

    Args:
        request: FastAPI request object
        token_type: "access" or "refresh"

    Returns:
        Token string or None
    """
    cookie_name = (
        ACCESS_TOKEN_COOKIE if token_type == "access" else REFRESH_TOKEN_COOKIE
    )
    return request.cookies.get(cookie_name)


def get_csrf_token_from_cookie(request: Request) -> str | None:
    """Get CSRF token from cookie.

    Args:
        request: FastAPI request object

    Returns:
        CSRF token string or None
    """
    return request.cookies.get(CSRF_TOKEN_COOKIE)


async def validate_csrf_token(request: Request) -> bool:
    """Validate CSRF token from cookie against header.

    Delegates to core/csrf.py for hash-based validation (double-submit with hashed cookie).
    The client sends: plaintext token in X-CSRF-Token header + sha256(token) in csrf_token cookie.
    This is the production security standard - plaintext cookie comparison is deprecated.

    Args:
        request: FastAPI request object

    Returns:
        True if valid, False otherwise
    """
    from core.csrf import validate_csrf as _validate_csrf

    header_token = request.headers.get("X-CSRF-Token")
    if not header_token:
        return False

    # core.validate_csrf(request) returns None on success and raises
    # HTTPException on failure — normalize to a boolean so the middleware can
    # return a clean 403 instead of an unhandled 500.
    try:
        await _validate_csrf(request)
        return True
    except HTTPException:
        return False


def require_csrf_validation(request: Request) -> None:
    """Require CSRF validation for mutating requests.

    Raises HTTPException if CSRF validation fails.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: If CSRF validation fails
    """
    # Skip CSRF for GET, HEAD, OPTIONS
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        return

    # Skip CSRF for login endpoint (no auth yet)
    if request.url.path in ["/api/auth/login", "/api/auth/refresh"]:
        return

    # Validate CSRF token
    if not validate_csrf_token(request):
        logger.warning(
            f"CSRF validation failed for {request.method} {request.url.path}",
            extra={
                "path": request.url.path,
                "method": request.method,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )


class CookieAuthManager:
    """Manager for cookie-based authentication."""

    def __init__(self, request: Request, response: Response):
        """Initialize cookie auth manager.

        Args:
            request: FastAPI request object
            response: FastAPI response object
        """
        self.request = request
        self.response = response

    def set_tokens(
        self,
        access_token: str,
        refresh_token: str,
    ) -> str:
        """Set authentication tokens as cookies.

        Args:
            access_token: JWT access token
            refresh_token: JWT refresh token

        Returns:
            CSRF token for client to use
        """
        csrf_token = generate_csrf_token()
        set_auth_cookies(
            self.response,
            access_token,
            refresh_token,
            csrf_token,
            self.request,
        )
        return csrf_token

    def clear_tokens(self) -> None:
        """Clear authentication tokens from cookies."""
        clear_auth_cookies(self.response, self.request)

    def get_access_token(self) -> str | None:
        """Get access token from cookie."""
        return get_token_from_cookie(self.request, "access")

    def get_refresh_token(self) -> str | None:
        """Get refresh token from cookie."""
        return get_token_from_cookie(self.request, "refresh")

    def validate_csrf(self) -> bool:
        """Validate CSRF token."""
        return validate_csrf_token(self.request)


def create_token_response_with_cookies(
    response: Response,
    request: Request,
    user_id: str,
    user_role: str,
) -> dict:
    """Create tokens and set them as cookies.

    Args:
        response: FastAPI response object
        request: FastAPI request object
        user_id: User ID
        user_role: User role

    Returns:
        Dict with CSRF token for client
    """
    # Create tokens
    access_token = create_access_token(
        data={"sub": user_id, "role": user_role},
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )
    refresh_token = create_refresh_token(data={"sub": user_id, "role": user_role})

    # Set cookies
    manager = CookieAuthManager(request, response)
    csrf_token = manager.set_tokens(access_token, refresh_token)

    return {
        "csrf_token": csrf_token,
        "token_type": "cookie",
        "expires_in": settings.jwt_expire_minutes * 60,
    }
