"""
Test fixtures and configuration
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from asgi_lifespan import LifespanManager

from main import app


@pytest_asyncio.fixture(scope="session")
async def client():
    """Async HTTP client for testing."""
    async with LifespanManager(app):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac


@pytest_asyncio.fixture
async def auth_client(client):
    """Authenticated client for testing."""
    # Login to get token
    response = await client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin123"}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
    yield client
    # Cleanup
    if "Authorization" in client.headers:
        del client.headers["Authorization"]


@pytest_asyncio.fixture
async def admin_client(client):
    """Admin authenticated client."""
    # Login as admin
    response = await client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin123"}
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        client.headers["Authorization"] = f"Bearer {token}"
    yield client
    # Cleanup
    if "Authorization" in client.headers:
        del client.headers["Authorization"]


@pytest.fixture
def sample_playbook_data():
    """Sample playbook data for tests."""
    return {
        "name": "Test Playbook",
        "version": "1.0.0",
        "description": "A test playbook",
        "dag": {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "Start",
                    "description": "Start node",
                },
                {
                    "id": "http",
                    "type": "http_request",
                    "name": "HTTP Request",
                    "config": {"method": "GET", "url": "https://api.example.com/test"},
                },
                {"id": "end", "type": "end", "name": "End", "description": "End node"},
            ],
            "edges": [
                {"source": "start", "target": "http"},
                {"source": "http", "target": "end"},
            ],
        },
    }


@pytest.fixture
def sample_alert_data():
    """Sample alert data for tests."""
    return {
        "title": "Test Security Alert",
        "description": "Suspicious activity detected",
        "severity": "high",
        "source": "test_system",
        "alert_type": "security",
        "metadata": {"ip": "192.168.1.1", "port": 443},
    }


@pytest.fixture
def sample_asset_data():
    """Sample asset data for tests."""
    return {
        "name": "Test Server",
        "asset_type": "server",
        "ip_address": "192.168.1.100",
        "mac_address": "00:11:22:33:44:55",
        "os": "Ubuntu 22.04",
        "status": "active",
        "risk_level": "medium",
    }
