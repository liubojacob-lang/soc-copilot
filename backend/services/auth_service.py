"""Authentication service — business logic for login, logout, token refresh, and password management."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from core.security import (
    check_password_history,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from core.token_blacklist import add_token_to_blacklist, get_token_blacklist
from models.user import UserModel, UserRole
from repositories.audit_repository import AuditRepository
from repositories.user_repository import UserRepository
from schemas.user import ChangePasswordRequest, UserLogin
from services.base import BaseService

logger = get_logger(__name__)

# Security constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


class AuthService(BaseService):
    """Authentication service handling login, logout, token refresh, and password operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.user_repo = UserRepository(session)
        self.audit_repo = AuditRepository(session)

    async def authenticate(self, credentials: UserLogin) -> tuple[UserModel, str, str]:
        """Authenticate user and return (user, access_token, refresh_token).

        Raises HTTPException on authentication failure.
        """
        # Find user by username
        user = await self.user_repo.get_by_username(credentials.username)
        if not user:
            await self._audit_login_failed(
                username=credentials.username,
                reason="user_not_found",
                status_code=401,
            )
            await self.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

        # Check if account is locked
        if user.locked_until:
            locked_until = datetime.fromisoformat(user.locked_until)
            if locked_until > datetime.now():
                remaining_minutes = int(
                    (locked_until - datetime.now()).total_seconds() / 60
                )
                await self._audit_login_failed(
                    user_id=user.id,
                    reason="account_locked",
                    status_code=423,
                    extra_json={
                        "locked_until": user.locked_until,
                    },
                )
                await self.commit()
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=f"Account is locked. Try again in {remaining_minutes} minutes or contact administrator.",
                )
            else:
                # Lockout period has expired, clear it
                user.locked_until = None
                user.failed_login_attempts = 0

        # Verify password
        if not verify_password(credentials.password, user.hashed_password):
            # Increment failed login attempts
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1

            # Check if we should lock the account
            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                lockout_until = datetime.now() + timedelta(
                    minutes=LOCKOUT_DURATION_MINUTES
                )
                user.locked_until = lockout_until

                await self._audit_login_failed(
                    user_id=user.id,
                    reason="max_login_attempts_exceeded",
                    status_code=423,
                    extra_json={
                        "attempts": user.failed_login_attempts,
                        "locked_until": user.locked_until,
                    },
                )
                await self.commit()
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=f"Too many failed login attempts. Account locked for {LOCKOUT_DURATION_MINUTES} minutes.",
                )

            # Log failed attempt
            await self._audit_login_failed(
                user_id=user.id,
                reason="invalid_password",
                status_code=401,
                extra_json={
                    "attempts": user.failed_login_attempts,
                    "max_attempts": MAX_LOGIN_ATTEMPTS,
                },
            )
            await self.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )

        # Check if user is active
        if not user.is_active:
            await self._audit_login_failed(
                user_id=user.id,
                reason="account_disabled",
                status_code=403,
            )
            await self.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )

        # Reset failed login attempts on successful login
        user.failed_login_attempts = 0
        user.locked_until = None

        # Update last login
        await self.user_repo.update_last_login(user.id)

        # Create tokens with role for authorization
        access_token = create_access_token(
            data={
                "sub": user.id,
                "role": user.role.value if hasattr(user.role, "value") else user.role,
            },
            expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
        )
        refresh_token = create_refresh_token(
            data={
                "sub": user.id,
                "role": user.role.value if hasattr(user.role, "value") else user.role,
            }
        )

        # Audit successful login
        await self.audit_repo.create(
            action="login:success",
            method="POST",
            path="/api/auth/login",
            status_code=200,
            user_id=user.id,
            extra_json={"username": user.username},
        )
        await self.commit()

        return user, access_token, refresh_token

    async def refresh_tokens(self, refresh_token: str) -> tuple[UserModel, str, str]:
        """Refresh access token using refresh token.

        Implements token rotation: old refresh token is blacklisted
        after new tokens are issued to prevent replay attacks.

        Returns (user, new_access_token, new_refresh_token).
        """
        # Decode refresh token
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Check if the old refresh token has already been blacklisted (replay detection)
        blacklist = get_token_blacklist()
        if await blacklist.is_blacklisted(refresh_token):
            logger.warning(f"Reused refresh token detected for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked. Please login again.",
            )

        # Get user
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        # Blacklist the old refresh token (rotation)
        await add_token_to_blacklist(refresh_token, reason="token_rotation")

        # Create new tokens with role for authorization
        access_token = create_access_token(
            data={
                "sub": user.id,
                "role": user.role.value if hasattr(user.role, "value") else user.role,
            },
            expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
        )
        new_refresh_token = create_refresh_token(
            data={
                "sub": user.id,
                "role": user.role.value if hasattr(user.role, "value") else user.role,
            }
        )

        # Create audit log
        await self.audit_repo.create(
            action="token:refresh",
            method="POST",
            path="/api/auth/refresh",
            status_code=200,
            user_id=user.id,
        )
        await self.commit()

        return user, access_token, new_refresh_token

    async def logout(
        self,
        user_id: str,
        access_token: str | None,
        refresh_token: str | None,
        bearer_token: str | None,
    ) -> None:
        """Logout user and blacklist all tokens."""
        if access_token:
            await add_token_to_blacklist(access_token, reason="logout")
        if refresh_token:
            await add_token_to_blacklist(refresh_token, reason="logout")
        if bearer_token:
            await add_token_to_blacklist(bearer_token, reason="logout")

        # Create audit log
        await self.audit_repo.create(
            action="logout",
            method="POST",
            path="/api/auth/logout",
            status_code=200,
            user_id=user_id,
        )
        await self.commit()

    async def change_password(
        self, user: UserModel, data: ChangePasswordRequest
    ) -> None:
        """Change user password with validation."""
        if not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        if data.new_password != data.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation do not match",
            )

        if data.new_password == data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password",
            )

        # P1-19: Check password history to prevent reuse
        if check_password_history(data.new_password, user.password_history):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reuse recent passwords",
            )

        hashed = get_password_hash(data.new_password)
        await self.user_repo.update_password(user.id, hashed)

        # S0-19: Invalidate permission cache after password change
        # Ensures any cached permissions from before the password change
        # are cleared so the next request goes through fresh auth
        from dependencies.auth import invalidate_user_permission_cache

        invalidate_user_permission_cache(user.id)

        await self.commit()

    async def unlock_user(self, admin_id: str, username: str) -> UserModel:
        """Unlock a user account (admin only).

        Clears failed login attempts and lockout status for the specified user.
        """
        user = await self.user_repo.get_by_username(username)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Clear lockout
        user.failed_login_attempts = 0
        user.locked_until = None
        await self.flush()

        # Create audit log
        await self.audit_repo.create(
            action="account_unlocked",
            method="POST",
            path=f"/api/auth/unlock-user/{username}",
            status_code=200,
            user_id=admin_id,
            extra_json={
                "unlocked_user_id": user.id,
                "unlocked_username": user.username,
            },
        )
        await self.commit()

        return user

    async def _audit_login_failed(
        self,
        reason: str,
        status_code: int,
        username: str | None = None,
        user_id: str | None = None,
        extra_json: dict[str, Any] | None = None,
    ) -> None:
        """Create audit log for failed login attempts."""
        audit_extra = extra_json or {}
        if username:
            audit_extra["username"] = username

        await self.audit_repo.create(
            action=(
                "login:failed"
                if reason != "max_login_attempts_exceeded"
                else "account_locked"
            ),
            method="POST",
            path="/api/auth/login",
            status_code=status_code,
            user_id=user_id,
            extra_json=audit_extra,
        )
