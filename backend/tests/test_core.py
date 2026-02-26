"""SOC Copilot core API tests aligned with current router contracts."""

import pytest


class TestHealthCheck:
    """API health check tests."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ("ok", "healthy")


class TestAuthentication:
    """Authentication and authorization tests."""

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        response = await client.post(
            "/api/auth/login", json={"username": "admin", "password": "admin123!"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data

    @pytest.mark.asyncio
    async def test_login_failure(self, client):
        response = await client.post(
            "/api/auth/login", json={"username": "admin", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_protected_endpoint_without_token(self, client):
        response = await client.get("/api/auth/me")
        assert response.status_code == 401


class TestPlaybookDefinitions:
    """Playbook definition CRUD tests."""

    @staticmethod
    def _valid_dag():
        return {
            "nodes": [
                {"id": "n1", "type": "normalize", "name": "Normalize"},
                {"id": "n2", "type": "generate_report", "name": "Generate Report"},
            ],
            "edges": [{"source": "n1", "target": "n2"}],
        }

    @pytest.mark.asyncio
    async def test_create_definition(self, auth_client):
        response = await auth_client.post(
            "/api/playbook-definitions",
            json={
                "name": "Test Playbook",
                "version": "1.0.0",
                "description": "Test description",
                "dag": self._valid_dag(),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Playbook"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_definitions(self, auth_client):
        response = await auth_client.get("/api/playbook-definitions")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    @pytest.mark.asyncio
    async def test_get_definition(self, auth_client):
        create_resp = await auth_client.post(
            "/api/playbook-definitions",
            json={
                "name": "Get Definition Target",
                "version": "1.0.1",
                "description": "Test get definition",
                "dag": self._valid_dag(),
            },
        )
        assert create_resp.status_code == 201
        definition_id = create_resp.json()["id"]

        get_resp = await auth_client.get(f"/api/playbook-definitions/{definition_id}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == definition_id


class TestSettings:
    """Settings management tests."""

    @pytest.mark.asyncio
    async def test_get_settings(self, admin_client):
        response = await admin_client.get("/api/admin/settings")
        assert response.status_code == 200
        data = response.json()
        assert "dify_api_url" in data
        assert "dify_configured" in data


class TestAssets:
    """Asset management tests."""

    @pytest.mark.asyncio
    async def test_list_assets(self, auth_client):
        response = await auth_client.get("/api/assets")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data


class TestThreatIntel:
    """Threat intelligence API tests."""

    @pytest.mark.asyncio
    async def test_lookup_ioc(self, auth_client):
        response = await auth_client.get("/api/ti/otx?ioc_type=ip&ioc_value=8.8.8.8")
        assert response.status_code == 200
        data = response.json()
        assert data["ioc_type"] == "ip"
        assert data["ioc_value"] == "8.8.8.8"
        assert "verdict" in data

    @pytest.mark.asyncio
    async def test_batch_lookup(self, auth_client):
        response = await auth_client.post(
            "/api/ti/otx/bulk",
            json={
                "items": [
                    {"ioc_type": "ip", "ioc_value": "8.8.8.8"},
                    {"ioc_type": "domain", "ioc_value": "example.com"},
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)
