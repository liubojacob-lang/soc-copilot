"""Security validators and production checks."""

import re

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# Weak passwords that should not be allowed
WEAK_PASSWORDS = {
    "password",
    "password1",
    "password123",
    "123456",
    "12345678",
    "qwerty",
    "abc123",
    "monkey",
    "letmein",
    "dragon",
    "master",
    "admin",
    "admin123",
    "admin123!",
    "root",
    "toor",
    "test",
    "test123",
    "guest",
    "welcome",
    "welcome1",
    "changeme",
    "passw0rd",
    "p@ssw0rd",
    "p@ssword",
    "password!",
    "iloveyou",
    "trustno1",
    "sunshine",
    "princess",
    "football",
    "baseball",
    "soccer",
    "hockey",
    "batman",
    "superman",
    "shadow",
    "ashley",
    "michael",
    "jennifer",
    "thomas",
    "charlie",
    "andrew",
    "joshua",
}

# Common password patterns that indicate weakness
WEAK_PATTERNS = [
    re.compile(r"^[a-z]+$"),  # Only lowercase letters
    re.compile(r"^[A-Z]+$"),  # Only uppercase letters
    re.compile(r"^[0-9]+$"),  # Only numbers
    re.compile(r"^[a-zA-Z]+$"),  # Only letters
    re.compile(r"^[a-z0-9]+$"),  # Only lowercase letters and numbers
    re.compile(r"^[A-Z0-9]+$"),  # Only uppercase letters and numbers
    re.compile(r"(.)\1{2,}"),  # Repeated characters (3+)
    re.compile(r"^[0-9]{4,}$"),  # 4+ digit numbers at start
    re.compile(r"[0-9]{4,}$"),  # 4+ digit numbers at end
    re.compile(r"(password|passwd|pwd)", re.IGNORECASE),  # Contains password
    re.compile(r"(admin|root|user|test)", re.IGNORECASE),  # Contains common words
]


class SecurityValidationError(Exception):
    """Raised when security validation fails."""

    pass


def validate_jwt_secret() -> tuple[bool, str | None]:
    """
    Validate JWT secret for production use.

    Returns:
        Tuple of (is_valid, error_message)
    """
    secret = settings.jwt_secret
    default_secret = "CHANGE_THIS_IN_PRODUCTION_MIN_32_CHARS_LONG"

    # Check if using default secret
    if secret == default_secret:
        if settings.environment == "production" or settings.strict_production_checks:
            return (
                False,
                "JWT_SECRET is using default value. This is not allowed in production.",
            )
        else:
            logger.warning(
                "JWT_SECRET is using default value. This should be changed before production deployment."
            )
            return True, None

    # Check minimum length
    if len(secret) < 32:
        if settings.enforce_strict_checks:
            return (
                False,
                f"JWT_SECRET must be at least 32 characters long. Current length: {len(secret)}",
            )
        else:
            logger.warning(
                f"JWT_SECRET is shorter than recommended 32 characters (current: {len(secret)})"
            )

    # Check entropy (basic check)
    unique_chars = len(set(secret))
    if unique_chars < 16:
        if settings.enforce_strict_checks:
            return (
                False,
                f"JWT_SECRET has low entropy. Only {unique_chars} unique characters.",
            )
        else:
            logger.warning(
                f"JWT_SECRET has low entropy ({unique_chars} unique characters). Consider using a more complex secret."
            )

    return True, None


def validate_password_strength(
    password: str, username: str = ""
) -> tuple[bool, list[str]]:
    """
    Validate password strength.

    Args:
        password: Password to validate
        username: Optional username to check if password contains it

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check minimum length
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    # Check maximum length (prevent DoS)
    if len(password) > 128:
        errors.append("Password must be less than 128 characters")

    # Check for weak password
    if password.lower() in WEAK_PASSWORDS:
        errors.append("Password is too common. Please choose a stronger password")

    # Check for weak patterns
    for pattern in WEAK_PATTERNS:
        if pattern.search(password):
            errors.append(
                "Password contains a common pattern. Please choose a more complex password"
            )
            break

    # Check for username in password
    if username and username.lower() in password.lower():
        errors.append("Password should not contain your username")

    # Check character variety (only if not already failed)
    if not errors:
        has_lower = any(c.islower() for c in password)
        has_upper = any(c.isupper() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        variety_count = sum([has_lower, has_upper, has_digit, has_special])
        if variety_count < 3:
            errors.append(
                "Password must contain at least 3 of: lowercase, uppercase, digits, special characters"
            )

    return len(errors) == 0, errors


def validate_bootstrap_password() -> tuple[bool, str | None]:
    """
    Validate bootstrap admin password.

    Returns:
        Tuple of (is_valid, error_message)
    """
    password = settings.bootstrap_admin_password

    # Check if using default password
    if password == "admin123!":
        if settings.enforce_strict_checks:
            return (
                False,
                "Bootstrap admin password is using default value 'admin123!'. This is not allowed with strict production checks.",
            )
        else:
            logger.warning(
                "Bootstrap admin password is using default value. Please change after first login!"
            )
            return True, None

    # Validate password strength
    is_valid, errors = validate_password_strength(
        password, settings.bootstrap_admin_username
    )
    if not is_valid:
        if settings.enforce_strict_checks:
            return False, f"Bootstrap admin password is weak: {'; '.join(errors)}"
        else:
            logger.warning(f"Bootstrap admin password is weak: {'; '.join(errors)}")

    return True, None


def run_production_security_checks() -> list[str]:
    """
    Run all production security checks.

    Returns:
        List of error messages (empty if all checks pass)
    """
    errors = []

    # Check JWT secret
    is_valid, error = validate_jwt_secret()
    if not is_valid:
        errors.append(f"JWT Secret: {error}")

    # Check bootstrap password
    is_valid, error = validate_bootstrap_password()
    if not is_valid:
        errors.append(f"Bootstrap Password: {error}")

    # Check environment-specific settings
    if settings.environment == "production":
        # Check CORS
        if not settings.cors_origins:
            errors.append(
                "CORS origins not configured for production. Set CORS_ORIGINS environment variable."
            )

        # Check secret encryption key
        if not settings.secret_encryption_key:
            errors.append(
                "SECRET_ENCRYPTION_KEY not set. Required for secrets management in production."
            )

    return errors


def get_password_strength_score(password: str) -> tuple[int, str]:
    """
    Calculate password strength score.

    Args:
        password: Password to evaluate

    Returns:
        Tuple of (score 0-100, strength_label)
    """
    score = 0

    # Length scoring
    if len(password) >= 8:
        score += 10
    if len(password) >= 12:
        score += 10
    if len(password) >= 16:
        score += 10
    if len(password) >= 20:
        score += 10

    # Character variety
    if any(c.islower() for c in password):
        score += 10
    if any(c.isupper() for c in password):
        score += 10
    if any(c.isdigit() for c in password):
        score += 10
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 15

    # Entropy bonus
    unique_chars = len(set(password))
    if unique_chars >= 8:
        score += 5
    if unique_chars >= 12:
        score += 5
    if unique_chars >= 16:
        score += 5

    # Penalty for weak patterns
    if password.lower() in WEAK_PASSWORDS:
        score = max(0, score - 50)

    for pattern in WEAK_PATTERNS:
        if pattern.search(password):
            score = max(0, score - 20)
            break

    # Determine label
    if score >= 80:
        label = "Very Strong"
    elif score >= 60:
        label = "Strong"
    elif score >= 40:
        label = "Moderate"
    elif score >= 20:
        label = "Weak"
    else:
        label = "Very Weak"

    return score, label
