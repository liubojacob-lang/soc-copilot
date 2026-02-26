"""Integration tests for event correlation system.

Tests complete flow from raw events to correlated incidents:
- Raw event ingestion
- API endpoint calls
- Database persistence
- Correlation generation
- Status updates
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from main import app
from models.correlation_rule import CorrelationRule
from models.correlated_event import CorrelatedEvent
from db.session import get_session


# Test fixtures
@pytest.fixture
async def db_session():
    """Create test database session."""
    async for session in get_session():
        yield session
        break


@pytest.fixture
async def test_client():
    """Create test HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


# Test data
SAMPLE_EVENTS = [
    {
        "id": "alert-001",
        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat(),
        "source_ip": "192.168.1.100",
        "username": "admin",
        "hostname": "server01",
        "severity": "high",
        "category": "authentication",
        "message": "Login failed for user admin"
    },
    {
        "id": "alert-002",
        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=8)).isoformat(),
        "source_ip": "192.168.1.100",
        "username": "admin",
        "hostname": "server01",
        "severity": "high",
        "category": "authentication",
        "message": "Login failed for user admin"
    },
    {
        "id": "alert-003",
        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=6)).isoformat(),
        "source_ip": "192.168.1.100",
        "username": "admin",
        "hostname": "server01",
        "severity": "high",
        "category": "authentication",
        "message": "Login failed for user admin"
    },
    {
        "id": "alert-004",
        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        "source_ip": "192.168.1.100",
        "username": "admin",
        "hostname": "server01",
        "severity": "high",
        "category": "authentication",
        "message": "Login failed for user admin"
    },
    {
        "id": "alert-005",
        "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat(),
        "source_ip": "192.168.1.100",
        "username": "admin",
        "hostname": "server01",
        "severity": "high",
        "category": "authentication",
        "message": "Login failed for user admin"
    }
]


class TestCorrelationAPI:
    """Test correlation API endpoints."""

    @pytest.mark.asyncio
    async def test_correlate_events_endpoint(self, test_client: AsyncClient):
        """Test POST /api/correlation/correlate endpoint."""
        response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": SAMPLE_EVENTS}
        )

        assert response.status_code == 200
        data = response.json()

        # API returns a list of CorrelatedEventResponse
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_incidents_empty(self, test_client: AsyncClient):
        """Test GET /api/correlation/incidents with no data."""
        response = await test_client.get("/api/correlation/incidents")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_incidents_after_correlation(
        self,
        test_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test GET /api/correlation/incidents after correlation."""
        # First correlate events
        correlate_response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": SAMPLE_EVENTS}
        )

        # Then fetch incidents
        response = await test_client.get("/api/correlation/incidents?limit=10")

        assert response.status_code == 200
        incidents = response.json()
        assert isinstance(incidents, list)

        if len(incidents) > 0:
            # Verify incident structure
            incident = incidents[0]
            assert "id" in incident
            assert "title" in incident
            assert "severity" in incident
            assert "confidence_score" in incident
            assert "raw_event_count" in incident
            assert "common_entities" in incident

    @pytest.mark.asyncio
    async def test_get_incident_by_id(
        self,
        test_client: AsyncClient
    ):
        """Test GET /api/correlation/incidents/{id} endpoint."""
        # Correlate events first
        correlate_response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": SAMPLE_EVENTS}
        )
        correlated_events = correlate_response.json()

        if isinstance(correlated_events, list) and len(correlated_events) > 0:
            incident_id = correlated_events[0]["id"]

            # Fetch specific incident
            response = await test_client.get(f"/api/correlation/incidents/{incident_id}")

            assert response.status_code == 200
            incident = response.json()
            assert incident["id"] == incident_id
            assert "title" in incident
            assert "description" in incident

    @pytest.mark.asyncio
    async def test_update_incident_status(
        self,
        test_client: AsyncClient
    ):
        """Test PUT /api/correlation/incidents/{id}/status endpoint."""
        # Correlate events first
        correlate_response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": SAMPLE_EVENTS}
        )
        correlated_events = correlate_response.json()

        if isinstance(correlated_events, list) and len(correlated_events) > 0:
            incident_id = correlated_events[0]["id"]

            # Update status
            response = await test_client.put(
                f"/api/correlation/incidents/{incident_id}/status",
                params={"status": "investigating", "assigned_to": "analyst1"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "investigating"
            assert data["assigned_to"] == "analyst1"

    @pytest.mark.asyncio
    async def test_get_correlation_stats(self, test_client: AsyncClient):
        """Test GET /api/correlation/stats endpoint."""
        # Correlate events first
        await test_client.post(
            "/api/correlation/correlate",
            json={"events": SAMPLE_EVENTS}
        )

        # Get stats
        response = await test_client.get("/api/correlation/stats")

        assert response.status_code == 200
        stats = response.json()
        # Stats endpoint returns statistics, validate structure
        assert isinstance(stats, dict)

    @pytest.mark.asyncio
    async def test_get_correlation_rules(self, test_client: AsyncClient):
        """Test GET /api/correlation/rules endpoint."""
        response = await test_client.get("/api/correlation/rules")

        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "count" in data
        assert data["count"] > 0  # Should have built-in rules

    @pytest.mark.asyncio
    async def test_create_custom_rule(self, test_client: AsyncClient):
        """Test POST /api/correlation/rules endpoint."""
        new_rule = {
            "name": "Test Custom Rule",
            "description": "Integration test rule",
            "time_window_seconds": 300,
            "entity_types": {"ip_address": True, "username": False},
            "min_similarity": 0.7,
            "action": "aggregate",
            "priority": 75
        }

        response = await test_client.post("/api/correlation/rules", json=new_rule)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "rule_id" in data
        assert data["rule"]["name"] == "Test Custom Rule"
        assert data["rule"]["priority"] == 75

    @pytest.mark.asyncio
    async def test_update_rule(self, test_client: AsyncClient):
        """Test PUT /api/correlation/rules/{id} endpoint."""
        # Create a rule first
        create_response = await test_client.post(
            "/api/correlation/rules",
            json={
                "name": "Rule to Update",
                "time_window_seconds": 300,
                "entity_types": {"ip_address": True},
                "action": "aggregate",
                "priority": 70
            }
        )
        create_data = create_response.json()
        rule_id = create_data["rule_id"]

        # Update the rule
        update_data = {"priority": 85, "enabled": False}
        response = await test_client.put(
            f"/api/correlation/rules/{rule_id}",
            json=update_data
        )

        assert response.status_code == 200
        updated_data = response.json()
        assert updated_data["success"] is True
        assert updated_data["rule_id"] == rule_id
        assert "priority" in updated_data["updated_fields"]

    @pytest.mark.asyncio
    async def test_delete_rule(self, test_client: AsyncClient):
        """Test DELETE /api/correlation/rules/{id} endpoint."""
        # Create a rule first
        create_response = await test_client.post(
            "/api/correlation/rules",
            json={
                "name": "Rule to Delete",
                "time_window_seconds": 300,
                "entity_types": {"ip_address": True},
                "action": "aggregate",
                "priority": 70
            }
        )
        create_data = create_response.json()
        rule_id = create_data["rule_id"]

        # Delete the rule
        response = await test_client.delete(f"/api/correlation/rules/{rule_id}")

        assert response.status_code == 200

        # Verify it's deleted
        get_response = await test_client.get("/api/correlation/rules")
        get_data = get_response.json()
        rule_ids = [r["id"] for r in get_data["rules"]]
        assert rule_id not in rule_ids


class TestDatabasePersistence:
    """Test database persistence of correlated events."""

    @pytest.mark.asyncio
    async def test_correlated_event_persistence(
        self,
        test_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that correlated events are persisted correctly."""
        # Correlate events
        await test_client.post(
            "/api/correlation/correlate",
            json={"events": SAMPLE_EVENTS}
        )

        # Query database directly
        result = await db_session.execute(
            select(CorrelatedEvent).limit(1)
        )
        incident = result.scalar_one_or_none()

        assert incident is not None
        assert incident.id is not None
        assert incident.raw_event_count > 0
        assert incident.common_entities is not None
        assert incident.created_at is not None

    @pytest.mark.asyncio
    async def test_rule_persistence(
        self,
        test_client: AsyncClient,
        db_session: AsyncSession
    ):
        """Test that custom rules are persisted correctly."""
        # Create rule via API
        response = await test_client.post(
            "/api/correlation/rules",
            json={
                "name": "Persistence Test Rule",
                "time_window_seconds": 600,
                "entity_types": {"ip_address": True},
                "action": "aggregate",
                "priority": 80
            }
        )

        rule_data = response.json()
        rule_id = rule_data["rule_id"]

        # Query database directly
        result = await db_session.execute(
            select(CorrelationRule).where(CorrelationRule.id == rule_id)
        )
        rule = result.scalar_one()

        assert rule.name == "Persistence Test Rule"
        assert rule.time_window_seconds == 600
        assert rule.priority == 80


class TestEndToEndFlow:
    """Test complete end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_complete_correlation_workflow(self, test_client: AsyncClient):
        """Test full workflow from events to status update."""
        # Step 1: Correlate events
        correlate_response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": SAMPLE_EVENTS}
        )
        assert correlate_response.status_code == 200
        correlated_events = correlate_response.json()

        # Step 2: Get incidents
        incidents_response = await test_client.get("/api/correlation/incidents")
        assert incidents_response.status_code == 200
        incidents = incidents_response.json()

        if len(incidents) > 0:
            # Step 3: Get specific incident
            incident_id = incidents[0]["id"]
            incident_response = await test_client.get(
                f"/api/correlation/incidents/{incident_id}"
            )
            assert incident_response.status_code == 200
            incident = incident_response.json()
            assert incident["id"] == incident_id

            # Step 4: Update status
            update_response = await test_client.put(
                f"/api/correlation/incidents/{incident_id}/status",
                params={"status": "resolved", "assigned_to": "john.doe"}
            )
            assert update_response.status_code == 200
            update_data = update_response.json()
            assert update_data["status"] == "resolved"
            assert update_data["assigned_to"] == "john.doe"

            # Step 5: Verify update
            verify_response = await test_client.get(
                f"/api/correlation/incidents/{incident_id}"
            )
            verify_data = verify_response.json()
            assert verify_data["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_multiple_correlation_batches(self, test_client: AsyncClient):
        """Test correlating multiple batches of events."""
        # First batch
        batch1 = [
            {
                "id": f"batch1-{i}",
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=15-i)).isoformat(),
                "source_ip": "10.0.0.50",
                "username": "analyst",
                "severity": "medium",
                "category": "network",
                "message": f"Network event {i}"
            }
            for i in range(5)
        ]

        await test_client.post("/api/correlation/correlate", json={"events": batch1})

        # Second batch (different IP)
        batch2 = [
            {
                "id": f"batch2-{i}",
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=10-i)).isoformat(),
                "source_ip": "10.0.0.99",
                "username": "guest",
                "severity": "low",
                "category": "access",
                "message": f"Access event {i}"
            }
            for i in range(5)
        ]

        await test_client.post("/api/correlation/correlate", json={"events": batch2})

        # Verify both batches are processed
        stats_response = await test_client.get("/api/correlation/stats")
        stats = stats_response.json()
        assert stats["incidents"]["total"] >= 2


class TestErrorHandling:
    """Test error handling in API endpoints."""

    @pytest.mark.asyncio
    async def test_correlate_empty_events(self, test_client: AsyncClient):
        """Test correlating empty event list."""
        response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": []}
        )

        assert response.status_code == 200
        data = response.json()
        # Returns empty list when no events
        assert isinstance(data, list)
        assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_nonexistent_incident(self, test_client: AsyncClient):
        """Test fetching incident that doesn't exist."""
        response = await test_client.get("/api/correlation/incidents/nonexistent-id")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_nonexistent_incident(self, test_client: AsyncClient):
        """Test updating incident that doesn't exist."""
        response = await test_client.put(
            "/api/correlation/incidents/nonexistent-id/status",
            params={"status": "resolved"}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_status_update(self, test_client: AsyncClient):
        """Test updating with invalid status value."""
        # Create incident first
        correlate_response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": SAMPLE_EVENTS[:3]}
        )
        correlated_events = correlate_response.json()

        if isinstance(correlated_events, list) and len(correlated_events) > 0:
            incident_id = correlated_events[0]["id"]

            # Try invalid status
            response = await test_client.put(
                f"/api/correlation/incidents/{incident_id}/status",
                params={"status": "invalid_status"}
            )

            # Should return client error (400 or 422)
            assert response.status_code in [400, 422]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
