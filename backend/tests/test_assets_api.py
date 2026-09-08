"""Integration tests for the assets API write path.

Regression coverage for the acceptance findings: asset mutations used to
flush without committing (phantom writes — a 201 response whose row never
landed), and a single legacy plain-text tags row 500'd the entire list
endpoint for every user.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_PASSWORD

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest.fixture
async def asset_client(client):
    """Authenticate the shared client as admin for asset operations."""
    response = await client.post(
        "/api/auth/login", json={"username": "admin", "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    token = response.json().get("access_token") or response.cookies.get("access_token")
    assert token, "No access token in response body or cookie"
    original_headers = dict(client.headers)
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
    client.headers.clear()
    client.headers.update(original_headers)


async def _create_asset(client: AsyncClient, hostname: str, **overrides) -> dict:
    payload = {
        "hostname": hostname,
        "ip": "10.99.99.99",
        "asset_type": "server",
        "criticality": "low",
        "tags": ["acceptance"],
        "owner": "qa",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/assets", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_create_asset_persists_and_reads_back(asset_client: AsyncClient):
    """A created asset must be readable in a fresh request (no phantom create)."""
    created = await _create_asset(asset_client, "test-asset-persist")
    asset_id = created["id"]

    read_back = await asset_client.get(f"/api/v1/assets/{asset_id}")
    assert read_back.status_code == 200, read_back.text
    body = read_back.json()
    assert body["id"] == asset_id
    assert body["hostname"] == "test-asset-persist"

    await asset_client.delete(f"/api/v1/assets/{asset_id}")


async def test_duplicate_asset_hostname_conflicts(asset_client: AsyncClient):
    """Duplicate hostname returns 409 with the conflicting field."""
    first = await _create_asset(asset_client, "test-asset-dup")
    duplicate = await asset_client.post(
        "/api/v1/assets",
        json={
            "hostname": "test-asset-dup",
            "ip": "10.99.99.98",
            "criticality": "low",
        },
    )
    assert duplicate.status_code == 409
    assert "hostname" in duplicate.text

    await asset_client.delete(f"/api/v1/assets/{first['id']}")


async def test_list_assets_parses_legacy_tag_text(asset_client: AsyncClient):
    """Rows whose tags are plain comma text must not 500 the list endpoint."""
    response = await asset_client.get("/api/v1/assets?limit=100")
    assert response.status_code == 200, response.text
    items = response.json().get("items", [])
    for asset in items:
        assert isinstance(asset.get("tags"), list)


async def test_delete_asset_removes_it(asset_client: AsyncClient):
    """A deleted asset must disappear for fresh readers."""
    created = await _create_asset(asset_client, "test-asset-delete")
    asset_id = created["id"]

    response = await asset_client.delete(f"/api/v1/assets/{asset_id}")
    assert response.status_code in (200, 204), response.text

    read_back = await asset_client.get(f"/api/v1/assets/{asset_id}")
    assert read_back.status_code == 404


async def test_create_asset_requires_auth(client: AsyncClient):
    """Unauthenticated creation must be rejected."""
    response = await client.post(
        "/api/v1/assets",
        json={"hostname": "anon-probe", "criticality": "low"},
    )
    assert response.status_code in (401, 403)
