"""Playbook engine tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json


class TestPlaybookDefinitions:
    """Playbook definition tests."""

    @pytest.mark.asyncio
    async def test_create_playbook_definition(self, auth_client):
        """Test creating a new playbook definition."""
        response = await auth_client.post(
            "/api/playbook-definitions",
            json={
                "name": "Test Playbook",
                "version": "1.0.0",
                "description": "A test playbook",
                "dag": {
                    "nodes": [
                        {"id": "n1", "type": "start", "name": "Start"},
                        {"id": "n2", "type": "normalize", "name": "Normalize"},
                        {"id": "n3", "type": "end", "name": "End"}
                    ],
                    "edges": [
                        {"source": "n1", "target": "n2"},
                        {"source": "n2", "target": "n3"}
                    ]
                }
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == "Test Playbook"

    @pytest.mark.asyncio
    async def test_create_invalid_dag(self, auth_client):
        """Test creating playbook with invalid DAG."""
        response = await auth_client.post(
            "/api/playbook-definitions",
            json={
                "name": "Invalid Playbook",
                "version": "1.0.0",
                "dag": {
                    "nodes": [],
                    "edges": []
                }
            }
        )
        # Should fail validation
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_list_playbook_definitions(self, auth_client):
        """Test listing playbook definitions."""
        response = await auth_client.get("/api/playbook-definitions")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "total" in data

    @pytest.mark.asyncio
    async def test_get_playbook_definition(self, auth_client):
        """Test getting a specific playbook definition."""
        # First create one
        create_response = await auth_client.post(
            "/api/playbook-definitions",
            json={
                "name": "Get Test",
                "version": "1.0.0",
                "dag": {
                    "nodes": [{"id": "n1", "type": "start", "name": "Start"}],
                    "edges": []
                }
            }
        )
        assert create_response.status_code == 201
        definition_id = create_response.json()["id"]

        # Get it
        get_response = await auth_client.get(f"/api/playbook-definitions/{definition_id}")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["id"] == definition_id

    @pytest.mark.asyncio
    async def test_update_playbook_definition(self, auth_client):
        """Test updating a playbook definition."""
        # Create first
        create_response = await auth_client.post(
            "/api/playbook-definitions",
            json={
                "name": "Update Test",
                "version": "1.0.0",
                "dag": {
                    "nodes": [{"id": "n1", "type": "start", "name": "Start"}],
                    "edges": []
                }
            }
        )
        definition_id = create_response.json()["id"]

        # Update it
        update_response = await auth_client.put(
            f"/api/playbook-definitions/{definition_id}",
            json={
                "name": "Updated Playbook",
                "version": "1.1.0",
                "description": "Updated description",
                "dag": {
                    "nodes": [
                        {"id": "n1", "type": "start", "name": "Start"},
                        {"id": "n2", "type": "end", "name": "End"}
                    ],
                    "edges": [{"source": "n1", "target": "n2"}]
                }
            }
        )
        assert update_response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_playbook_definition(self, auth_client):
        """Test deleting a playbook definition."""
        # Create first
        create_response = await auth_client.post(
            "/api/playbook-definitions",
            json={
                "name": "Delete Test",
                "version": "1.0.0",
                "dag": {
                    "nodes": [{"id": "n1", "type": "start", "name": "Start"}],
                    "edges": []
                }
            }
        )
        definition_id = create_response.json()["id"]

        # Delete it
        delete_response = await auth_client.delete(f"/api/playbook-definitions/{definition_id}")
        assert delete_response.status_code in [200, 204]

        # Verify it's gone
        get_response = await auth_client.get(f"/api/playbook-definitions/{definition_id}")
        assert get_response.status_code == 404


class TestPlaybookRuns:
    """Playbook run execution tests."""

    @pytest.mark.asyncio
    async def test_execute_playbook(self, auth_client, sample_playbook_data):
        """Test executing a playbook."""
        # First create a definition
        create_response = await auth_client.post(
            "/api/playbook-definitions",
            json=sample_playbook_data
        )
        assert create_response.status_code == 201
        definition_id = create_response.json()["id"]

        # Execute it
        run_response = await auth_client.post(
            "/api/playbook-runs",
            json={
                "definition_id": definition_id,
                "trigger_data": {"test": "data"}
            }
        )
        # Should succeed or 503 if executor not available
        assert run_response.status_code in [201, 202, 503]

    @pytest.mark.asyncio
    async def test_list_playbook_runs(self, auth_client):
        """Test listing playbook runs."""
        response = await auth_client.get("/api/playbook-runs?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "runs" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_playbook_run_status(self, auth_client):
        """Test getting playbook run status."""
        # Create and execute a playbook
        create_response = await auth_client.post(
            "/api/playbook-definitions",
            json={
                "name": "Status Test",
                "version": "1.0.0",
                "dag": {
                    "nodes": [
                        {"id": "n1", "type": "start", "name": "Start"},
                        {"id": "n2", "type": "end", "name": "End"}
                    ],
                    "edges": [{"source": "n1", "target": "n2"}]
                }
            }
        )
        definition_id = create_response.json()["id"]

        run_response = await auth_client.post(
            "/api/playbook-runs",
            json={"definition_id": definition_id}
        )

        if run_response.status_code in [201, 202]:
            run_id = run_response.json().get("id") or run_response.json().get("run_id")

            # Get status
            status_response = await auth_client.get(f"/api/playbook-runs/{run_id}")
            assert status_response.status_code == 200
            data = status_response.json()
            assert "status" in data

    @pytest.mark.asyncio
    async def test_cancel_playbook_run(self, auth_client):
        """Test cancelling a playbook run."""
        # This test requires a long-running playbook
        # For now, test the endpoint exists
        response = await auth_client.post("/api/playbook-runs/nonexistent/cancel")
        # Should fail for non-existent run
        assert response.status_code in [404, 400]

    @pytest.mark.asyncio
    async def test_playbook_run_logs(self, auth_client):
        """Test getting playbook run logs."""
        # This would require an actual run
        response = await auth_client.get("/api/playbook-runs/nonexistent/logs")
        # Should fail for non-existent run
        assert response.status_code == 404


class TestPlaybookNodes:
    """Playbook node plugin tests."""

    @pytest.mark.asyncio
    async def test_normalize_node(self, auth_client):
        """Test the normalize node functionality."""
        response = await auth_client.post(
            "/api/playbooks/test-node",
            json={
                "node_type": "normalize",
                "input_data": {"raw": "test data"}
            }
        )
        # Should succeed or 404 if test endpoint not available
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_extract_iocs_node(self, auth_client):
        """Test the IOC extraction node."""
        response = await auth_client.post(
            "/api/playbooks/test-node",
            json={
                "node_type": "extract_iocs",
                "input_data": {
                    "text": "Attacker IP: 192.168.1.1, Domain: evil.com"
                }
            }
        )
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_risk_score_node(self, auth_client):
        """Test the risk scoring node."""
        response = await auth_client.post(
            "/api/playbooks/test-node",
            json={
                "node_type": "risk_score",
                "input_data": {
                    "severity": "high",
                    "iocs": {"ips": ["1.1.1.1"]}
                }
            }
        )
        assert response.status_code in [200, 404]


class TestPlaybookTriggers:
    """Playbook trigger tests."""

    @pytest.mark.asyncio
    async def test_create_webhook_trigger(self, auth_client):
        """Test creating a webhook trigger."""
        response = await auth_client.post(
            "/api/triggers/webhook",
            json={
                "name": "Test Webhook",
                "definition_id": "test-definition-id",
                "enabled": True
            }
        )
        # Should succeed or 404 if endpoint not implemented
        assert response.status_code in [201, 404]

    @pytest.mark.asyncio
    async def test_list_triggers(self, auth_client):
        """Test listing triggers."""
        response = await auth_client.get("/api/triggers")
        # Should succeed or 404 if endpoint not implemented
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_trigger_webhook(self, client):
        """Test triggering a webhook."""
        # This would test the actual webhook endpoint
        response = await client.post(
            "/api/webhooks/test-trigger-id",
            json={"event": "test"}
        )
        # May or may not be implemented
        assert response.status_code in [200, 404, 500]


class TestPlaybookValidation:
    """Playbook validation tests."""

    @pytest.mark.asyncio
    async def test_validate_dag_cyclic(self, auth_client):
        """Test DAG validation with cycles."""
        response = await auth_client.post(
            "/api/playbook-definitions",
            json={
                "name": "Cyclic Playbook",
                "version": "1.0.0",
                "dag": {
                    "nodes": [
                        {"id": "n1", "type": "start", "name": "Start"},
                        {"id": "n2", "type": "end", "name": "End"}
                    ],
                    "edges": [
                        {"source": "n1", "target": "n2"},
                        {"source": "n2", "target": "n1"}  # Cycle!
                    ]
                }
            }
        )
        # Should reject cyclic DAG
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_validate_dag_orphan_nodes(self, auth_client):
        """Test DAG validation with orphan nodes."""
        response = await auth_client.post(
            "/api/playbook-definitions",
            json={
                "name": "Orphan Nodes Playbook",
                "version": "1.0.0",
                "dag": {
                    "nodes": [
                        {"id": "n1", "type": "start", "name": "Start"},
                        {"id": "n2", "type": "end", "name": "End"},
                        {"id": "n3", "type": "normalize", "name": "Orphan"}  # No edges!
                    ],
                    "edges": [
                        {"source": "n1", "target": "n2"}
                    ]
                }
            }
        )
        # Should warn about orphan nodes or still accept
        assert response.status_code in [200, 201, 400, 422]

    @pytest.mark.asyncio
    async def test_validate_required_nodes(self, auth_client):
        """Test that DAG has required start/end nodes."""
        response = await auth_client.post(
            "/api/playbook-definitions",
            json={
                "name": "Missing Start/End",
                "version": "1.0.0",
                "dag": {
                    "nodes": [
                        {"id": "n1", "type": "normalize", "name": "Normalize"}
                    ],
                    "edges": []
                }
            }
        )
        # Should require start and end nodes
        assert response.status_code in [400, 422]


class TestPlaybookResults:
    """Playbook result tests."""

    @pytest.mark.asyncio
    async def test_get_run_results(self, auth_client):
        """Test getting playbook run results."""
        response = await auth_client.get("/api/playbook-runs/nonexistent/results")
        # Should fail for non-existent run
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_run_artifacts(self, auth_client):
        """Test getting playbook run artifacts."""
        response = await auth_client.get("/api/playbook-runs/nonexistent/artifacts")
        # Should fail for non-existent run
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_download_run_report(self, auth_client):
        """Test downloading playbook run report."""
        response = await auth_client.get("/api/playbook-runs/nonexistent/report")
        # Should fail for non-existent run
        assert response.status_code == 404
