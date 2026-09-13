"""Router for Two-Factor Authentication (TOTP - RFC 6238)."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from core.security import create_sudo_token, verify_password
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel
from schemas.user import (
    TOTPDisableRequest,
    TOTPEnableRequest,
    TOTPPolicyRequest,
    TOTPSetupResponse,
    TOTPStatusResponse,
    TOTPSudoResponse,
    TOTPVerifyRequest,
)
from services.security.secret_service import get_secret_service
from services.totp_service import TOTPService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth/2fa", tags=["Two-Factor Authentication"])


@router.get("/status", response_model=TOTPStatusResponse)
async def get_2fa_status(
    current_user: UserModel = Depends(get_current_user),
) -> TOTPStatusResponse:
    """Get current user's 2FA enablement status and active policy."""
    return TOTPStatusResponse(
        is_enabled=bool(current_user.is_totp_enabled),
        policy=current_user.totp_policy or "sudo",
    )


@router.post("/setup", response_model=TOTPSetupResponse)
async def setup_2fa(
    current_user: UserModel = Depends(get_current_user),
) -> TOTPSetupResponse:
    """Initiate 2FA setup by generating a secret, QR code, and backup codes."""
    secret = TOTPService.generate_secret()
    uri = TOTPService.get_provisioning_uri(current_user.username, secret)
    qr_code = TOTPService.generate_qr_code_base64(uri)
    backup_codes = TOTPService.generate_backup_codes(count=8)

    return TOTPSetupResponse(
        secret=secret,
        qr_code=qr_code,
        provisioning_uri=uri,
        backup_codes=backup_codes,
    )


@router.post("/enable", response_model=TOTPStatusResponse)
async def enable_2fa(
    request: TOTPEnableRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> TOTPStatusResponse:
    """Verify code and activate 2FA with the chosen policy."""
    valid, _, _ = TOTPService.verify_code(request.secret, request.code)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA verification code. Please check your authenticator app.",
        )

    secret_service = get_secret_service()
    encrypted_secret = secret_service.encrypt(request.secret)
    encrypted_backup = (
        secret_service.encrypt(json.dumps(request.backup_codes))
        if request.backup_codes
        else None
    )

    current_user.totp_secret = encrypted_secret
    current_user.totp_backup_codes = encrypted_backup
    current_user.is_totp_enabled = True
    current_user.totp_policy = request.policy

    await db.commit()
    logger.info(f"User {current_user.username} enabled 2FA with policy: {request.policy}")

    return TOTPStatusResponse(
        is_enabled=True,
        policy=current_user.totp_policy or "sudo",
    )


@router.post("/policy", response_model=TOTPStatusResponse)
async def switch_2fa_policy(
    request: TOTPPolicyRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> TOTPStatusResponse:
    """Switch 2FA authentication policy (sudo vs login) after verifying current code."""
    if not current_user.is_totp_enabled or not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled on this account.",
        )

    secret_service = get_secret_service()
    plain_secret = secret_service.decrypt(current_user.totp_secret)
    backup_codes: list[str] = []
    if current_user.totp_backup_codes:
        try:
            backup_codes = json.loads(secret_service.decrypt(current_user.totp_backup_codes))
        except Exception:
            backup_codes = []

    valid, used_backup, updated_backup = TOTPService.verify_code(
        plain_secret, request.code, backup_codes=backup_codes
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA verification code.",
        )

    current_user.totp_policy = request.policy
    if used_backup and updated_backup is not None:
        current_user.totp_backup_codes = secret_service.encrypt(json.dumps(updated_backup))

    await db.commit()
    logger.info(f"User {current_user.username} switched 2FA policy to: {request.policy}")

    return TOTPStatusResponse(
        is_enabled=True,
        policy=current_user.totp_policy,
    )


@router.post("/verify-sudo", response_model=TOTPSudoResponse)
async def verify_sudo_mode(
    request: TOTPVerifyRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> TOTPSudoResponse:
    """Verify 2FA code for Sudo Mode and issue a temporary sudo token (10 mins valid)."""
    if not current_user.is_totp_enabled or not current_user.totp_secret:
        # If user has not enabled 2FA, pass-through sudo token
        sudo_token = create_sudo_token(current_user.id, minutes=10)
        return TOTPSudoResponse(valid=True, sudo_token=sudo_token, expires_in_seconds=600)

    secret_service = get_secret_service()
    plain_secret = secret_service.decrypt(current_user.totp_secret)
    backup_codes: list[str] = []
    if current_user.totp_backup_codes:
        try:
            backup_codes = json.loads(secret_service.decrypt(current_user.totp_backup_codes))
        except Exception:
            backup_codes = []

    valid, used_backup, updated_backup = TOTPService.verify_code(
        plain_secret, request.code, backup_codes=backup_codes
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA verification code.",
        )

    if used_backup and updated_backup is not None:
        current_user.totp_backup_codes = secret_service.encrypt(json.dumps(updated_backup))
        await db.commit()

    sudo_token = create_sudo_token(current_user.id, minutes=10)
    return TOTPSudoResponse(valid=True, sudo_token=sudo_token, expires_in_seconds=600)


@router.post("/disable", response_model=TOTPStatusResponse)
async def disable_2fa(
    request: TOTPDisableRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> TOTPStatusResponse:
    """Disable 2FA after validating both password and 2FA code."""
    if not current_user.is_totp_enabled:
        return TOTPStatusResponse(is_enabled=False, policy="sudo")

    # 1. Verify password
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid account password.",
        )

    # 2. Verify 2FA code
    secret_service = get_secret_service()
    plain_secret = secret_service.decrypt(current_user.totp_secret)
    backup_codes: list[str] = []
    if current_user.totp_backup_codes:
        try:
            backup_codes = json.loads(secret_service.decrypt(current_user.totp_backup_codes))
        except Exception:
            backup_codes = []

    valid, _, _ = TOTPService.verify_code(
        plain_secret, request.code, backup_codes=backup_codes
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 2FA verification code.",
        )

    current_user.is_totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_backup_codes = None
    current_user.totp_policy = "sudo"

    await db.commit()
    logger.info(f"User {current_user.username} disabled 2FA.")

    return TOTPStatusResponse(is_enabled=False, policy="sudo")
