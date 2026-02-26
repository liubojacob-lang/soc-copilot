"""Simple test to debug API response."""
import asyncio
import sys
sys.path.insert(0, '/Users/levent/Desktop/sec/backend')

from httpx import AsyncClient, ASGITransport
from main import app


async def test_correlate():
    """Test the correlate endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        test_events = [
            {
                "id": "test-001",
                "timestamp": "2026-02-16T18:00:00+00:00",
                "source_ip": "192.168.1.100",
                "username": "admin",
                "hostname": "server01",
                "severity": "high",
                "category": "authentication",
                "message": "Login failed"
            },
            {
                "id": "test-002",
                "timestamp": "2026-02-16T18:02:00+00:00",
                "source_ip": "192.168.1.100",
                "username": "admin",
                "hostname": "server01",
                "severity": "high",
                "category": "authentication",
                "message": "Login failed"
            }
        ]

        response = await client.post(
            "/api/correlation/correlate",
            json={"events": test_events}
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:1000]}")


if __name__ == "__main__":
    asyncio.run(test_correlate())
