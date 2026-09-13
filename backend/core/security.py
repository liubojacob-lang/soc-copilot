"""Security utilities for JWT, password hashing, and API keys."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from jwt import PyJWTError

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# Password hashing with bcrypt (native API, not passlib which is unmaintained
# and incompatible with bcrypt>=4.0 — see P0-4 security audit).
# Development: 10 rounds (faster, ~100ms)
# Production: 12 rounds (default, ~250ms)
bcrypt_rounds = 10 if settings.environment == "development" else 12

# JWT settings - always use fresh settings.jwt_secret, not cached constant
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expire_minutes
REFRESH_TOKEN_EXPIRE_MINUTES = settings.jwt_refresh_expire_minutes


# Helper function to get JWT secret dynamically
def get_jwt_secret() -> str:
    """Get current JWT secret from settings."""
    return settings.jwt_secret


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash.

    Handles legacy passlib hashes (starting with $2b$/$2a$) transparently —
    bcrypt native checkpw accepts the same hash format.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # Malformed hash (e.g. legacy SHA-256 API keys handled elsewhere)
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=bcrypt_rounds)
    ).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.

    Security: Includes 'iat' (issued at) claim for token invalidation detection.
    When user data changes (role, password), compare iat with user.updated_at
    to detect if token was issued before the change.
    Includes 'jti' — a unique identity per token, so revocation/blacklist
    applies to the exact token. Without jti, two logins within the same
    second produce identical JWT strings and blacklisting one blacklists all.
    """
    to_encode = data.copy()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update(
        {
            "exp": expire,
            "iat": now,  # Issued at - for invalidation detection
            "jti": str(uuid.uuid4()),
            "type": "access",
        }
    )
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token.

    Security: Includes 'iat' (issued at) claim for token invalidation detection
    and a unique 'jti' (see create_access_token).
    """
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update(
        {
            "exp": expire,
            "iat": now,  # Issued at - for invalidation detection
            "jti": str(uuid.uuid4()),
            "type": "refresh",
        }
    )
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_pre_auth_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """Create a short-lived token for 2FA login challenge (5 min valid)."""
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=5))
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "pre_2fa",
    }
    return jwt.encode(to_encode, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_sudo_token(user_id: str, minutes: int = 10) -> str:
    """Create a temporary ticket for sudo-mode sensitive operations."""
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=minutes)
    to_encode = {
        "sub": user_id,
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "type": "sudo",
    }
    return jwt.encode(to_encode, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token.

    P1-17: Supports JWT secret rotation — tries current secret first,
    then falls back to jwt_secret_previous for transition period compatibility.
    """
    secrets_to_try = [get_jwt_secret()]
    if settings.jwt_secret_previous:
        secrets_to_try.append(settings.jwt_secret_previous)

    for secret in secrets_to_try:
        try:
            payload = jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
            return payload
        except PyJWTError:
            continue

    logger.debug("Token decode failed with all secrets")
    return None


def is_token_invalidated_by_user_update(
    token_payload: dict,
    user_updated_at: str | None,
) -> bool:
    """Check if a token was issued before the user's last update.

    This implements token invalidation without requiring a blacklist.
    When a user's role, password, or other critical data changes,
    their updated_at timestamp is updated. Tokens issued before
    that timestamp are considered invalid.

    Args:
        token_payload: Decoded JWT payload containing 'iat' claim
        user_updated_at: User's updated_at timestamp (ISO format)

    Returns:
        True if token was issued before user update (should be rejected)
        False if token is still valid
    """
    if not user_updated_at:
        return False  # No update timestamp, token is valid

    token_iat = token_payload.get("iat")
    if not token_iat:
        return True  # No iat claim, reject token

    # Parse user's updated_at (ISO format)
    try:
        if isinstance(user_updated_at, str):
            user_updated = datetime.fromisoformat(user_updated_at)
            if user_updated.tzinfo is None:
                user_updated = user_updated.replace(tzinfo=UTC)
        else:
            user_updated = user_updated_at
    except (ValueError, TypeError):
        logger.warning(f"Invalid updated_at format: {user_updated_at}")
        return False  # If we can't parse, allow token (fallback behavior)

    # Parse token iat (may be float timestamp or datetime)
    try:
        if isinstance(token_iat, int | float):
            token_issued = datetime.fromtimestamp(token_iat, tz=UTC)
        else:
            token_issued = token_iat
            if isinstance(token_issued, str):
                token_issued = datetime.fromisoformat(token_issued)
                if token_issued.tzinfo is None:
                    token_issued = token_issued.replace(tzinfo=UTC)
    except (ValueError, TypeError, OSError):
        logger.warning(f"Invalid iat format: {token_iat}")
        return False  # If we can't parse, allow token (fallback behavior)

    # Token is invalid if issued before user update
    # v1.0: Normalize timezone awareness for safe comparison (DB DateTime(timezone=True))
    _user_updated = user_updated
    if isinstance(_user_updated, datetime) and _user_updated.tzinfo is None:
        _user_updated = _user_updated.replace(tzinfo=UTC)
    if isinstance(_user_updated, str):
        _user_updated = datetime.fromisoformat(_user_updated)
        if _user_updated.tzinfo is None:
            _user_updated = _user_updated.replace(tzinfo=UTC)
    # v1.0: Compare at second precision - JWT iat is second-precision while
    # DB updated_at has microseconds. Truncating avoids false rejection of
    # tokens issued in the same second as a user update, while still
    # invalidating tokens issued BEFORE the update.
    _user_updated = _user_updated.replace(microsecond=0)
    is_invalidated = token_issued < _user_updated

    if is_invalidated:
        logger.info(
            f"Token invalidated by user update: "
            f"token_iat={token_issued.isoformat()}, "
            f"user_updated={user_updated.isoformat()}"
        )

    return is_invalidated


def check_password_history(new_password: str, password_history: list) -> bool:
    """Check if new password exists in the recent password history.

    P1-19: Prevents password reuse by comparing against the last 5 passwords
    using bcrypt verify.

    Args:
        new_password: Plain-text new password to check
        password_history: List of previous password entries (dict or str hashes)

    Returns:
        True if password is found in history (should be rejected)
        False if password is not in history (allowed)
    """
    if not password_history:
        return False

    for entry in password_history[:5]:
        if isinstance(entry, dict):
            old_hash = entry.get("hashed_password", "")
        else:
            old_hash = str(entry)

        if old_hash and verify_password(new_password, old_hash):
            return True

    return False


# API Key hashing with salt - using bcrypt for security
def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage using bcrypt (version 2).

    For backward compatibility, also supports legacy SHA256 (version 1).
    New keys always use bcrypt.
    """
    # Use bcrypt for new keys (prefix with 'v2:' to identify)
    return f"v2:{get_password_hash(api_key)}"


def verify_api_key(plain_api_key: str, hashed_api_key: str) -> bool:
    """Verify an API key against its hash.

    Supports both legacy SHA256 (v1) and new bcrypt (v2) hashes.
    """
    if hashed_api_key.startswith("v2:"):
        # New bcrypt hash (native API)
        return verify_password(plain_api_key, hashed_api_key[3:])
    else:
        # Legacy SHA256 hash - for backward compatibility
        legacy_hash = hashlib.sha256(plain_api_key.encode()).hexdigest()
        return legacy_hash == hashed_api_key


def generate_api_key() -> str:
    """Generate a new API key."""
    return f"sk_{secrets.token_urlsafe(32)}"


def get_api_key_prefix(api_key: str) -> str:
    """Get the prefix of an API key for display."""
    return api_key[:8]
