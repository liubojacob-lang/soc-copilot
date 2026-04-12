"""Tests for JWT token invalidation after user updates."""

from datetime import UTC, datetime, timedelta

from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    is_token_invalidated_by_user_update,
)


class TestTokenInvalidationByUserUpdate:
    """Test that tokens are invalidated when user data changes."""

    def test_new_token_has_iat_claim(self):
        """Verify that new tokens include 'iat' (issued at) claim."""
        token = create_access_token(data={"sub": "user-123"})
        payload = decode_token(token)

        assert payload is not None
        assert "iat" in payload
        assert "exp" in payload
        assert payload["type"] == "access"
        assert payload["sub"] == "user-123"

    def test_refresh_token_has_iat_claim(self):
        """Verify that refresh tokens also include 'iat' claim."""
        token = create_refresh_token(data={"sub": "user-123"})
        payload = decode_token(token)

        assert payload is not None
        assert "iat" in payload
        assert payload["type"] == "refresh"

    def test_token_valid_when_no_user_update(self):
        """Token should be valid when user has no updated_at."""
        token = create_access_token(data={"sub": "user-123"})
        payload = decode_token(token)

        is_invalid = is_token_invalidated_by_user_update(payload, user_updated_at=None)
        assert is_invalid is False

    def test_token_valid_when_issued_after_update(self):
        """Token should be valid if issued AFTER user update."""
        # Simulate user update timestamp (5 minutes ago)
        user_updated = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()

        # Create token now (after update)
        token = create_access_token(data={"sub": "user-123"})
        payload = decode_token(token)

        is_invalid = is_token_invalidated_by_user_update(payload, user_updated)
        assert is_invalid is False

    def test_token_invalidated_when_issued_before_update(self):
        """Token should be invalidated if issued BEFORE user update."""
        # Create token first
        token = create_access_token(data={"sub": "user-123"})
        payload = decode_token(token)

        # Simulate user update happened AFTER token was issued
        user_updated = (datetime.now(UTC) + timedelta(minutes=1)).isoformat()

        is_invalid = is_token_invalidated_by_user_update(payload, user_updated)
        assert is_invalid is True

    def test_role_change_invalidates_old_tokens(self):
        """Changing user role should invalidate tokens issued before the change."""
        # Create token with old role
        token = create_access_token(data={"sub": "user-123", "role": "analyst"})
        payload = decode_token(token)

        # Simulate admin changed user's role (updated_at is now)
        user_updated = (datetime.now(UTC) + timedelta(seconds=1)).isoformat()

        # Old token should be invalidated
        is_invalid = is_token_invalidated_by_user_update(payload, user_updated)
        assert is_invalid is True

    def test_password_change_invalidates_old_tokens(self):
        """Changing password should invalidate tokens issued before the change."""
        token = create_access_token(data={"sub": "user-123"})
        payload = decode_token(token)

        # Simulate password change
        user_updated = (datetime.now(UTC) + timedelta(seconds=1)).isoformat()

        is_invalid = is_token_invalidated_by_user_update(payload, user_updated)
        assert is_invalid is True

    def test_user_deactivation_invalidates_tokens(self):
        """Deactivating user should invalidate all existing tokens."""
        token = create_access_token(data={"sub": "user-123"})
        payload = decode_token(token)

        # Simulate user deactivation
        user_updated = (datetime.now(UTC) + timedelta(seconds=1)).isoformat()

        is_invalid = is_token_invalidated_by_user_update(payload, user_updated)
        assert is_invalid is True

    def test_invalid_updated_at_format_allows_token(self):
        """Malformed updated_at should not break authentication (fallback)."""
        token = create_access_token(data={"sub": "user-123"})
        payload = decode_token(token)

        # Invalid date format
        is_invalid = is_token_invalidated_by_user_update(payload, "not-a-date")
        assert is_invalid is False  # Fallback: allow token

    def test_token_without_iat_claim_is_rejected(self):
        """Old tokens without 'iat' claim should be rejected."""
        # Manually create a token without iat (simulating old behavior)
        from jose import jwt

        from core.security import JWT_ALGORITHM, get_jwt_secret

        old_token = jwt.encode(
            {
                "sub": "user-123",
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "type": "access",
            },
            get_jwt_secret(),
            algorithm=JWT_ALGORITHM,
        )
        payload = decode_token(old_token)

        # Token without iat should be rejected when user has updated_at
        user_updated = datetime.now(UTC).isoformat()
        is_invalid = is_token_invalidated_by_user_update(payload, user_updated)
        assert is_invalid is True

    def test_concurrent_requests_during_update(self):
        """Requests during update window should behave correctly."""
        # Create token
        token = create_access_token(data={"sub": "user-123"})
        payload = decode_token(token)

        # Update happened at exactly the same time
        user_updated = datetime.now(UTC).isoformat()

        # This is an edge case - token iat might be slightly before or after
        # Implementation should handle this gracefully
        is_invalid = is_token_invalidated_by_user_update(payload, user_updated)
        # Result depends on exact timing, but shouldn't crash
        assert isinstance(is_invalid, bool)
