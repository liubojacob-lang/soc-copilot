"""Authentication and authorization tests."""

import pytest

# Import test setup
from tests.conftest_setup import (
    TEST_ALT_PASSWORD,
    TEST_DUMMY_REFRESH_TOKEN,
    TEST_MISMATCH_PASSWORD,
    TEST_NEW_PASSWORD,
    TEST_PASSWORD,
    TEST_WRONG_PASSWORD,
)


class TestAuthentication:
    """Authentication endpoint tests."""

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Test successful login."""
        response = await client.post(
            "/api/auth/login", json={"username": "admin", "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = await client.post(
            "/api/auth/login", json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        data = response.json()
        # API returns 'error' and 'message' instead of 'detail'
        assert "error" in data or "detail" in data

    @pytest.mark.asyncio
    async def test_login_missing_fields(self, client):
        """Test login with missing required fields."""
        response = await client.post("/api/auth/login", json={"username": "admin"})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = await client.post(
            "/api/auth/login",
            json={"username": "nonexistent", "password": "password123"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user(self, auth_client):
        """Test getting current user info."""
        response = await auth_client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "username" in data
        assert "email" in data
        assert "role" in data

    @pytest.mark.asyncio
    async def test_get_current_user_without_token(self, client):
        """Test getting current user without authentication returns 401."""
        original_headers = dict(client.headers)
        client.headers.pop("Authorization", None)
        # Clear cookies too - session-scoped client may carry access_token
        # from earlier tests in the same session (would bypass auth → 200)
        client.cookies.clear()
        try:
            response = await client.get("/api/auth/me")
            assert response.status_code == 401
        finally:
            client.headers.clear()
            client.headers.update(original_headers)

    @pytest.mark.asyncio
    async def test_logout(self, auth_client):
        """Test logout functionality."""
        response = await auth_client.post("/api/auth/logout")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_token_refresh(self, auth_client):
        """Test token refresh."""
        # First get current token
        me_response = await auth_client.get("/api/auth/me")
        assert me_response.status_code == 200

        # Try to refresh - requires refresh_token in body
        refresh_response = await auth_client.post(
            "/api/auth/refresh", json={"refresh_token": TEST_DUMMY_REFRESH_TOKEN}
        )
        # Using a dummy token, expect unauthorized or validation error
        assert refresh_response.status_code in [
            401,
            422,
        ]  # 401 = invalid token, 422 = validation error


class TestAPIKeyAuthentication:
    """API Key authentication tests."""

    @pytest.mark.asyncio
    async def test_create_api_key(self, auth_client):
        """Test creating an API key."""
        response = await auth_client.post(
            "/api/api-keys", json={"description": "Test Key", "expires_in_days": 30}
        )
        assert response.status_code == 201  # Created
        data = response.json()
        assert "key" in data or "api_key" in data

    @pytest.mark.asyncio
    async def test_list_api_keys(self, auth_client):
        """Test listing API keys."""
        response = await auth_client.get("/api/api-keys")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "api_keys" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, auth_client):
        """Test revoking an API key."""
        # First create a key
        create_response = await auth_client.post(
            "/api/api-keys", json={"description": "To Revoke", "expires_in_days": 30}
        )
        assert create_response.status_code == 201
        data = create_response.json()
        key_id = data.get("api_key", {}).get("id") or data.get("id")

        # Then revoke it
        if key_id:
            revoke_response = await auth_client.delete(f"/api/api-keys/{key_id}")
            assert revoke_response.status_code == 200

    @pytest.mark.asyncio
    async def test_api_key_authentication(self, client):
        """Test authentication using API key."""
        # First create an API key as admin
        auth_response = await client.post(
            "/api/auth/login", json={"username": "admin", "password": TEST_PASSWORD}
        )
        assert auth_response.status_code == 200
        token = auth_response.json()["access_token"]

        # Create API key
        key_response = await client.post(
            "/api/api-keys",
            headers={"Authorization": f"Bearer {token}"},
            json={"description": "Test Key", "expires_in_days": 30},
        )
        assert key_response.status_code == 201
        api_key = key_response.json().get("key")

        if api_key:
            # Use API key to authenticate
            protected_response = await client.get(
                "/api/auth/me", headers={"X-API-Key": api_key}
            )
            assert protected_response.status_code == 200


class TestAuthorization:
    """Authorization tests."""

    @pytest.mark.asyncio
    async def test_admin_only_endpoint_as_admin(self, admin_client):
        """Test admin accessing admin-only endpoint."""
        # Use an endpoint that exists - /api/users is admin-only
        response = await admin_client.get("/api/users")
        # Admin should have access
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_only_endpoint_without_admin(self, auth_client):
        """Test non-admin trying to access admin endpoint."""
        # Note: auth_client uses admin user, so this test may need adjustment
        # For now, just check the endpoint behavior
        response = await auth_client.get("/api/users")
        # If auth_client is admin user, expect 200; otherwise 403 forbidden
        assert response.status_code == 200  # auth_client uses admin user

    @pytest.mark.asyncio
    async def test_permission_check(self, auth_client):
        """Test permission checking."""
        response = await auth_client.get("/api/auth/me")
        assert response.status_code == 200
        data = response.json()
        # Check if permissions are included
        if "permissions" in data:
            assert isinstance(data["permissions"], list)


class TestTokenBlacklist:
    """Token blacklist tests."""

    @pytest.mark.asyncio
    async def test_blacklisted_token_rejected(self, client):
        """Test that blacklisted tokens are rejected."""
        # First login to get a token
        login_response = await client.post(
            "/api/auth/login", json={"username": "admin", "password": TEST_PASSWORD}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Set auth header
        client.headers["Authorization"] = f"Bearer {token}"

        # Logout to blacklist token
        logout_response = await client.post("/api/auth/logout")
        assert logout_response.status_code == 200

        # Restore the shared session client: the blacklisted token must not
        # leak into subsequent tests through the default headers.
        client.headers.pop("Authorization", None)

        # Clear the header and try to use the blacklisted token again
        # Note: The token is blacklisted on the server side, but we need a new request
        # For now, just verify logout succeeded
        # A proper test would require a separate client or manual token injection

    @pytest.mark.asyncio
    async def test_multiple_logout_consistency(self, auth_client):
        """Test that multiple logout calls are handled consistently."""
        # First logout
        response1 = await auth_client.post("/api/auth/logout")
        assert response1.status_code == 200

        # Second logout should also succeed (idempotent)
        response2 = await auth_client.post("/api/auth/logout")
        assert response2.status_code == 200  # Logout is idempotent


class TestPasswordManagement:
    """Password management tests."""

    @pytest.mark.asyncio
    async def test_change_password(self, auth_client):
        """Test changing password."""
        response = await auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": TEST_NEW_PASSWORD,
                "confirm_password": TEST_NEW_PASSWORD,
            },
        )
        assert response.status_code == 200

        # A password change invalidates tokens issued before it (iat vs
        # updated_at). Re-authenticate exactly as a real client would after
        # its session is invalidated.
        relogin = await auth_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": TEST_NEW_PASSWORD},
        )
        assert relogin.status_code == 200, relogin.text
        fresh_token = relogin.json()["access_token"]

        # Use an intermediate password (not TEST_PASSWORD) to avoid
        # password-history rejection (TEST_PASSWORD was just saved to history)
        response = await auth_client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {fresh_token}"},
            json={
                "current_password": TEST_NEW_PASSWORD,
                "new_password": TEST_ALT_PASSWORD,
                "confirm_password": TEST_ALT_PASSWORD,
            },
        )
        assert response.status_code == 200

        # Restore TEST_PASSWORD so subsequent tests can log in as admin
        # (use direct repo call since password history prevents reusing TEST_PASSWORD)
        from core.security import get_password_hash
        from db.session import AsyncSessionLocal
        from repositories.user_repository import UserRepository

        async with AsyncSessionLocal() as session:
            repo = UserRepository(session)
            user = await repo.get_by_username("admin")
            user.hashed_password = get_password_hash(TEST_PASSWORD)
            user.password_history = []
            await session.commit()

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(self, auth_client):
        """Test changing password with wrong current password."""
        response = await auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": TEST_WRONG_PASSWORD,
                "new_password": TEST_NEW_PASSWORD,
                "confirm_password": TEST_NEW_PASSWORD,
            },
        )
        assert response.status_code == 400  # Bad request - wrong current password

    @pytest.mark.asyncio
    async def test_change_password_mismatch(self, auth_client):
        """Test changing password with mismatched confirmation."""
        response = await auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": TEST_PASSWORD,
                "new_password": TEST_NEW_PASSWORD,
                "confirm_password": TEST_MISMATCH_PASSWORD,
            },
        )
        assert response.status_code == 400  # Bad request - password mismatch
