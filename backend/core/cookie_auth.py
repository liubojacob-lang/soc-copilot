"""Cookie-based authentication with httpOnly cookies for XSS protection."""

from datetime import timedelta
from fastapi import Response
from core.config import settings

# Cookie configuration
COOKIE_ACCESS_TOKEN_NAME = "access_token"
COOKIE_REFRESH_TOKEN_NAME = "refresh_token"

# Cookie security settings
def get_cookie_settings() -> dict:
    """Get secure cookie settings based on environment."""
    is_production = settings.environment == "production"

    return {
        "httponly": True,  # Prevent JavaScript access (XSS protection)
        "secure": is_production,  # Only send over HTTPS in production
        "samesite": "lax",  # CSRF protection (lax allows navigation from external sites)
        "max_age": settings.jwt_expire_minutes * 60,  # Convert to seconds
    }


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str
) -> None:
    """Set authentication cookies on response."""
    cookie_settings = get_cookie_settings()

    # Set access token cookie
    response.set_cookie(
        key=COOKIE_ACCESS_TOKEN_NAME,
        value=access_token,
        path="/",
        **cookie_settings
    )

    # Set refresh token cookie (longer expiry)
    refresh_cookie_settings = cookie_settings.copy()
    refresh_cookie_settings["max_age"] = settings.jwt_refresh_expire_minutes * 60
    response.set_cookie(
        key=COOKIE_REFRESH_TOKEN_NAME,
        value=refresh_token,
        path="/",
        **refresh_cookie_settings
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies."""
    is_production = settings.environment == "production"

    # Delete access token cookie
    response.delete_cookie(
        key=COOKIE_ACCESS_TOKEN_NAME,
        path="/",
        httponly=True,
        secure=is_production,
        samesite="lax",
    )

    # Delete refresh token cookie
    response.delete_cookie(
        key=COOKIE_REFRESH_TOKEN_NAME,
        path="/",
        httponly=True,
        secure=is_production,
        samesite="lax",
    )


def get_token_from_cookie(cookie_header: str | None, cookie_name: str) -> str | None:
    """Extract token from Cookie header."""
    if not cookie_header:
        return None

    cookies = cookie_header.split(";")
    for cookie in cookies:
        cookie = cookie.strip()
        if cookie.startswith(f"{cookie_name}="):
            return cookie.split("=", 1)[1].strip()

    return None
