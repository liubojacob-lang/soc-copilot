"""Comprehensive tests for AuthService business logic, lockout, and token rotation."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from core.security import create_access_token, create_refresh_token, get_password_hash
from models.user import UserModel, UserRole
from schemas.user import ChangePasswordRequest, UserLogin
from services.auth_service import MAX_LOGIN_ATTEMPTS, AuthService


def _make_mock_user(
    username="analyst_alice",
    password="ValidPassword123!",
    is_active=True,
    failed_attempts=0,
    locked_until=None,
    must_change_password=False,
):
    user = UserModel(
        id="user-uuid-1234",
        tenant_id="default",
        username=username,
        email=f"{username}@example.com",
        hashed_password=get_password_hash(password),
        role=UserRole.ANALYST.value,
        is_active=is_active,
        failed_login_attempts=failed_attempts,
        locked_until=locked_until,
        must_change_password=must_change_password,
    )
    return user


@pytest.fixture
def auth_service():
    session = AsyncMock()
    service = AuthService(session)
    service.user_repo = AsyncMock()
    service.audit_repo = AsyncMock()
    service.commit = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_authenticate_success(auth_service):
    user = _make_mock_user()
    auth_service.user_repo.get_by_username.return_value = user

    creds = UserLogin(username=user.username, password="ValidPassword123!")
    ret_user, access_token, refresh_token = await auth_service.authenticate(creds)

    assert ret_user.id == user.id
    assert access_token is not None
    assert refresh_token is not None
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
    auth_service.user_repo.update_last_login.assert_awaited_once_with(user.id)
    auth_service.audit_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_authenticate_user_not_found(auth_service):
    auth_service.user_repo.get_by_username.return_value = None

    creds = UserLogin(username="ghost_user", password="AnyPassword123!")
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.authenticate(creds)

    assert exc_info.value.status_code == 401
    assert "Incorrect username or password" in exc_info.value.detail


@pytest.mark.asyncio
async def test_authenticate_account_locked_active(auth_service):
    future_time = datetime.now(UTC) + timedelta(minutes=20)
    user = _make_mock_user(locked_until=future_time)
    auth_service.user_repo.get_by_username.return_value = user

    creds = UserLogin(username=user.username, password="ValidPassword123!")
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.authenticate(creds)

    assert exc_info.value.status_code == 423
    assert "Account locked" in exc_info.value.detail


@pytest.mark.asyncio
async def test_authenticate_account_locked_expired(auth_service):
    past_time = datetime.now(UTC) - timedelta(minutes=5)
    user = _make_mock_user(locked_until=past_time, failed_attempts=5)
    auth_service.user_repo.get_by_username.return_value = user

    creds = UserLogin(username=user.username, password="ValidPassword123!")
    ret_user, _access_token, _refresh_token = await auth_service.authenticate(creds)

    assert ret_user.id == user.id
    assert user.locked_until is None
    assert user.failed_login_attempts == 0


@pytest.mark.asyncio
async def test_authenticate_wrong_password_under_limit(auth_service):
    user = _make_mock_user(failed_attempts=2)
    auth_service.user_repo.get_by_username.return_value = user

    creds = UserLogin(username=user.username, password="WrongPassword123!")
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.authenticate(creds)

    assert exc_info.value.status_code == 401
    assert user.failed_login_attempts == 3
    assert user.locked_until is None


@pytest.mark.asyncio
async def test_authenticate_wrong_password_triggers_lockout(auth_service):
    user = _make_mock_user(failed_attempts=MAX_LOGIN_ATTEMPTS - 1)
    auth_service.user_repo.get_by_username.return_value = user

    creds = UserLogin(username=user.username, password="WrongPassword123!")
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.authenticate(creds)

    assert exc_info.value.status_code == 423
    assert user.failed_login_attempts == MAX_LOGIN_ATTEMPTS
    assert user.locked_until is not None
    assert "Account locked for 30 minutes" in exc_info.value.detail


@pytest.mark.asyncio
async def test_authenticate_disabled_account(auth_service):
    user = _make_mock_user(is_active=False)
    auth_service.user_repo.get_by_username.return_value = user

    creds = UserLogin(username=user.username, password="ValidPassword123!")
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.authenticate(creds)

    assert exc_info.value.status_code == 403
    assert "Account is disabled" in exc_info.value.detail


@pytest.mark.asyncio
async def test_refresh_tokens_success(auth_service):
    user = _make_mock_user()
    auth_service.user_repo.get_by_id.return_value = user

    valid_refresh = create_refresh_token(data={"sub": user.id, "role": user.role})

    with patch("services.auth_service.get_token_blacklist") as mock_bl:
        mock_blacklist_inst = AsyncMock()
        mock_blacklist_inst.is_blacklisted.return_value = False
        mock_bl.return_value = mock_blacklist_inst

        ret_user, new_access, new_refresh = await auth_service.refresh_tokens(
            valid_refresh
        )

        assert ret_user.id == user.id
        assert new_access is not None
        assert new_refresh is not None
        auth_service.audit_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_tokens_invalid_type(auth_service):
    access_tok = create_access_token(data={"sub": "user-123", "role": "admin"})

    with pytest.raises(HTTPException) as exc_info:
        await auth_service.refresh_tokens(access_tok)

    assert exc_info.value.status_code == 401
    assert "Invalid refresh token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_refresh_tokens_already_blacklisted(auth_service):
    valid_refresh = create_refresh_token(data={"sub": "user-123", "role": "admin"})

    with patch("services.auth_service.get_token_blacklist") as mock_bl:
        mock_blacklist_inst = AsyncMock()
        mock_blacklist_inst.is_blacklisted.return_value = True
        mock_bl.return_value = mock_blacklist_inst

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_tokens(valid_refresh)

        assert exc_info.value.status_code == 401
        assert "revoked" in exc_info.value.detail


@pytest.mark.asyncio
async def test_refresh_tokens_user_inactive_or_missing(auth_service):
    valid_refresh = create_refresh_token(data={"sub": "user-123", "role": "admin"})

    with patch("services.auth_service.get_token_blacklist") as mock_bl:
        mock_blacklist_inst = AsyncMock()
        mock_blacklist_inst.is_blacklisted.return_value = False
        mock_bl.return_value = mock_blacklist_inst

        auth_service.user_repo.get_by_id.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await auth_service.refresh_tokens(valid_refresh)
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_logout_blacklists_tokens(auth_service):
    with patch(
        "services.auth_service.add_token_to_blacklist", new_callable=AsyncMock
    ) as mock_bl:
        await auth_service.logout(
            user_id="user-123",
            access_token="acc-tok",
            refresh_token="ref-tok",
            bearer_token="bear-tok",
        )
        assert mock_bl.await_count == 3
        auth_service.audit_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_change_password_flow(auth_service):
    user = _make_mock_user(password="OldPass123!")

    # 1. Incorrect current password
    bad_current = ChangePasswordRequest(
        current_password="WrongOldPassword!",
        new_password="NewPass123!",
        confirm_password="NewPass123!",
    )
    with pytest.raises(HTTPException) as exc:
        await auth_service.change_password(user, bad_current)
    assert exc.value.status_code == 400
    assert "Current password is incorrect" in exc.value.detail

    # 2. Confirm password mismatch
    mismatch = ChangePasswordRequest(
        current_password="OldPass123!",
        new_password="NewPass123!",
        confirm_password="DifferentPass123!",
    )
    with pytest.raises(HTTPException) as exc:
        await auth_service.change_password(user, mismatch)
    assert exc.value.status_code == 400
    assert "do not match" in exc.value.detail

    # 3. Password reused in history
    reused_req = ChangePasswordRequest(
        current_password="OldPass123!",
        new_password="RecentPass123!",
        confirm_password="RecentPass123!",
    )
    with patch("services.auth_service.check_password_history", return_value=True):
        with pytest.raises(HTTPException) as exc:
            await auth_service.change_password(user, reused_req)
        assert exc.value.status_code == 400
        assert "Cannot reuse recent passwords" in exc.value.detail

    # 4. Success
    valid_req = ChangePasswordRequest(
        current_password="OldPass123!",
        new_password="NewSecurePass456!",
        confirm_password="NewSecurePass456!",
    )
    with patch("services.auth_service.check_password_history", return_value=False):
        await auth_service.change_password(user, valid_req)
        assert user.must_change_password is False
        auth_service.user_repo.update_password.assert_awaited_once()
        auth_service.commit.assert_awaited()


@pytest.mark.asyncio
async def test_unlock_user(auth_service):
    user = _make_mock_user(failed_attempts=5, locked_until=datetime.now(UTC))
    auth_service.user_repo.get_by_username.return_value = user

    unlocked = await auth_service.unlock_user(
        admin_id="admin-99", username=user.username
    )
    assert unlocked.failed_login_attempts == 0
    assert unlocked.locked_until is None
    auth_service.audit_repo.create.assert_awaited_once()
    auth_service.commit.assert_awaited()

    # User not found
    auth_service.user_repo.get_by_username.return_value = None
    with pytest.raises(HTTPException) as exc:
        await auth_service.unlock_user(admin_id="admin-99", username="nobody")
    assert exc.value.status_code == 404
