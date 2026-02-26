"""Security utilities for JWT, password hashing, and API keys."""

import hashlib
import secrets
from datetime import datetime, timedelta, UTC
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# Password hashing with configurable bcrypt rounds
# Development: 10 rounds (faster, ~100ms)
# Production: 12 rounds (default, ~250ms)
bcrypt_rounds = 10 if settings.environment == "development" else 12
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=bcrypt_rounds
)

# JWT settings - always use fresh settings.jwt_secret, not cached constant
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expire_minutes
REFRESH_TOKEN_EXPIRE_MINUTES = settings.jwt_refresh_expire_minutes

# Helper function to get JWT secret dynamically
def get_jwt_secret() -> str:
    """Get current JWT secret from settings."""
    return settings.jwt_secret


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.debug(f"Token decode failed: {e}")
        return None


# API Key hashing with salt - using bcrypt for security
def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage using bcrypt (version 2).
    
    For backward compatibility, also supports legacy SHA256 (version 1).
    New keys always use bcrypt.
    """
    # Use bcrypt for new keys (prefix with 'v2:' to identify)
    return f"v2:{pwd_context.hash(api_key)}"


def verify_api_key(plain_api_key: str, hashed_api_key: str) -> bool:
    """Verify an API key against its hash.
    
    Supports both legacy SHA256 (v1) and new bcrypt (v2) hashes.
    """
    if hashed_api_key.startswith("v2:"):
        # New bcrypt hash
        return pwd_context.verify(plain_api_key, hashed_api_key[3:])
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
