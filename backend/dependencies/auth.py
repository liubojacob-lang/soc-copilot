"""Authentication and authorization dependencies."""

from datetime import UTC, datetime, timedelta
from fnmatch import fnmatch
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, true
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from core.security import (
    decode_token,
    is_token_invalidated_by_user_update,
    verify_api_key,
)
from core.validators import validate_id_format, validate_sql_input
from db.session import get_session
from models.api_key import APIKeyModel
from models.user import UserModel, UserRole
from schemas.user import MeResponse

logger = get_logger(__name__)

# v0.8.3: User permission cache with TTL for improved performance
# Cache structure: {user_id: (permissions_list, cached_at_datetime)}
_user_permission_cache: dict[str, tuple[list[str], datetime]] = {}
_PERMISSION_CACHE_TTL_SECONDS = 300  # 5 minutes TTL

# HTTP Bearer scheme for JWT
security = HTTPBearer(auto_error=False)


async def get_user_by_username(
    session: AsyncSession, username: str
) -> UserModel | None:
    """Get user by username."""
    validated_username = validate_sql_input(username)
    result = await session.execute(
        select(UserModel).where(UserModel.username == validated_username)
    )
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: str) -> UserModel | None:
    """Get user by ID."""
    validate_id_format(user_id, "user_id")
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_api_key(
    session: AsyncSession, plain_api_key: str
) -> tuple[UserModel, APIKeyModel] | None:
    """Get user and API key by plain API key (verifies against stored hash).

    v0.8.4: Added rate limiting to prevent API key enumeration attacks.

    Returns tuple of (user, api_key) if valid, None otherwise.
    """
    from fastapi import HTTPException, status

    from middleware.rate_limiter import check_api_key_rate_limit

    # Get API key prefix for quick lookup
    prefix = plain_api_key[:8] if len(plain_api_key) >= 8 else plain_api_key

    # P3-3: Rate limiting - Check before verification to prevent enumeration
    allowed, rate_info = await check_api_key_rate_limit(prefix, session)

    if not allowed:
        logger.warning(f"API key rate limit exceeded for prefix: {prefix[:4]}****")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please wait a moment before trying again.",
            headers={
                "X-RateLimit-Limit": str(rate_info["limit"]),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(rate_info["reset"]),
                "Retry-After": str(rate_info["reset"]),
            },
        )

    # Query active API keys matching the prefix
    result = await session.execute(
        select(APIKeyModel, UserModel)
        .join(UserModel, APIKeyModel.user_id == UserModel.id)
        .where(APIKeyModel.key_prefix == prefix)
        .where(APIKeyModel.is_active == true())
        .where(UserModel.is_active == true())
    )

    # Check each key for match (bcrypt hashes are unique)
    for api_key, user in result.all():
        if verify_api_key(plain_api_key, api_key.key_hash):
            return (user, api_key)

    return None


async def update_api_key_last_used(session: AsyncSession, api_key: APIKeyModel) -> None:
    """Update API key last used timestamp."""
    from datetime import datetime

    api_key.last_used_at = datetime.now().isoformat()
    session.add(api_key)
    await session.commit()


@lru_cache(maxsize=32)
def _get_permissions_by_role(role_value: str) -> tuple[str, ...]:
    """Get permissions for a role value (cached).

    Returns tuple for hashability and immutability.
    """
    if role_value == UserRole.ADMIN.value:
        return (
            "users:read",
            "users:write",
            "users:delete",
            "api_keys:read",
            "api_keys:write",
            "api_keys:delete",
            "audit_logs:read",
            "audit_logs:write",
            "assets:read",
            "assets:write",
            "assets:delete",
            "ioc_hits:read",
            "ioc_hits:write",
            "history:read",
            "history:write",
            "history:delete",
            "analyze_alert",
            "build_timeline",
            "generate_report",
            "playbook:read",
            "playbook:run",
            "playbook:resume",
            "playbook:apply",
            "ti:query",
        )
    elif role_value == UserRole.ANALYST.value:
        return (
            "api_keys:read",
            "api_keys:write",
            "assets:read",
            "assets:write",
            "ioc_hits:read",
            "ioc_hits:write",
            "history:read",
            "history:write",
            "analyze_alert",
            "build_timeline",
            "generate_report",
            "playbook:read",
            "playbook:run",
            "playbook:resume",
            "ti:query",
        )
    elif role_value == UserRole.AUDITOR.value:
        return (
            "assets:read",
            "ioc_hits:read",
            "history:read",
            "analyze_alert",
            "build_timeline",
            "generate_report",  # Read-only analysis
            "playbook:read",
            "ti:query",
            "audit_logs:read",
        )
    return ()


def get_user_permissions(user: UserModel) -> list[str]:
    """Get user permissions based on role (cached by role)."""
    # user.role may be stored as string, not enum
    role_value = user.role.value if hasattr(user.role, "value") else user.role
    return list(_get_permissions_by_role(role_value))


def get_user_permissions_cached(user_id: str, user: UserModel) -> list[str]:
    """Get user permissions with per-user caching and TTL.

    This provides a second-level cache that avoids repeated role lookups
    for the same user within the TTL window.

    Args:
        user_id: User ID for cache key
        user: User model to get permissions from

    Returns:
        List of permission strings for the user
    """
    now = datetime.now(UTC)

    # Check cache
    if user_id in _user_permission_cache:
        perms, cached_at = _user_permission_cache[user_id]
        if now - cached_at < timedelta(seconds=_PERMISSION_CACHE_TTL_SECONDS):
            return perms

    # Fetch and cache
    perms = get_user_permissions(user)
    _user_permission_cache[user_id] = (perms, now)
    return perms


def clear_permission_cache() -> None:
    """Clear the permission cache (use when roles/permissions are updated)."""
    _get_permissions_by_role.cache_clear()
    _user_permission_cache.clear()


def invalidate_user_permission_cache(user_id: str | None = None) -> None:
    """Invalidate permission cache for a specific user or all users.

    Call this when:
    - User's role is changed
    - Role permissions are updated
    - User is deleted/deactivated

    Args:
        user_id: Specific user to invalidate, or None for all users
    """
    global _user_permission_cache
    if user_id:
        _user_permission_cache.pop(user_id, None)
        logger.debug(f"Permission cache invalidated for user {user_id}")
    else:
        _user_permission_cache.clear()
        _get_permissions_by_role.cache_clear()
        logger.debug("All permission caches cleared")


def user_to_response(user: UserModel) -> MeResponse:
    """Convert UserModel to MeResponse with cached permissions."""
    return MeResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        permissions=get_user_permissions_cached(user.id, user),
    )


def is_public_readonly_endpoint(path: str) -> bool:
    """Check if a request path matches any public readonly endpoint pattern.

    S0-20: Uses fnmatch-style glob patterns for flexible matching.
    Default whitelist is empty (deny-all) for maximum security.

    Args:
        path: The request path to check (e.g., "/api/health")

    Returns:
        True if the path is in the public readonly whitelist
    """
    for pattern in settings.public_readonly_endpoints:
        if fnmatch(path, pattern):
            logger.debug(
                f"Public readonly access allowed for: {path} (matched: {pattern})"
            )
            return True
    return False


async def get_current_user_optional(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    x_api_key: Annotated[str | None, Header()] = None,
    cookie: Annotated[str | None, Header(alias="cookie")] = None,
) -> UserModel | None:
    """Get current user from JWT (Bearer or cookie) or API key (optional, returns None if not authenticated).

    S0-20: Public readonly endpoints are accessible without authentication
    if their path matches the configured whitelist.
    """
    # S0-20: Check if path is in public readonly whitelist
    if is_public_readonly_endpoint(request.url.path):
        # For public endpoints, return None (no user) — the endpoint
        # handler decides whether to allow unauthenticated access
        return None

    # Try API Key first
    if x_api_key:
        result = await get_user_by_api_key(session, x_api_key)
        if result:
            user, api_key = result
            await update_api_key_last_used(session, api_key)
            return user

    # Collect auth token candidates: Bearer header first, then the
    # access_token cookie. Placeholder values sent by the frontend when it
    # holds no token ("undefined"/"null") must not shadow a valid cookie.
    candidates: list[str] = []
    if authorization and authorization.credentials:
        bearer = authorization.credentials
        if bearer not in ("undefined", "null", ""):
            candidates.append(bearer)
    if cookie:
        from core.cookie_auth import COOKIE_ACCESS_TOKEN_NAME, get_token_from_cookie

        cookie_token = get_token_from_cookie(cookie, COOKIE_ACCESS_TOKEN_NAME)
        if cookie_token:
            candidates.append(cookie_token)

    # Check if any candidate token authenticates
    from core.token_blacklist import get_token_blacklist

    blacklist = get_token_blacklist()
    for token in candidates:
        if await blacklist.is_blacklisted(token):
            logger.warning("Blacklisted token used for authentication")
            continue

        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            user_id = payload.get("sub")
            if user_id:
                user = await get_user_by_id(session, user_id)
                if user and user.is_active:
                    # Security: Check if token was invalidated by user update
                    # (e.g., role change, password change)
                    if is_token_invalidated_by_user_update(payload, user.updated_at):
                        logger.warning(
                            f"Token rejected: issued before user update "
                            f"(user_id={user_id}, role={user.role})"
                        )
                        return None
                    return user

    return None


async def get_current_user(
    current_user: Annotated[UserModel | None, Depends(get_current_user_optional)],
) -> UserModel:
    """Get current user (required, raises 401 if not authenticated)."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    return current_user


def require_role(*roles: UserRole):
    """Dependency factory to require specific role(s)."""

    async def role_checker(
        current_user: Annotated[UserModel, Depends(get_current_user)],
    ) -> UserModel:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required role: {', '.join([r.value for r in roles])}",
            )
        return current_user

    return role_checker


# Common role dependencies
require_admin = require_role(UserRole.ADMIN)
require_analyst_or_admin = require_role(UserRole.ADMIN, UserRole.ANALYST)
require_auditor_or_admin = require_role(UserRole.ADMIN, UserRole.AUDITOR)
require_analyst = require_role(
    UserRole.ANALYST
)  # Includes admin implicitly by logic above

# ============================================================================
# v1.1: Fine-grained RBAC — require_permission via database-backed checks
# ============================================================================


async def check_permission_in_db(
    session: AsyncSession, user: UserModel, resource: str, action: str
) -> bool:
    """Check if a user has a specific permission via database RBAC tables.

    Queries the role_permissions join table. Falls back to role-based
    string permissions (backward compat) when no DB records match.
    """
    from sqlalchemy import select as sa_select

    from models.rbac import Permission, Role

    # v1.1: Admin role is superuser - has all permissions (short-circuit)
    _role_val = user.role.value if hasattr(user.role, "value") else user.role
    if _role_val == "admin":
        return True

    # Check DB-based permissions (join through role_permissions)
    result = await session.execute(
        sa_select(Permission)
        .join(Role.permissions)
        .where(Role.name == str(_role_val))
        .where(Permission.resource == resource)
        .where(Permission.action == action)
    )
    if result.scalars().first():
        return True

    # Fallback: role-based string permissions (backward compatibility)
    perms = get_user_permissions(user)
    perm_str = f"{resource}:{action}"
    return perm_str in perms


async def has_permission(user: UserModel, resource: str, action: str) -> bool:
    """Check if a user has a specific permission (convenience helper)."""
    from db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        return await check_permission_in_db(session, user, resource, action)


def require_permission(resource: str, action: str):
    """Dependency factory to require a specific resource:action permission.

    Usage:
        Depends(require_permission("admin", "write"))
    """

    async def checker(
        current_user: Annotated[UserModel, Depends(get_current_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> UserModel:
        if not await check_permission_in_db(session, current_user, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permission denied. Required: {resource}:{action}. "
                    f"Your role: "
                    f"{current_user.role.value if hasattr(current_user.role, 'value') else current_user.role!s}"
                ),
            )
        return current_user

    return checker


async def get_api_key_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    x_api_key: Annotated[str, Header(...)],
) -> UserModel:
    """Get user from API Key (for API authentication)."""
    result = await get_user_by_api_key(session, x_api_key)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    user, api_key = result

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Update last_used
    await update_api_key_last_used(session, api_key)

    return user


async def logout_with_token_blacklist(
    authorization: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict:
    """Handle logout with token blacklist."""
    from core.token_blacklist import add_token_to_blacklist

    token = authorization.credentials if authorization else None

    if token:
        await add_token_to_blacklist(token, reason="User logged out")

    return {"message": "Successfully logged out", "token_revoked": True}
