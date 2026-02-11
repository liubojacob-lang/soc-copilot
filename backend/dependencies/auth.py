"""Authentication and authorization dependencies."""

import secrets
import hashlib
from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_session
from models.user import UserModel, UserRole
from models.api_key import APIKeyModel
from schemas.user import UserResponse
from core.security import decode_token, verify_password, hash_api_key
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# HTTP Bearer scheme for JWT
security = HTTPBearer(auto_error=False)


async def get_user_by_username(session: AsyncSession, username: str) -> Optional[UserModel]:
    """Get user by username."""
    result = await session.execute(select(UserModel).where(UserModel.username == username))
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: str) -> Optional[UserModel]:
    """Get user by ID."""
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_api_key(session: AsyncSession, key_hash: str) -> Optional[UserModel]:
    """Get user by API key hash."""
    result = await session.execute(
        select(UserModel)
        .join(APIKeyModel, UserModel.id == APIKeyModel.user_id)
        .where(APIKeyModel.key_hash == key_hash)
        .where(APIKeyModel.is_active == True)
        .where(UserModel.is_active == True)
    )
    return result.scalar_one_or_none()


async def update_api_key_last_used(session: AsyncSession, api_key: APIKeyModel) -> None:
    """Update API key last used timestamp."""
    from datetime import datetime
    api_key.last_used_at = datetime.now().isoformat()
    session.add(api_key)
    await session.commit()


def get_user_permissions(user: UserModel) -> list[str]:
    """Get user permissions based on role."""
    if user.role == UserRole.ADMIN:
        return [
            "users:read", "users:write", "users:delete",
            "api_keys:read", "api_keys:write", "api_keys:delete",
            "audit_logs:read", "audit_logs:write",
            "assets:read", "assets:write", "assets:delete",
            "ioc_hits:read", "ioc_hits:write",
            "history:read", "history:write", "history:delete",
            "analyze_alert", "build_timeline", "generate_report",
            "playbook:read", "playbook:run", "playbook:resume", "playbook:apply",
            "ti:query",
        ]
    elif user.role == UserRole.ANALYST:
        return [
            "api_keys:read", "api_keys:write",
            "assets:read", "assets:write",
            "ioc_hits:read", "ioc_hits:write",
            "history:read", "history:write",
            "analyze_alert", "build_timeline", "generate_report",
            "playbook:read", "playbook:run", "playbook:resume",
            "ti:query",
        ]
    elif user.role == UserRole.AUDITOR:
        return [
            "assets:read",
            "ioc_hits:read",
            "history:read",
            "analyze_alert", "build_timeline", "generate_report",  # Read-only analysis
            "playbook:read",
            "ti:query",
            "audit_logs:read",
        ]
    return []


def user_to_response(user: UserModel) -> UserResponse:
    """Convert UserModel to UserResponse."""
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        permissions=get_user_permissions(user),
    )


async def get_current_user_optional(
    session: Annotated[AsyncSession, Depends(get_session)],
    authorization: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    x_api_key: Annotated[Optional[str], Header()] = None,
) -> Optional[UserModel]:
    """Get current user from JWT or API key (optional, returns None if not authenticated)."""
    # Try API Key first
    if x_api_key:
        key_hash = hash_api_key(x_api_key)
        user = await get_user_by_api_key(session, key_hash)
        if user:
            # Get the API key to update last_used
            result = await session.execute(
                select(APIKeyModel).where(APIKeyModel.key_hash == key_hash)
            )
            api_key = result.scalar_one_or_none()
            if api_key:
                await update_api_key_last_used(session, api_key)
            return user

    # Try JWT
    if authorization:
        token = authorization.credentials
        payload = decode_token(token)
        if payload and payload.get("type") == "access":
            user_id = payload.get("sub")
            if user_id:
                user = await get_user_by_id(session, user_id)
                if user and user.is_active:
                    return user

    return None


async def get_current_user(
    current_user: Annotated[Optional[UserModel], Depends(get_current_user_optional)],
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
        current_user: Annotated[UserModel, Depends(get_current_user)]
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
require_analyst = require_role(UserRole.ANALYST)  # Includes admin implicitly by logic above


async def get_api_key_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    x_api_key: Annotated[str, Header(...)],
) -> UserModel:
    """Get user from API Key (for API authentication)."""
    key_hash = hash_api_key(x_api_key)
    user = await get_user_by_api_key(session, key_hash)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    # Update last_used
    result = await session.execute(
        select(APIKeyModel).where(APIKeyModel.key_hash == key_hash)
    )
    api_key = result.scalar_one_or_none()
    if api_key:
        await update_api_key_last_used(session, api_key)

    return user
