"""
Test fixtures and configuration
"""

import os

# Set environment variables BEFORE any other imports
# This must be done at module level before any imports from the project
os.environ["ENVIRONMENT"] = "test"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "admin123!TestPass"
os.environ["JWT_SECRET"] = "test-jwt-secret-min-32-characters-long-for-testing"
os.environ["SECRET_KEY"] = "test-secret-key-min-32-characters-long-for-testing-purposes"
os.environ["DB_PASSWORD"] = "test-db-password-min-32-characters"

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from main import app

# Test password constant
TEST_PASSWORD = "admin123!TestPass"


def pytest_configure(config):
    """Configure pytest with environment variables."""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "admin123!TestPass"
    os.environ["JWT_SECRET"] = "test-jwt-secret-min-32-characters-long-for-testing"
    os.environ["SECRET_KEY"] = "test-secret-key-min-32-characters-long-for-testing-purposes"
    os.environ["DB_PASSWORD"] = "test-db-password-min-32-characters"


@pytest_asyncio.fixture(scope="session")
async def client():
    """Async HTTP client for testing."""
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest_asyncio.fixture
async def auth_client(client):
    """Authenticated client for testing - uses session-scoped client with fresh token."""
    # Login to get a fresh token
    response = await client.post(
        "/api/auth/login", json={"username": "admin", "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]

    # Store original headers
    original_headers = dict(client.headers)

    # Set auth header
    client.headers["Authorization"] = f"Bearer {token}"

    yield client

    # Restore original headers
    client.headers.clear()
    client.headers.update(original_headers)


@pytest_asyncio.fixture
async def admin_client(client):
    """Admin authenticated client - uses session-scoped client with fresh token."""
    # Login as admin to get a fresh token
    response = await client.post(
        "/api/auth/login", json={"username": "admin", "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]

    # Store original headers
    original_headers = dict(client.headers)

    # Set auth header
    client.headers["Authorization"] = f"Bearer {token}"

    yield client

    # Restore original headers
    client.headers.clear()
    client.headers.update(original_headers)


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
