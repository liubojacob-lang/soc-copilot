"""Unit tests for the database-backed RBAC in ``dependencies.auth``.

These replaced tests for ``dependencies/rbac.py``, a second ``require_permission``
factory that read a ``user.permissions`` attribute nothing sets and never joined
the RBAC tables. The real implementation is ``check_permission_in_db``, which
``routers/users.py`` and ``routers/admin_settings.py`` already depend on.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from dependencies.auth import check_permission_in_db, require_permission
from models.user import UserRole

pytestmark = [pytest.mark.unit]


def _user(role):
    return MagicMock(role=role)


def _session(permission_rows=()):
    """Session whose Role->permissions join returns ``permission_rows``."""
    scalars = MagicMock()
    scalars.first.return_value = permission_rows[0] if permission_rows else None
    result = MagicMock()
    result.scalars.return_value = scalars
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
    return session


class TestCheckPermissionInDb:
    async def test_admin_short_circuits_without_touching_the_database(self):
        session = _session()
        assert await check_permission_in_db(session, _user(UserRole.ADMIN), "admin", "write")
        session.execute.assert_not_awaited()

    async def test_database_grant_authorises_a_non_admin(self):
        session = _session([MagicMock()])
        assert await check_permission_in_db(session, _user(UserRole.ANALYST), "admin", "read")

    async def test_role_map_is_the_fallback_when_no_row_grants_it(self):
        session = _session()
        assert await check_permission_in_db(session, _user(UserRole.ANALYST), "assets", "read")
        assert not await check_permission_in_db(
            session, _user(UserRole.AUDITOR), "assets", "write"
        )

    async def test_string_valued_role_is_accepted(self):
        """``users.role`` is stored as text, so both forms must work."""
        session = _session()
        assert await check_permission_in_db(session, _user("analyst"), "assets", "read")
        assert not await check_permission_in_db(session, _user("auditor"), "users", "write")


class TestRequirePermissionDependency:
    async def test_returns_the_user_when_granted(self):
        checker = require_permission("admin", "write")
        user = _user(UserRole.ADMIN)
        assert await checker(current_user=user, session=_session()) is user

    async def test_raises_403_naming_the_missing_permission(self):
        checker = require_permission("admin", "write")
        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=_user(UserRole.ANALYST), session=_session())
        assert exc_info.value.status_code == 403
        assert "admin:write" in exc_info.value.detail


class TestSeedRBAC:
    """T3.6: Tests for RBAC database seeding."""

    async def test_seed_rbac_structure(self):
        from services.rbac_service import SYSTEM_PERMISSIONS, SYSTEM_ROLE_PERMISSIONS
        assert len(SYSTEM_PERMISSIONS) >= 15
        assert "admin" in SYSTEM_ROLE_PERMISSIONS
        assert "analyst" in SYSTEM_ROLE_PERMISSIONS
        assert "auditor" in SYSTEM_ROLE_PERMISSIONS

    async def test_seed_rbac_execution(self):
        from services.rbac_service import seed_rbac

        # Mock session that records adds and executes
        added_objs = []
        session = MagicMock()
        session.add = MagicMock(side_effect=lambda obj: added_objs.append(obj))
        session.flush = AsyncMock()
        session.commit = AsyncMock()

        # First run: empty existing roles and permissions
        res_empty = MagicMock()
        res_empty.scalars.return_value.all.return_value = []
        res_empty.all.return_value = []

        session.execute = AsyncMock(return_value=res_empty)

        roles_created, perms_created = await seed_rbac(session)
        assert roles_created == 3
        assert perms_created >= 15
        assert session.commit.called

