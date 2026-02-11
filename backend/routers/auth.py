"""Authentication API endpoints."""

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.user import UserModel, UserRole
from schemas.user import UserLogin, TokenResponse, TokenRefresh, MeResponse
from repositories.user_repository import UserRepository
from core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from core.config import settings
from dependencies.auth import get_current_user, get_current_user_optional
from dependencies.auth import user_to_response
from core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    credentials: UserLogin,
    session: AsyncSession = Depends(get_session),
):
    """Authenticate user and return tokens."""
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

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        from repositories.audit_repository import AuditRepository
        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="login:failed",
            method="POST",
            path="/api/auth/login",
            status_code=401,
            user_id=user.id,
            extra_json={"reason": "invalid_password"},
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

    # Update last login
    await user_repo.update_last_login(user.id)

    # Create tokens
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )
    refresh_token = create_refresh_token(data={"sub": user.id})

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

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_to_response(user),
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

    # Create new tokens
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes),
    )
    new_refresh_token = create_refresh_token(data={"sub": user.id})

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
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Logout user (client should discard tokens)."""
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

    return {"message": "Successfully logged out"}


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: UserModel = Depends(get_current_user),
):
    """Get current user info."""
    from dependencies.auth import get_user_permissions
    permissions = get_user_permissions(current_user)

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
        permissions=permissions,
    )
