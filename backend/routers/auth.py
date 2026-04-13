"""Authentication API endpoints."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.cookie_auth import clear_auth_cookies, set_auth_cookies
from core.csrf import generate_csrf_token, set_csrf_cookie
from core.logger import get_logger
from middleware.rate_limiter import rate_limit
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from db.session import get_session
from dependencies.auth import (
    get_current_user,
    require_admin,
    user_to_response,
)
from models.user import UserModel
from repositories.user_repository import UserRepository
from schemas.user import ChangePasswordRequest, MeResponse, TokenRefresh, TokenResponse, UserLogin

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Security constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="用户登录",
    description="""
用户登录接口，验证用户名和密码后返回访问令牌。

**认证流程**:
1. 验证用户名和密码
2. 检查账户是否被锁定
3. 生成 JWT 访问令牌和刷新令牌
4. 将令牌存储在 HttpOnly Cookie 中

**安全特性**:
- 连续 5 次失败登录将锁定账户 30 分钟
- 令牌存储在 HttpOnly Cookie 中防止 XSS 攻击
- 支持 CSRF 保护

**响应状态码**:
- 200: 登录成功
- 401: 用户名或密码错误
- 423: 账户已被锁定
""",
    responses={
        200: {
            "description": "登录成功",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 720,
                        "user": {
                            "id": "uuid",
                            "username": "admin",
                            "email": "admin@example.com",
                            "role": "admin",
                        },
                    }
                }
            },
        },
        401: {"description": "用户名或密码错误"},
        423: {"description": "账户已被锁定"},
    },
)
@rate_limit(max_requests=5, window_seconds=60)
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    """Authenticate user and return tokens (stored in httpOnly cookies)."""
    user_repo = UserRepository(session)

    # Find user by username
    user = await user_repo.get_by_username(credentials.username)
    if not user:
        # Create audit log for failed login
        from repositories.audit_repository import AuditRepository

        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="login:failed",
            method="POST",
            path="/api/auth/login",
            status_code=401,
            extra_json={"username": credentials.username, "reason": "user_not_found"},
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Check if account is locked
    if user.locked_until:
        locked_until = datetime.fromisoformat(user.locked_until)
        if locked_until > datetime.now():
            # Account is still locked
            remaining_minutes = int((locked_until - datetime.now()).total_seconds() / 60)
            from repositories.audit_repository import AuditRepository

            audit_repo = AuditRepository(session)
            await audit_repo.create(
                action="login:failed",
                method="POST",
                path="/api/auth/login",
                status_code=423,
                user_id=user.id,
                extra_json={
                    "reason": "account_locked",
                    "locked_until": user.locked_until,
                },
            )
            await session.commit()
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
            # Lock the account
            lockout_until = datetime.now() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
            user.locked_until = lockout_until.isoformat()

            from repositories.audit_repository import AuditRepository

            audit_repo = AuditRepository(session)
            await audit_repo.create(
                action="account_locked",
                method="POST",
                path="/api/auth/login",
                status_code=423,
                user_id=user.id,
                extra_json={
                    "reason": "max_login_attempts_exceeded",
                    "attempts": user.failed_login_attempts,
                    "locked_until": user.locked_until,
                },
            )
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Too many failed login attempts. Account locked for {LOCKOUT_DURATION_MINUTES} minutes.",
            )

        # Log failed attempt
        from repositories.audit_repository import AuditRepository

        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="login:failed",
            method="POST",
            path="/api/auth/login",
            status_code=401,
            user_id=user.id,
            extra_json={
                "reason": "invalid_password",
                "attempts": user.failed_login_attempts,
                "max_attempts": MAX_LOGIN_ATTEMPTS,
            },
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Check if user is active
    if not user.is_active:
        from repositories.audit_repository import AuditRepository

        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="login:failed",
            method="POST",
            path="/api/auth/login",
            status_code=403,
            user_id=user.id,
            extra_json={"reason": "account_disabled"},
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Reset failed login attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None

    # Update last login
    await user_repo.update_last_login(user.id)

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

    # Create audit log for successful login
    from repositories.audit_repository import AuditRepository

    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="login:success",
        method="POST",
        path="/api/auth/login",
        status_code=200,
        user_id=user.id,
        extra_json={"username": user.username},
    )
    await session.commit()

    # Set httpOnly cookies for XSS protection
    set_auth_cookies(response, access_token, refresh_token)

    # Generate and set CSRF token
    csrf_token = generate_csrf_token()
    set_csrf_cookie(response, csrf_token)

    # Return tokens in response body for backward compatibility
    # (but prefer cookies in production)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_to_response(user),
        must_change_password=user.must_change_password,
        csrf_token=csrf_token,  # Include CSRF token for frontend use
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: TokenRefresh,
    session: AsyncSession = Depends(get_session),
):
    """Refresh access token using refresh token."""
    # Decode refresh token
    payload = decode_token(refresh_data.refresh_token)
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

    # Get user
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

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
    from repositories.audit_repository import AuditRepository

    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="token:refresh",
        method="POST",
        path="/api/auth/refresh",
        status_code=200,
        user_id=user.id,
    )
    await session.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=user_to_response(user),
    )


@router.post("/logout")
async def logout(
    response: Response,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Logout user and clear httpOnly cookies."""
    from repositories.audit_repository import AuditRepository

    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="logout",
        method="POST",
        path="/api/auth/logout",
        status_code=200,
        user_id=current_user.id,
    )
    await session.commit()

    # Clear httpOnly cookies
    clear_auth_cookies(response)

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: UserModel = Depends(get_current_user),
):
    """Get current user info."""
    # Use cached version for better performance
    response = user_to_response(current_user)
    return MeResponse(
        id=response.id,
        username=response.username,
        email=response.email,
        role=response.role,
        is_active=response.is_active,
        created_at=response.created_at,
        updated_at=response.updated_at,
        last_login_at=response.last_login_at,
        permissions=response.permissions,
    )


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Change the current user's password."""
    if not verify_password(data.current_password, current_user.hashed_password):
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

    user_repo = UserRepository(session)
    hashed = get_password_hash(data.new_password)
    await user_repo.update_password(current_user.id, hashed)
    await session.commit()

    return {"message": "Password changed successfully"}


@router.post("/unlock-user/{username}")
async def unlock_user_account(
    username: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(require_admin),
):
    """Unlock a user account (admin only).

    Clears failed login attempts and lockout status for the specified user.
    """
    user_repo = UserRepository(session)
    user = await user_repo.get_by_username(username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Clear lockout
    user.failed_login_attempts = 0
    user.locked_until = None

    # Create audit log
    from repositories.audit_repository import AuditRepository

    audit_repo = AuditRepository(session)
    await audit_repo.create(
        action="account_unlocked",
        method="POST",
        path=f"/api/auth/unlock-user/{username}",
        status_code=200,
        user_id=current_user.id,
        extra_json={
            "unlocked_user_id": user.id,
            "unlocked_username": user.username,
        },
    )
    await session.commit()

    return {
        "message": f"User account '{username}' has been unlocked",
        "username": user.username,
        "failed_attempts": 0,
        "locked_until": None,
    }
