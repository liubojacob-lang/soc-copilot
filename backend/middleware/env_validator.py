"""Environment variable validation middleware.

Ensures all required environment variables are set before application starts.
Provides helpful error messages with generation commands.
"""

import os
import sys

from core.logger import get_logger

logger = get_logger(__name__)


class EnvVarError(Exception):
    """Raised when a required environment variable is missing or invalid."""

    pass


def validate_env_var(
    name: str,
    required: bool = True,
    default: str | None = None,
    min_length: int = 0,
    pattern: str | None = None,
    hint: str | None = None,
) -> str:
    """Validate a single environment variable.

    Args:
        name: Environment variable name
        required: If True, raises error when missing
        default: Default value if not set (only used when required=False)
        min_length: Minimum length for non-empty values
        pattern: Description of expected pattern (for error messages)
        hint: Command to generate a valid value

    Returns:
        The validated environment variable value

    Raises:
        EnvVarError: If validation fails
    """
    value = os.environ.get(name, default)

    if required and not value:
        error_msg = f"❌ Required environment variable missing: {name}"
        if hint:
            error_msg += f"\n   💡 Generate value: {hint}"
        raise EnvVarError(error_msg)

    if value and len(value) < min_length:
        error_msg = (
            f"❌ Environment variable too short: {name} (min length: {min_length})"
        )
        if hint:
            error_msg += f"\n   💡 Generate value: {hint}"
        raise EnvVarError(error_msg)

    return value


def validate_security_env():
    """Validate all security-critical environment variables.

    This should be called during application startup to catch
    misconfiguration early.
    """
    environment = os.environ.get("ENVIRONMENT", "development")

    # Skip validation in development environment
    if environment == "development":
        logger.info("✅ Skipping security env validation in development mode")
        return

    errors: list[str] = []

    # Database
    try:
        validate_env_var(
            "DB_PASSWORD", required=True, min_length=16, hint="openssl rand -base64 32"
        )
    except EnvVarError as e:
        errors.append(str(e))

    # JWT Secret (the signing key actually consumed by core.config.jwt_secret;
    # a legacy SECRET_KEY variable was never read by the application)
    try:
        secret_key = validate_env_var(
            "JWT_SECRET", required=True, min_length=32, hint="openssl rand -base64 64"
        )
        # Additional check for secret strength
        if secret_key and len(secret_key) < 32:
            errors.append(
                f"❌ JWT_SECRET too weak (length: {len(secret_key)}, minimum: 32)\n"
                f"   💡 Generate strong key: openssl rand -base64 64"
            )
    except EnvVarError as e:
        errors.append(str(e))

    # Redis Password (required in production)
    if environment == "production":
        try:
            validate_env_var(
                "REDIS_PASSWORD",
                required=True,
                min_length=16,
                hint="openssl rand -base64 32",
            )
        except EnvVarError as e:
            errors.append(str(e))

    # Report results
    if errors:
        logger.error("\n" + "=" * 60)
        logger.error("🔒 SECURITY CONFIGURATION ERRORS")
        logger.error("=" * 60)
        for i, error in enumerate(errors, 1):
            logger.error(f"\n{i}. {error}")
        logger.error("\n" + "=" * 60)
        logger.error("Please fix these issues before starting the application")
        logger.error("=" * 60 + "\n")
        sys.exit(1)
    else:
        logger.info("✅ All security environment variables validated successfully")


def validate_cors_origins():
    """Validate CORS configuration."""
    origins = os.environ.get("CORS_ORIGINS", "")
    environment = os.environ.get("ENVIRONMENT", "development")

    if environment == "production":
        if not origins or "*" in origins:
            logger.warning(
                "⚠️  WARNING: CORS_ORIGINS contains wildcard '*' in production!\n"
                "   This is a security risk. Set specific origins:\n"
                "   CORS_ORIGINS=http://localhost:3000,https://your-domain.com"
            )


# Run validation on import (when in development)
if os.environ.get("ENVIRONMENT") == "development":
    try:
        # Don't fail on missing vars in development, just warn
        validate_security_env()
    except SystemExit:
        pass  # Suppress exit during development
