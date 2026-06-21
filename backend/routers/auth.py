"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.cookie_auth import clear_auth_cookies, set_auth_cookies
from core.csrf import generate_csrf_token, set_csrf_cookie
from core.logger import get_logger
from db.session import get_session
from dependencies.auth import (
    get_current_user,
    require_admin,
    user_to_response,
)
from models.user import UserModel
from schemas.user import (
    ChangePasswordRequest,
    MeResponse,
    TokenRefresh,
    TokenResponse,
    UserLogin,
)
from services.auth_service import AuthService
from middleware.rate_limiter import rate_limit

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    """Dependency: provide AuthService instance."""
    return AuthService(session)


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
    auth_service: AuthService = Depends(get_auth_service),
):
    """Authenticate user and return tokens (stored in httpOnly cookies)."""
    user, access_token, refresh_token = await auth_service.authenticate(credentials)

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
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Refresh access token using refresh token.

    Implements token rotation: old refresh token is blacklisted
    after new tokens are issued to prevent replay attacks.
    """
    user, access_token, new_refresh_token = await auth_service.refresh_tokens(
        refresh_data.refresh_token
    )

    # Update httpOnly cookies with new tokens
    set_auth_cookies(response, access_token, new_refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=user_to_response(user),
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: UserModel = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Logout user, blacklist tokens, and clear httpOnly cookies."""
    from core.cookie_auth import COOKIE_ACCESS_TOKEN_NAME, COOKIE_REFRESH_TOKEN_NAME
    from core.cookie_auth import get_token_from_cookie as _get_cookie

    # Extract tokens from cookies
    cookie_header = request.headers.get("cookie")
    access_token = _get_cookie(cookie_header, COOKIE_ACCESS_TOKEN_NAME)
    refresh_token = _get_cookie(cookie_header, COOKIE_REFRESH_TOKEN_NAME)

    # Also extract Bearer token if present
    bearer_token = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        bearer_token = auth_header[7:]

    await auth_service.logout(
        user_id=current_user.id,
        access_token=access_token,
        refresh_token=refresh_token,
        bearer_token=bearer_token,
    )

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
    auth_service: AuthService = Depends(get_auth_service),
):
    """Change the current user's password."""
    await auth_service.change_password(current_user, data)
    return {"message": "Password changed successfully"}


@router.post("/unlock-user/{username}")
async def unlock_user_account(
    username: str,
    current_user: UserModel = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Unlock a user account (admin only).

    Clears failed login attempts and lockout status for the specified user.
    """
    user = await auth_service.unlock_user(
        admin_id=current_user.id,
        username=username,
    )

    return {
        "message": f"User account '{username}' has been unlocked",
        "username": user.username,
        "failed_attempts": 0,
        "locked_until": None,
    }
