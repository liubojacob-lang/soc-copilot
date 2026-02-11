"""Secret Service for encrypted credential storage (v0.7.4).

This service handles encryption and decryption of secrets using Fernet
symmetric encryption. Secrets are stored encrypted in the database and
only decrypted when needed for playbook execution.
"""

from typing import Optional
import logging

from cryptography.fernet import Fernet, InvalidToken
from cryptography.exceptions import InvalidKey

from core.config import settings

logger = logging.getLogger(__name__)


class SecretService:
    """Service for encrypting and decrypting secrets."""

    def __init__(self):
        """Initialize the secret service with Fernet cipher.

        Raises:
            ValueError: If SECRET_ENCRYPTION_KEY is not configured or invalid
        """
        if not settings.secret_encryption_key:
            raise ValueError(
                "SECRET_ENCRYPTION_KEY not configured. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        try:
            self.fernet = Fernet(settings.secret_encryption_key.encode())
        except (InvalidKey, ValueError) as e:
            raise ValueError(
                f"Invalid SECRET_ENCRYPTION_KEY. "
                f"Generate a valid key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'. "
                f"Error: {e}"
            )

        logger.info("Secret service initialized with Fernet encryption")

    def encrypt(self, value: str) -> str:
        """Encrypt a secret value.

        Args:
            value: Plain text secret value

        Returns:
            Encrypted value as base64-encoded string
        """
        if not isinstance(value, str):
            value = str(value)

        encrypted = self.fernet.encrypt(value.encode())
        return encrypted.decode()

    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt a secret value.

        Args:
            encrypted_value: Encrypted secret value

        Returns:
            Decrypted plain text value

        Raises:
            ValueError: If decryption fails (invalid key or corrupted data)
        """
        try:
            decrypted = self.fernet.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except (InvalidToken, InvalidKey) as e:
            logger.error("Failed to decrypt secret - invalid key or corrupted data")
            raise ValueError("Failed to decrypt secret. The encryption key may have changed.")

    def encrypt_dict(self, data: dict) -> dict:
        """Encrypt all string values in a dictionary.

        Args:
            data: Dictionary with plain text values

        Returns:
            Dictionary with encrypted values
        """
        return {k: self.encrypt(v) for k, v in data.items()}

    def decrypt_dict(self, encrypted_data: dict) -> dict:
        """Decrypt all values in a dictionary.

        Args:
            encrypted_data: Dictionary with encrypted values

        Returns:
            Dictionary with decrypted values
        """
        return {k: self.decrypt(v) for k, v in encrypted_data.items()}

    def validate_encryption_key(self) -> bool:
        """Validate that the current encryption key is working.

        Returns:
            True if key is valid, False otherwise
        """
        try:
            test_value = "test_validation_string"
            encrypted = self.encrypt(test_value)
            decrypted = self.decrypt(encrypted)
            return decrypted == test_value
        except Exception:
            return False

    def get_encryption_key_status(self) -> dict:
        """Get status of encryption key configuration.

        Returns:
            Dictionary with key status information
        """
        return {
            "configured": bool(settings.secret_encryption_key),
            "valid": self.validate_encryption_key() if settings.secret_encryption_key else False,
            "key_preview": settings.secret_encryption_key[:10] + "..." if settings.secret_encryption_key else None,
        }


# Singleton instance
_secret_service: Optional[SecretService] = None


def get_secret_service() -> SecretService:
    """Get or create the singleton SecretService instance."""
    global _secret_service
    if _secret_service is None:
        _secret_service = SecretService()
    return _secret_service


def set_secret_service(service: SecretService) -> None:
    """Set the singleton SecretService instance (for testing)."""
    global _secret_service
    _secret_service = service
