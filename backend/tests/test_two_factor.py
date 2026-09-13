"""Unit and integration tests for Two-Factor Authentication (TOTP)."""

import pyotp
import pytest

from services.totp_service import TOTPService
from tests.conftest_setup import TEST_PASSWORD


class TestTOTPService:
    """Test TOTP generation, validation, and backup codes."""

    def test_generate_secret(self):
        secret = TOTPService.generate_secret()
        assert isinstance(secret, str)
        assert len(secret) == 32

    def test_verify_code_success(self):
        secret = TOTPService.generate_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()

        valid, used_backup, _ = TOTPService.verify_code(secret, code)
        assert valid is True
        assert used_backup is False

    def test_verify_code_invalid(self):
        secret = TOTPService.generate_secret()
        valid, _, _ = TOTPService.verify_code(secret, "000000")
        assert valid is False

    def test_verify_backup_code(self):
        secret = TOTPService.generate_secret()
        backup_codes = ["abcd-1234", "efgh-5678"]

        valid, used_backup, remaining = TOTPService.verify_code(
            secret, "abcd-1234", backup_codes=backup_codes
        )
        assert valid is True
        assert used_backup is True
        assert remaining == ["efgh-5678"]


class TestTwoFactorEndpoints:
    """Test 2FA API endpoints."""

    @pytest.mark.asyncio
    async def test_2fa_flow(self, auth_client):
        # 1. Check initial status
        res = await auth_client.get("/api/v1/auth/2fa/status")
        assert res.status_code == 200
        data = res.json()
        assert "is_enabled" in data
        assert "policy" in data

        # 2. Setup 2FA
        res = await auth_client.post("/api/v1/auth/2fa/setup")
        assert res.status_code == 200
        setup_data = res.json()
        assert "secret" in setup_data
        assert "qr_code" in setup_data
        assert "backup_codes" in setup_data
        secret = setup_data["secret"]

        # 3. Enable 2FA with valid TOTP
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()

        enable_res = await auth_client.post(
            "/api/v1/auth/2fa/enable",
            json={
                "secret": secret,
                "code": valid_code,
                "policy": "sudo",
                "backup_codes": setup_data["backup_codes"],
            },
        )
        assert enable_res.status_code == 200
        assert enable_res.json()["is_enabled"] is True
        assert enable_res.json()["policy"] == "sudo"

        # 4. Verify Sudo Mode
        sudo_code = totp.now()
        sudo_res = await auth_client.post(
            "/api/v1/auth/2fa/verify-sudo",
            json={"code": sudo_code},
        )
        assert sudo_res.status_code == 200
        sudo_data = sudo_res.json()
        assert sudo_data["valid"] is True
        assert "sudo_token" in sudo_data

        # 5. Switch Policy to login
        switch_code = totp.now()
        policy_res = await auth_client.post(
            "/api/v1/auth/2fa/policy",
            json={"policy": "login", "code": switch_code},
        )
        assert policy_res.status_code == 200
        assert policy_res.json()["policy"] == "login"

        # 6. Disable 2FA
        disable_code = totp.now()
        disable_res = await auth_client.post(
            "/api/v1/auth/2fa/disable",
            json={"password": TEST_PASSWORD, "code": disable_code},
        )
        assert disable_res.status_code == 200
        assert disable_res.json()["is_enabled"] is False
