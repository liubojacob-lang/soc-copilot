"""
SOC Copilot Test Suite - Core Functionality Tests
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any


# Core tests
class TestHealthCheck:
    """API health check tests."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "status" in data


class TestAuthentication:
    """Authentication and authorization tests."""

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Test successful login."""
        response = await client.post(
            "/api/auth/login", json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data

    @pytest.mark.asyncio
    async def test_login_failure(self, client):
        """Test failed login."""
        response = await client.post(
            "/api/auth/login", json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = await client.get("/api/alerts")
        assert response.status_code == 401


class TestPlaybookDefinitions:
    """Playbook definition CRUD tests."""

    @pytest.mark.asyncio
    async def test_create_definition(self, auth_client):
        """Test creating playbook definition."""
        definition_data = {
            "name": "Test Playbook",
            "version": "1.0.0",
            "description": "Test description",
            "dag": {
                "nodes": [
                    {
                        "id": "start",
                        "type": "start",
                        "name": "Start",
                        "description": "Start node",
                    },
                    {
                        "id": "end",
                        "type": "end",
                        "name": "End",
                        "description": "End node",
                    },
                ],
                "edges": [{"source": "start", "target": "end"}],
            },
        }
        response = await auth_client.post(
            "/api/playbook-definitions", json=definition_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Playbook"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_definitions(self, auth_client):
        """Test listing playbook definitions."""
        response = await auth_client.get("/api/playbook-definitions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_definition(self, auth_client, sample_definition):
        """Test getting single definition."""
        response = await auth_client.get(
            f"/api/playbook-definitions/{sample_definition['id']}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_definition["id"]


class TestAlerts:
    """Alert management tests."""

    @pytest.mark.asyncio
    async def test_list_alerts(self, auth_client):
        """Test listing alerts."""
        response = await auth_client.get("/api/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_alert(self, auth_client):
        """Test creating alert."""
        alert_data = {
            "title": "Test Alert",
            "description": "Test alert description",
            "severity": "high",
            "source": "test",
            "alert_type": "security",
        }
        response = await auth_client.post("/api/alerts", json=alert_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Alert"


class TestSettings:
    """Settings management tests."""

    @pytest.mark.asyncio
    async def test_get_settings(self, admin_client):
        """Test getting settings (admin only)."""
        response = await admin_client.get("/api/admin/settings")
        assert response.status_code == 200
        data = response.json()
        assert "dify_api_url" in data
        assert "dify_configured" in data

    @pytest.mark.asyncio
    async def test_update_settings(self, admin_client):
        """Test updating settings."""
        settings_data = {
            "dify_api_url": "http://test.example.com",
            "dify_api_key": "test-api-key",
        }
        response = await admin_client.post("/api/admin/settings", json=settings_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestAssets:
    """Asset management tests."""

    @pytest.mark.asyncio
    async def test_list_assets(self, auth_client):
        """Test listing assets."""
        response = await auth_client.get("/api/assets")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestThreatIntel:
    """Threat intelligence tests."""

    @pytest.mark.asyncio
    async def test_lookup_ioc(self, auth_client):
        """Test IOC lookup."""
        response = await auth_client.get("/api/threat-intel/lookup?ioc=8.8.8.8&type=ip")
        assert response.status_code in [200, 404]  # 404 if not found

    @pytest.mark.asyncio
    async def test_batch_lookup(self, auth_client):
        """Test batch IOC lookup."""
        iocs = ["8.8.8.8", "1.1.1.1"]
        response = await auth_client.post(
            "/api/threat-intel/batch", json={"iocs": iocs}
        )
        assert response.status_code == 200


# Utility functions
@pytest.fixture
def sample_dag():
    """Sample DAG for testing."""
    return {
        "nodes": [
            {"id": "start", "type": "start", "name": "Start"},
            {"id": "http", "type": "http_request", "name": "HTTP Request"},
            {"id": "end", "type": "end", "name": "End"},
        ],
        "edges": [
            {"source": "start", "target": "http"},
            {"source": "http", "target": "end"},
        ],
    }


@pytest.fixture
def sample_definition():
    """Sample playbook definition."""
    return {
        "id": "test-definition-id",
        "name": "Test Playbook",
        "version": "1.0.0",
        "description": "Test playbook",
    }
