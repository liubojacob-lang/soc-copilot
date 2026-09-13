"""Unit tests for the RBAC dependency factory."""

import enum

import pytest
from fastapi import HTTPException

from dependencies.rbac import require_permission

pytestmark = [pytest.mark.unit]


class Role(str, enum.Enum):
    ADMIN = "admin"
    ANALYST = "analyst"


class TestRequirePermission:
    async def test_admin_string_role_bypasses(self):
        checker = require_permission("alerts:write")

        class AdminUser:
            role = "admin"
            permissions = []

        assert await checker(current_user=AdminUser()) is None

    async def test_admin_enum_role_bypasses(self):
        checker = require_permission("alerts:write")

        class AdminUser:
            role = Role.ADMIN

        assert await checker(current_user=AdminUser()) is None

    async def test_user_with_permission_passes(self):
        checker = require_permission("alerts:write")

        class Analyst:
            role = Role.ANALYST
            permissions = ["alerts:read", "alerts:write"]

        assert await checker(current_user=Analyst()) is None

    async def test_missing_permission_raises_403(self):
        checker = require_permission("alerts:delete")

        class Analyst:
            role = "analyst"
            permissions = ["alerts:read"]

        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=Analyst())
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Missing permission: alerts:delete"

    async def test_user_without_permissions_attribute_raises_403(self):
        checker = require_permission("alerts:read")

        class Analyst:
            role = "analyst"

        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=Analyst())
        assert exc_info.value.status_code == 403

    async def test_role_defaults_to_analyst_when_missing(self):
        checker = require_permission("cases:read")

        class BareUser:
            permissions = []

        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=BareUser())
        assert exc_info.value.status_code == 403

    async def test_empty_permissions_list_is_treated_as_missing(self):
        checker = require_permission("alerts:read")

        class Analyst:
            role = "analyst"
            permissions = None

        with pytest.raises(HTTPException):
            await checker(current_user=Analyst())
