"""Integration tests for the cases API write path.

Regression coverage for the acceptance findings: case creation used to 500
(MissingGreenlet on lazily loaded relations in _to_detail) and every write
silently rolled back because the service never committed the session.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import TEST_PASSWORD

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest_asyncio.fixture
async def case_client(client):
    """Authenticate the shared client as admin for case operations."""
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


async def _create_case(
    client: AsyncClient, title: str = "acceptance-case", **overrides
) -> dict:
    payload = {
        "title": title,
        "description": "Regression case created by tests/test_cases_api.py",
        "severity": "medium",
        "status": "new",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/cases", json=payload)
    assert response.status_code in (200, 201), response.text
    return response.json()


async def test_create_case_persists_and_reads_back(case_client: AsyncClient):
    """A created case must be readable in a fresh request (no phantom create)."""
    created = await _create_case(case_client, title="acceptance-create-read")
    case_id = created["id"]

    read_back = await case_client.get(f"/api/v1/cases/{case_id}")
    assert read_back.status_code == 200, read_back.text
    body = read_back.json()
    assert body["id"] == case_id
    assert body["title"] == "acceptance-create-read"
    assert body["status"] == "new"
    # The initial timeline entry must have been persisted too.
    assert any(
        e["entry_type"] == "status_change" for e in body.get("timeline_entries", [])
    )

    await case_client.delete(f"/api/v1/cases/{case_id}")


async def test_create_case_handles_unicode_and_long_input(case_client: AsyncClient):
    """Emoji/CJK titles and long descriptions must round-trip intact."""
    long_description = "检测引擎误报分析 - " + "x" * 5000
    created = await _create_case(
        case_client,
        title="验收用例 🔥 中文标题",
        description=long_description,
    )
    case_id = created["id"]

    read_back = await case_client.get(f"/api/v1/cases/{case_id}")
    assert read_back.status_code == 200
    body = read_back.json()
    assert body["title"] == "验收用例 🔥 中文标题"
    assert body["description"] == long_description

    await case_client.delete(f"/api/v1/cases/{case_id}")


async def test_update_case_persists(case_client: AsyncClient):
    """An updated case must reflect the change on a fresh read."""
    created = await _create_case(case_client, title="acceptance-update")
    case_id = created["id"]

    response = await case_client.put(
        f"/api/v1/cases/{case_id}", json={"severity": "high"}
    )
    assert response.status_code == 200, response.text

    read_back = await case_client.get(f"/api/v1/cases/{case_id}")
    assert read_back.status_code == 200
    assert read_back.json()["severity"] == "high"

    await case_client.delete(f"/api/v1/cases/{case_id}")


async def test_delete_case_removes_it(case_client: AsyncClient):
    """A deleted case must disappear for fresh readers (no phantom delete)."""
    created = await _create_case(case_client, title="acceptance-delete")
    case_id = created["id"]

    response = await case_client.delete(f"/api/v1/cases/{case_id}")
    assert response.status_code in (200, 204), response.text

    read_back = await case_client.get(f"/api/v1/cases/{case_id}")
    assert read_back.status_code == 404


async def test_create_case_requires_auth(client: AsyncClient):
    """Unauthenticated creation must be rejected."""
    response = await client.post(
        "/api/v1/cases",
        json={"title": "anon", "severity": "low", "status": "new"},
    )
    assert response.status_code in (401, 403)


async def test_create_case_with_alert_ids(case_client: AsyncClient):
    """Creating a case with alert_ids links the alert and records timeline."""
    from db.session import AsyncSessionLocal
    from models.security_alert import SecurityAlert

    alert_id = None
    async with AsyncSessionLocal() as session:
        alert = SecurityAlert(
            source="test_source",
            external_event_id="evt_test_case_123",
            event_type="test_event",
            title="Alert for case test",
            severity="high",
            status="new",
        )
        session.add(alert)
        await session.commit()
        alert_id = alert.id

    assert alert_id is not None

    created = await _create_case(
        case_client,
        title="case-with-alert",
        alert_ids=[str(alert_id)],
    )
    case_id = created["id"]
    assert "id" in created
    assert created["title"] == "case-with-alert"

    # Read back case and check alert is linked
    read_back = await case_client.get(f"/api/v1/cases/{case_id}")
    assert read_back.status_code == 200
    body = read_back.json()
    assert body["title"] == "case-with-alert"
    assert any(a["id"] == alert_id for a in body.get("alerts", []))

    # Verify alert lifecycle includes related_cases
    lifecycle_resp = await case_client.get(f"/api/v1/alerts/{alert_id}/lifecycle")
    assert lifecycle_resp.status_code == 200
    lifecycle_data = lifecycle_resp.json()
    assert "related_cases" in lifecycle_data
    assert any(c["id"] == case_id for c in lifecycle_data["related_cases"])

    await case_client.delete(f"/api/v1/cases/{case_id}")

    # Clean up alert
    async with AsyncSessionLocal() as session:
        a = await session.get(SecurityAlert, alert_id)
        if a:
            await session.delete(a)
            await session.commit()


async def test_create_case_with_integer_alert_ids(case_client: AsyncClient):
    """Creating a case with integer alert_ids (e.g. [1]) must succeed without 422 error."""
    from db.session import AsyncSessionLocal
    from models.security_alert import SecurityAlert

    alert_id = None
    async with AsyncSessionLocal() as session:
        alert = SecurityAlert(
            source="test_source_int",
            external_event_id="evt_test_case_int_123",
            event_type="test_event",
            title="Alert for int case test",
            severity="medium",
            status="new",
        )
        session.add(alert)
        await session.commit()
        alert_id = alert.id

    assert alert_id is not None

    created = await _create_case(
        case_client,
        title="case-with-int-alert",
        alert_ids=[alert_id],
    )
    case_id = created["id"]
    assert "id" in created
    assert created["title"] == "case-with-int-alert"

    # Read back case and check alert is linked
    read_back = await case_client.get(f"/api/v1/cases/{case_id}")
    assert read_back.status_code == 200
    body = read_back.json()
    assert any(a["id"] == alert_id for a in body.get("alerts", []))

    await case_client.delete(f"/api/v1/cases/{case_id}")

    # Clean up alert
    async with AsyncSessionLocal() as session:
        a = await session.get(SecurityAlert, alert_id)
        if a:
            await session.delete(a)
            await session.commit()

