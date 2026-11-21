"""TOTP Two-Factor Authentication Service (RFC 6238)."""

import base64
import hashlib
import hmac
import io
import secrets
import string

import pyotp
import qrcode

from core.logger import get_logger

logger = get_logger(__name__)


class TOTPService:
    """Service for TOTP (Time-based One-Time Password) management."""

    @staticmethod
    def generate_secret() -> str:
        """Generate a random 32-character base32 secret."""
        return pyotp.random_base32()

    @staticmethod
    def hash_backup_code(code: str) -> str:
        """Hash a backup recovery code for storage using SHA-256."""
        normalized = code.strip().replace(" ", "").lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def hash_backup_codes(codes: list[str]) -> list[str]:
        """Hash a list of backup codes for storage."""
        return [TOTPService.hash_backup_code(c) for c in codes]

    @staticmethod
    def get_provisioning_uri(
        username: str, secret: str, issuer_name: str = "SOC-Copilot"
    ) -> str:
        """Generate an otpauth URI for authenticator apps."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=username, issuer_name=issuer_name)

    @staticmethod
    def generate_qr_code_base64(uri: str) -> str:
        """Render the provisioning URI as a base64-encoded PNG data URI."""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        b64_png = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{b64_png}"

    @staticmethod
    def generate_backup_codes(count: int = 8) -> list[str]:
        """Generate backup recovery codes (format: xxxx-xxxx)."""
        alphabet = string.ascii_lowercase + string.digits
        codes = []
        for _ in range(count):
            part1 = "".join(secrets.choice(alphabet) for _ in range(4))
            part2 = "".join(secrets.choice(alphabet) for _ in range(4))
            codes.append(f"{part1}-{part2}")
        return codes

    @staticmethod
    def verify_code(
        secret: str,
        code: str,
        backup_codes: list[str] | None = None,
        valid_window: int = 1,
    ) -> tuple[bool, bool, list[str] | None]:
        """Verify a TOTP code or backup code.

        Supports both hashed backup codes (SHA-256) and legacy plaintext backup codes.

        Args:
            secret: Base32 TOTP secret
            code: 6-digit TOTP code or backup code
            backup_codes: Optional list of available backup codes (hashes or plain)
            valid_window: Number of 30-second steps to allow before/after (default 1 = +/-30s)

        Returns:
            Tuple of (is_valid, is_backup_used, updated_backup_codes)
        """
        clean_code = code.strip().replace(" ", "")

        # 1. Try TOTP code first
        if len(clean_code) == 6 and clean_code.isdigit():
            try:
                totp = pyotp.TOTP(secret)
                if totp.verify(clean_code, valid_window=valid_window):
                    return True, False, backup_codes
            except Exception as e:
                logger.warning(f"TOTP verify error: {e}")

        # 2. Try backup codes if provided (constant-time comparison)
        if backup_codes:
            normalized_code = clean_code.lower()
            code_hash = hashlib.sha256(normalized_code.encode()).hexdigest()

            for idx, stored in enumerate(backup_codes):
                # Check hashed backup code first (SHA-256 64-char hex)
                is_match = False
                if len(stored) == 64:
                    is_match = hmac.compare_digest(code_hash, stored)
                else:
                    # Legacy plaintext fallback
                    is_match = hmac.compare_digest(normalized_code, stored.lower())

                if is_match:
                    new_backup = list(backup_codes)
                    new_backup.pop(idx)
                    logger.info("A 2FA backup recovery code was successfully used.")
                    return True, True, new_backup

        return False, False, backup_codes
