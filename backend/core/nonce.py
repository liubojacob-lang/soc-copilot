"""CSP nonce utilities for nonce-based Content Security Policy."""

import secrets


def generate_csp_nonce() -> str:
    """Generate a cryptographically secure CSP nonce.

    Returns a 22-character URL-safe base64 string (16 bytes = 128 bits of entropy).

    This nonce should be:
    - Generated fresh per request
    - Stored in request.state.csp_nonce for SSR template access
    - Injected into the Content-Security-Policy header
    - Added to every <script nonce="..."> and <style nonce="..."> tag in HTML
    """
    return secrets.token_urlsafe(16)


def get_csp_header(nonce: str, is_production: bool = True) -> str:
    """Build CSP header string with nonce injection.

    Args:
        nonce: The generated CSP nonce value.
        is_production: If False, include 'unsafe-inline' as fallback for development.

    Returns:
        Full Content-Security-Policy header value string.
    """
    script_src = f"script-src 'self' 'nonce-{nonce}'"
    style_src = f"style-src 'self' 'nonce-{nonce}'"

    if not is_production:
        # Development: keep unsafe-inline for hot-reload / dev tools compatibility
        script_src += " 'unsafe-inline'"
        style_src += " 'unsafe-inline'"

    return (
        f"default-src 'self'; "
        f"{script_src}; "
        f"{style_src}; "
        f"img-src 'self' data:; "
        f"connect-src 'self'; "
        f"frame-ancestors 'none'; "
        f"base-uri 'self'; "
        f"form-action 'self';"
    )
