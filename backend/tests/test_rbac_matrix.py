"""RBAC matrix tests — role x endpoint coverage for representative routes.

Verifies the three auth outcomes that matter in production:
- anonymous requests are rejected with 401
- authenticated non-admin users are rejected with 403 on admin-only routes
- admins pass

Run against the real app via the shared integration fixtures.
"""

import secrets

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_PASSWORD

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

# (method, path, admin_expected, analyst_expected, anon_expected)
RBAC_MATRIX = [
    ("GET", "/api/v1/users", 200, 403, 401),
    # audit-logs owner-scopes analysts to their own entries (routers/audit.py)
    ("GET", "/api/v1/audit-logs", 200, 200, 401),
    ("GET", "/api/v1/secrets", 200, 403, 401),
    ("GET", "/api/v1/assets", 200, 200, 401),
    ("GET", "/api/v1/cases", 200, 200, 401),
    ("GET", "/api/v1/playbook-definitions", 200, 200, 401),
    ("GET", "/api/v1/threat-hunting/hypotheses", 200, 200, 401),
    ("GET", "/api/v1/ai/models", 200, 200, 401),
    ("GET", "/api/v1/dashboard/stats", 200, 200, 401),
]


async def _login(client: AsyncClient, username: str, password: str) -> dict:
    response = await client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
async def admin_headers(client):
    body = await _login(client, "admin", TEST_PASSWORD)
    # Never mutate the shared client's default headers: the anon leg of the
    # matrix must be truly anonymous.
    return {"Authorization": f"Bearer {body.get('access_token')}"}


@pytest.fixture
async def analyst_headers(client, admin_headers):
    """Create an analyst account (runtime-generated credentials) and log in."""
    username = f"rbac_probe_{secrets.token_hex(4)}"
    password = f"RbacProbe-{secrets.token_urlsafe(12)}!9"
    create = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": username,
            "password": password,
            "email": f"{username}@example.com",
            "role": "analyst",
        },
    )
    assert create.status_code == 201, create.text
    body = await _login(client, username, password)
    return {"Authorization": f"Bearer {body.get('access_token')}"}


@pytest.mark.parametrize(
    "method,path,admin_expected,analyst_expected,anon_expected", RBAC_MATRIX
)
async def test_rbac_matrix(
    client,
    admin_headers,
    analyst_headers,
    method,
    path,
    admin_expected,
    analyst_expected,
    anon_expected,
):
    # The login probes left session cookies in the shared client jar; the
    # anon leg must be genuinely anonymous, so clear them. The analyst and
    # admin legs authenticate via explicit Bearer headers.
    client.cookies.clear()

    anon = await client.request(method, path)
    assert anon.status_code == anon_expected, f"anon {method} {path}: {anon.text[:120]}"

    as_analyst = await client.request(method, path, headers=analyst_headers)
    assert (
        as_analyst.status_code == analyst_expected
    ), f"analyst {method} {path}: {as_analyst.text[:120]}"

    as_admin = await client.request(method, path, headers=admin_headers)
    assert (
        as_admin.status_code == admin_expected
    ), f"admin {method} {path}: {as_admin.text[:120]}"


async def test_analyst_cannot_refresh_ai_models(client, analyst_headers):
    """Regression: the refresh endpoint lost its admin check once."""
    response = await client.post("/api/v1/ai/models/refresh", headers=analyst_headers)
    assert response.status_code == 403


async def test_analyst_cannot_delete_asset(client, analyst_headers, admin_headers):
    response = await client.post(
        "/api/v1/assets",
        headers=admin_headers,
        json={"hostname": "rbac-del-probe", "ip": "10.8.8.8", "criticality": "low"},
    )
    assert response.status_code == 201, response.text
    asset_id = response.json()["id"]

    denied = await client.delete(f"/api/v1/assets/{asset_id}", headers=analyst_headers)
    assert denied.status_code == 403

    cleanup = await client.delete(f"/api/v1/assets/{asset_id}", headers=admin_headers)
    assert cleanup.status_code == 204
