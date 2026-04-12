"""
Tests for core security and token blacklist modules.
"""

import pytest
import pytest_asyncio

from core.security import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from core.token_blacklist import (
    TokenBlacklist,
    add_token_to_blacklist,
    get_token_blacklist,
    verify_token_not_blacklisted,
)


class TestPasswordHashing:
    """Test password hashing functions."""

    def test_password_hash_creates_different_hashes(self):
        """Same password should create different hashes due to salt."""
        password = "test_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2
        assert hash1.startswith("$2b$")
        assert hash2.startswith("$2b$")

    def test_verify_password_correct(self):
        """Correct password should verify successfully."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Incorrect password should fail verification."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password("wrong_password", hashed) is False

    def test_verify_password_empty(self):
        """Empty password should fail verification."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert verify_password("", hashed) is False


class TestJWTokens:
    """Test JWT token creation and decoding."""

    def test_create_access_token(self):
        """Should create a valid JWT token."""
        data = {"sub": "test_user", "user_id": "123"}
        token = create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT has 3 parts

    def test_decode_token_valid(self):
        """Should decode a valid token."""
        data = {"sub": "test_user", "user_id": "123"}
        token = create_access_token(data)

        decoded = decode_token(token)

        assert decoded is not None
        assert decoded["sub"] == "test_user"
        assert decoded["user_id"] == "123"

    def test_decode_token_invalid(self):
        """Should return None for invalid token."""
        invalid_token = "invalid.token.here"

        decoded = decode_token(invalid_token)

        assert decoded is None

    def test_decode_token_empty(self):
        """Should return None for empty token."""
        decoded = decode_token("")

        assert decoded is None


class TestTokenBlacklist:
    """Test token blacklist functionality."""

    @pytest_asyncio.fixture
    async def blacklist(self):
        """Create a fresh TokenBlacklist instance for each test."""
        return TokenBlacklist()

    @pytest.mark.asyncio
    async def test_add_token_to_blacklist(self, blacklist):
        """Should add token to blacklist."""
        token = "test-token-123"

        await blacklist.add_to_blacklist(token)

        assert await blacklist.is_blacklisted(token) is True

    @pytest.mark.asyncio
    async def test_is_blacklisted_false_for_new_token(self, blacklist):
        """New token should not be blacklisted."""
        token = "new-test-token-456"

        assert await blacklist.is_blacklisted(token) is False

    @pytest.mark.asyncio
    async def test_remove_from_blacklist(self, blacklist):
        """Should remove token from blacklist."""
        token = "token-to-remove"

        await blacklist.add_to_blacklist(token)
        assert await blacklist.is_blacklisted(token) is True

        await blacklist.remove_from_blacklist(token)
        assert await blacklist.is_blacklisted(token) is False

    @pytest.mark.asyncio
    async def test_blacklist_persistence(self, blacklist):
        """Blacklisted token should remain blacklisted."""
        token = "persistent-token-345"

        await blacklist.add_to_blacklist(token)

        # Check multiple times
        assert await blacklist.is_blacklisted(token) is True
        assert await blacklist.is_blacklisted(token) is True
        assert await blacklist.is_blacklisted(token) is True

    @pytest.mark.asyncio
    async def test_get_blacklist_info(self, blacklist):
        """Should return blacklist info."""
        token = "info-test-token"
        await blacklist.add_to_blacklist(token)

        info = await blacklist.get_blacklist_info()

        assert "fallback" in info
        assert info["fallback"]["count"] >= 1

    @pytest.mark.asyncio
    async def test_global_blacklist_instance(self):
        """Should return same global instance."""
        instance1 = get_token_blacklist()
        instance2 = get_token_blacklist()

        assert instance1 is instance2

    @pytest.mark.asyncio
    async def test_add_token_to_blacklist_helper(self):
        """Helper function should add token to blacklist."""
        token = "helper-test-token"

        await add_token_to_blacklist(token)
        blacklist = get_token_blacklist()

        assert await blacklist.is_blacklisted(token) is True

    @pytest.mark.asyncio
    async def test_verify_token_not_blacklisted_passes(self):
        """Non-blacklisted token should pass verification."""
        token = "valid-token"

        result = await verify_token_not_blacklisted(token)

        assert result is True
