"""Router for secrets management (v0.7.4)."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from middleware.rate_limiter import rate_limit
from models.user import UserModel, UserRole
from repositories.secret_repository import SecretRepository
from services.security.secret_service import get_secret_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/secrets", tags=["secrets"])


# ============ Schemas ============


class SecretCreate(BaseModel):
    """Schema for creating a secret."""

    name: str = Field(..., min_length=1, max_length=100, description="Unique secret name")
    value: str = Field(..., min_length=1, description="Secret value (will be encrypted)")


class SecretUpdate(BaseModel):
    """Schema for updating a secret."""

    value: str = Field(..., min_length=1, description="New secret value (will be encrypted)")


class SecretResponse(BaseModel):
    """Schema for secret response."""

    id: str
    name: str
    created_at: str
    updated_at: str
    created_by_user_id: str | None = None
    value_preview: str = Field(..., description="Masked preview of secret value")

    model_config = {"from_attributes": True}


class SecretListResponse(BaseModel):
    """Schema for secret list response."""

    items: list[SecretResponse]
    total: int
    page: int
    page_size: int


class SecretKeyStatusResponse(BaseModel):
    """Schema for encryption key status."""

    configured: bool
    valid: bool
    key_preview: str | None = None


# ============ Helper Functions ============


def mask_secret_value(value: str, visible_chars: int = 4) -> str:
    """Mask a secret value for display.

    Args:
        value: Secret value to mask
        visible_chars: Number of leading chars to show

    Returns:
        Masked value (e.g., "abcd****************")
    """
    if len(value) <= visible_chars:
        return "*" * len(value)
    return value[:visible_chars] + "*" * (len(value) - visible_chars)


# ============ CRUD Endpoints ============


@router.post("", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
@rate_limit(max_requests=10, window_seconds=60)
async def create_secret(
    data: SecretCreate,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Create a new secret (admin only).

    The value will be encrypted before storage.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can create secrets")

    repo = SecretRepository(db)

    # Check if secret already exists
    existing = await repo.get_by_name(data.name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Secret '{data.name}' already exists")

    # Encrypt the value
    secret_service = get_secret_service()
    encrypted_value = secret_service.encrypt(data.value)

    # Create secret
    secret = await repo.create(
        name=data.name,
        encrypted_value=encrypted_value,
        created_by_user_id=current_user.id,
    )

    await db.commit()

    logger.info(f"Secret '{data.name}' created by user {current_user.username}")

    return SecretResponse(
        id=secret.id,
        name=secret.name,
        created_at=secret.created_at.isoformat(),
        updated_at=secret.updated_at.isoformat(),
        created_by_user_id=secret.created_by_user_id,
        value_preview=mask_secret_value(data.value),
    )


@router.get("", response_model=SecretListResponse)
async def list_secrets(
    page: int = 1,
    page_size: int = 50,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List all secrets (admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can list secrets")

    repo = SecretRepository(db)
    total = await repo.count()
    items = await repo.list_all(limit=page_size, offset=(page - 1) * page_size)

    return SecretListResponse(
        items=[
            SecretResponse(
                id=item.id,
                name=item.name,
                created_at=item.created_at.isoformat(),
                updated_at=item.updated_at.isoformat(),
                created_by_user_id=item.created_by_user_id,
                value_preview="****",  # Never return actual values
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/key-status", response_model=SecretKeyStatusResponse)
async def get_key_status(
    current_user: UserModel = Depends(get_current_user),
):
    """Get encryption key status (admin only)."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can check key status")

    secret_service = get_secret_service()
    return SecretKeyStatusResponse(**secret_service.get_encryption_key_status())


@router.get("/{secret_name}", response_model=SecretResponse)
async def get_secret(
    secret_name: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get a secret by name (admin only).

    Note: Returns masked preview only, never the actual value.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view secrets")

    repo = SecretRepository(db)
    secret = await repo.get_by_name(secret_name)

    if not secret:
        raise HTTPException(status_code=404, detail=f"Secret '{secret_name}' not found")

    # Decrypt to get length for preview
    secret_service = get_secret_service()
    decrypted_value = secret_service.decrypt(secret.encrypted_value)

    return SecretResponse(
        id=secret.id,
        name=secret.name,
        created_at=secret.created_at.isoformat(),
        updated_at=secret.updated_at.isoformat(),
        created_by_user_id=secret.created_by_user_id,
        value_preview=mask_secret_value(decrypted_value),
    )


@router.patch("/{secret_name}", response_model=SecretResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def update_secret(
    secret_name: str,
    data: SecretUpdate,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update a secret's value (admin only).

    Creates an audit log of the change.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can update secrets")

    repo = SecretRepository(db)

    # Check if secret exists
    existing = await repo.get_by_name(secret_name)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Secret '{secret_name}' not found")

    # Encrypt the new value
    secret_service = get_secret_service()
    encrypted_value = secret_service.encrypt(data.value)

    # Update secret
    updated = await repo.update(secret_name, encrypted_value)

    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update secret")

    await db.commit()

    logger.info(f"Secret '{secret_name}' updated by user {current_user.username}")

    return SecretResponse(
        id=updated.id,
        name=updated.name,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
        created_by_user_id=updated.created_by_user_id,
        value_preview=mask_secret_value(data.value),
    )


@router.delete("/{secret_name}", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit(max_requests=10, window_seconds=60)
async def delete_secret(
    secret_name: str,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Delete a secret (admin only).

    Warning: This action cannot be undone. Playbooks referencing this
    secret will fail until it is recreated.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete secrets")

    repo = SecretRepository(db)
    success = await repo.delete(secret_name)

    if not success:
        raise HTTPException(status_code=404, detail=f"Secret '{secret_name}' not found")

    await db.commit()

    logger.info(f"Secret '{secret_name}' deleted by user {current_user.username}")
