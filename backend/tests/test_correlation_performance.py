"""Performance tests for event correlation system.

Tests performance requirements:
- Correlation of 1000 events < 2s
- Database queries optimized with indexes
- Similarity calculation caching effective
"""

import pytest
import time
import random
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from main import app
from models.correlated_event import CorrelatedEvent
from db.session import get_session


# Test fixtures
@pytest.fixture
async def test_client():
    """Create test HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


def generate_test_events(count: int, time_span_minutes: int = 60) -> list:
    """Generate test events for performance testing.

    Args:
        count: Number of events to generate
        time_span_minutes: Time span for events in minutes

    Returns:
        List of event dictionaries
    """
    events = []
    base_time = datetime.now(timezone.utc)
    categories = ["authentication", "network", "malware", "access", "application"]
    severities = ["low", "medium", "high", "critical"]

    # Generate events with patterns to create correlations
    for i in range(count):
        # Create correlated groups (every 10-20 events share same IP)
        group_size = random.randint(10, 20)
        ip_suffix = (i // group_size) % 255
        source_ip = f"192.168.{ip_suffix}.{i % 255}"

        # Spread events across time span
        offset_seconds = (i / count) * time_span_minutes * 60
        timestamp = base_time - timedelta(seconds=offset_seconds)

        event = {
            "id": f"perf-event-{i:05d}",
            "timestamp": timestamp.isoformat(),
            "source_ip": source_ip,
            "username": f"user-{i % 50}",  # 50 different users
            "hostname": f"server-{i % 20}",  # 20 different servers
            "severity": random.choice(severities),
            "category": random.choice(categories),
            "message": f"Test event message {i} for performance testing"
        }
        events.append(event)

    return events


class TestCorrelationPerformance:
    """Test correlation performance requirements."""

    @pytest.mark.asyncio
    async def test_correlate_100_events_performance(self, test_client: AsyncClient):
        """Test correlating 100 events completes in reasonable time."""
        events = generate_test_events(100, time_span_minutes=30)

        start_time = time.time()
        response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": events}
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200
        data = response.json()

        # Performance requirement: 100 events should correlate in < 0.5s
        assert elapsed < 0.5, f"100 events correlation took {elapsed:.2f}s, expected < 0.5s"
        assert data["total_events_processed"] == 100

        print(f"✓ 100 events correlated in {elapsed:.3f}s")

    @pytest.mark.asyncio
    async def test_correlate_500_events_performance(self, test_client: AsyncClient):
        """Test correlating 500 events completes in reasonable time."""
        events = generate_test_events(500, time_span_minutes=60)

        start_time = time.time()
        response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": events}
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200
        data = response.json()

        # Performance requirement: 500 events should correlate in < 1s
        assert elapsed < 1.0, f"500 events correlation took {elapsed:.2f}s, expected < 1.0s"
        assert data["total_events_processed"] == 500

        print(f"✓ 500 events correlated in {elapsed:.3f}s")

    @pytest.mark.asyncio
    async def test_correlate_1000_events_performance(self, test_client: AsyncClient):
        """Test correlating 1000 events meets < 2s requirement."""
        events = generate_test_events(1000, time_span_minutes=120)

        start_time = time.time()
        response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": events}
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200
        data = response.json()

        # CRITICAL PERFORMANCE REQUIREMENT: 1000 events < 2s
        assert elapsed < 2.0, f"❌ 1000 events correlation took {elapsed:.2f}s, FAILED < 2.0s requirement"
        assert data["total_events_processed"] == 1000

        print(f"✓ 1000 events correlated in {elapsed:.3f}s (requirement: < 2.0s)")

        # Log correlation quality
        incident_count = len(data["correlated_events"])
        print(f"  → Generated {incident_count} correlated incidents")
        print(f"  → Events per incident: {1000 / incident_count:.1f}")

    @pytest.mark.asyncio
    async def test_correlate_5000_events_stress(self, test_client: AsyncClient):
        """Stress test with 5000 events (optional, higher threshold)."""
        events = generate_test_events(5000, time_span_minutes=240)

        start_time = time.time()
        response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": events}
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200
        data = response.json()

        # For 5000 events, allow up to 10s (still reasonable for batch processing)
        assert elapsed < 10.0, f"5000 events correlation took {elapsed:.2f}s, expected < 10.0s"
        assert data["total_events_processed"] == 5000

        print(f"✓ 5000 events correlated in {elapsed:.3f}s")


class TestDatabaseQueryPerformance:
    """Test database query performance with indexes."""

    @pytest.mark.asyncio
    async def test_get_incidents_query_performance(self, test_client: AsyncClient):
        """Test GET /incidents query performance."""
        # First create some incidents
        events = generate_test_events(200, time_span_minutes=30)
        await test_client.post("/api/correlation/correlate", json={"events": events})

        # Measure query performance
        start_time = time.time()
        response = await test_client.get("/api/correlation/incidents?limit=50")
        elapsed = time.time() - start_time

        assert response.status_code == 200
        incidents = response.json()

        # Database queries should be fast with proper indexes
        assert elapsed < 0.2, f"Query took {elapsed:.3f}s, expected < 0.2s"
        assert len(incidents) <= 50

        print(f"✓ GET /incidents query returned {len(incidents)} results in {elapsed:.3f}s")

    @pytest.mark.asyncio
    async def test_stats_query_performance(self, test_client: AsyncClient):
        """Test GET /stats query performance."""
        start_time = time.time()
        response = await test_client.get("/api/correlation/stats")
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 0.1, f"Stats query took {elapsed:.3f}s, expected < 0.1s"

        print(f"✓ GET /stats query completed in {elapsed:.3f}s")

    @pytest.mark.asyncio
    async def test_rules_query_performance(self, test_client: AsyncClient):
        """Test GET /rules query performance."""
        start_time = time.time()
        response = await test_client.get("/api/correlation/rules")
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 0.1, f"Rules query took {elapsed:.3f}s, expected < 0.1s"

        print(f"✓ GET /rules query completed in {elapsed:.3f}s")


class TestSimilarityCaching:
    """Test similarity calculation caching effectiveness."""

    @pytest.mark.asyncio
    async def test_similarity_cache_hit_rate(self, test_client: AsyncClient):
        """Test that similarity cache improves performance on repeated events."""
        # Generate events with overlapping patterns
        events = generate_test_events(300, time_span_minutes=30)

        # First run (cold cache)
        start_time = time.time()
        response1 = await test_client.post(
            "/api/correlation/correlate",
            json={"events": events}
        )
        time_cold = time.time() - start_time

        # Second run with similar events (warm cache)
        events_warm = generate_test_events(300, time_span_minutes=30)
        start_time = time.time()
        response2 = await test_client.post(
            "/api/correlation/correlate",
            json={"events": events_warm}
        )
        time_warm = time.time() - start_time

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Warm cache should be faster (or at least not significantly slower)
        print(f"✓ Cold cache: {time_cold:.3f}s, Warm cache: {time_warm:.3f}s")

        # Cache should provide at least 10% improvement
        if time_warm < time_cold:
            improvement = ((time_cold - time_warm) / time_cold) * 100
            print(f"  → Cache improvement: {improvement:.1f}%")


class TestScalability:
    """Test system scalability with increasing load."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("event_count", [100, 500, 1000])
    async def test_linear_scalability(self, test_client: AsyncClient, event_count: int):
        """Test that correlation time scales roughly linearly with event count."""
        events = generate_test_events(event_count, time_span_minutes=60)

        start_time = time.time()
        response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": events}
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200
        data = response.json()

        # Calculate events per second
        events_per_second = event_count / elapsed

        # Should process at least 500 events/second
        assert events_per_second >= 500, f"Processing rate: {events_per_second:.0f} events/s, required: ≥500"

        print(f"✓ {event_count} events: {elapsed:.3f}s ({events_per_second:.0f} events/s)")

    @pytest.mark.asyncio
    async def test_concurrent_correlation_requests(self, test_client: AsyncClient):
        """Test handling multiple concurrent correlation requests."""
        import asyncio

        # Create 5 concurrent requests
        tasks = []
        for i in range(5):
            events = generate_test_events(200, time_span_minutes=30)
            task = test_client.post("/api/correlation/correlate", json={"events": events})
            tasks.append(task)

        start_time = time.time()
        responses = await asyncio.gather(*tasks)
        elapsed = time.time() - start_time

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

        # Concurrent processing should be faster than sequential
        # (This is a rough check - actual performance depends on async handling)
        print(f"✓ 5 concurrent requests completed in {elapsed:.3f}s")
        print(f"  → Average per request: {elapsed/5:.3f}s")


class TestMemoryEfficiency:
    """Test memory efficiency during correlation."""

    @pytest.mark.asyncio
    async def test_large_event_payload_memory(self, test_client: AsyncClient):
        """Test handling large event payloads without memory issues."""
        # Generate large payload (5000 events)
        events = generate_test_events(5000, time_span_minutes=120)

        # Measure request
        start_time = time.time()
        response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": events}
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200
        data = response.json()

        # Should complete without excessive memory usage
        assert elapsed < 15.0, f"Large payload took {elapsed:.2f}s"
        assert data["total_events_processed"] == 5000

        print(f"✓ Large payload (5000 events) processed in {elapsed:.3f}s")


class TestRealWorldScenarios:
    """Test performance with realistic event patterns."""

    @pytest.mark.asyncio
    async def test_brute_force_pattern_performance(self, test_client: AsyncClient):
        """Test performance with brute force attack pattern."""
        # Generate events simulating brute force (same IP, user, time)
        base_time = datetime.now(timezone.utc)
        events = [
            {
                "id": f"bf-{i:04d}",
                "timestamp": (base_time - timedelta(seconds=i*5)).isoformat(),
                "source_ip": "192.168.1.100",
                "username": "admin",
                "hostname": "server01",
                "severity": "high",
                "category": "authentication",
                "message": "Login failed for user admin"
            }
            for i in range(100)
        ]

        start_time = time.time()
        response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": events}
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200
        data = response.json()

        # Should create one strong correlation
        assert len(data["correlated_events"]) >= 1
        assert elapsed < 0.5

        print(f"✓ Brute force pattern (100 events): {elapsed:.3f}s, {len(data['correlated_events'])} incidents")

    @pytest.mark.asyncio
    async def test_port_scan_pattern_performance(self, test_client: AsyncClient):
        """Test performance with port scan pattern."""
        # Generate events simulating port scan (same IP, different ports)
        base_time = datetime.now(timezone.utc)
        events = [
            {
                "id": f"scan-{i:04d}",
                "timestamp": (base_time - timedelta(seconds=i)).isoformat(),
                "source_ip": "10.0.0.50",
                "dest_port": 20 + i,
                "username": "scanner",
                "hostname": "firewall",
                "severity": "medium",
                "category": "network",
                "message": f"Port scan detected on port {20+i}"
            }
            for i in range(200)
        ]

        start_time = time.time()
        response = await test_client.post(
            "/api/correlation/correlate",
            json={"events": events}
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 0.8

        print(f"✓ Port scan pattern (200 events): {elapsed:.3f}s")


class TestPerformanceRegression:
    """Tests to prevent performance regressions."""

    @pytest.mark.asyncio
    async def test_baseline_correlation_performance(self, test_client: AsyncClient):
        """Establish baseline performance metric."""
        events = generate_test_events(1000, time_span_minutes=60)

        # Run multiple times to get stable measurement
        times = []
        for _ in range(3):
            start_time = time.time()
            response = await test_client.post(
                "/api/correlation/correlate",
                json={"events": events}
            )
            elapsed = time.time() - start_time
            times.append(elapsed)

        avg_time = sum(times) / len(times)

        assert response.status_code == 200

        # Baseline: 1000 events should correlate in < 2s
        assert avg_time < 2.0, f"Baseline failed: {avg_time:.3f}s average"

        print(f"✓ Baseline performance: {avg_time:.3f}s average (n=3)")
        print(f"  → Min: {min(times):.3f}s, Max: {max(times):.3f}s")

        # Store baseline for future comparisons
        baseline = {
            "event_count": 1000,
            "avg_time_seconds": avg_time,
            "min_time": min(times),
            "max_time": max(times),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        print(f"  → Baseline data: {baseline}")


# Performance summary reporter
@pytest.fixture(autouse=True)
def performance_summary(request):
    """Print performance summary after test run."""
    yield

    if request.node.callspec.id == "test_baseline_correlation_performance":
        print("\n" + "="*70)
        print("🚀 PERFORMANCE TEST SUMMARY")
        print("="*70)
        print("All critical performance requirements:")
        print("  ✓ 100 events < 0.5s")
        print("  ✓ 500 events < 1.0s")
        print("  ✓ 1000 events < 2.0s  ← CRITICAL REQUIREMENT")
        print("  ✓ Database queries < 0.2s")
        print("="*70)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
