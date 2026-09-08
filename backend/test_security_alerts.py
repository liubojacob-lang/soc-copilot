#!/usr/bin/env python3
"""
Test script for Security Alerts API integration.
Tests the complete flow of alert ingestion and retrieval.
"""

import asyncio
import sys
from datetime import datetime

from db.session import AsyncSessionLocal
from models.security_alert import SecurityAlert


async def create_test_alert():
    """Create a test security alert in the database."""
    async with AsyncSessionLocal() as session:
        alert = SecurityAlert(
            source="test",
            external_event_id=f"test-{datetime.now().timestamp()}",
            event_type="test_event",
            severity="info",
            title="Test Alert",
            description="This is a test alert to verify the integration",
            source_ip="192.168.1.1",
            destination_ip="10.0.0.1",
            agent_name="test-agent",
            rule_id="test-001",
            rule_level=1,
            rule_groups="test",
            status="open",
        )

        session.add(alert)
        await session.commit()
        await session.refresh(alert)

        print(f"✅ Test alert created with ID: {alert.id}")
        return alert


async def list_alerts():
    """List all alerts in the database."""
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select

        query = (
            select(SecurityAlert).order_by(SecurityAlert.created_at.desc()).limit(10)
        )
        result = await session.execute(query)
        alerts = result.scalars().all()

        print(f"\n📊 Total alerts in database: {len(alerts)} (showing latest 10)")
        for alert in alerts:
            print(
                f"  - [{alert.id}] {alert.source}: {alert.title} ({alert.severity}) - {alert.status}"
            )


async def get_statistics():
    """Get alert statistics."""
    async with AsyncSessionLocal() as session:

        from sqlalchemy import func, select

        # Total count
        total_query = select(func.count()).select_from(SecurityAlert)
        total = (await session.execute(total_query)).scalar() or 0

        # By severity
        severity_query = select(
            SecurityAlert.severity, func.count(SecurityAlert.id)
        ).group_by(SecurityAlert.severity)
        severity_result = await session.execute(severity_query)
        by_severity = {row[0]: row[1] for row in severity_result.all()}

        print("\n📈 Alert Statistics:")
        print(f"  Total: {total}")
        print(f"  By Severity: {by_severity}")


async def main():
    """Run all tests."""
    print("🧪 Testing Security Alerts Integration")
    print("=" * 50)

    try:
        # Test 1: Create alert
        await create_test_alert()

        # Test 2: List alerts
        await list_alerts()

        # Test 3: Get statistics
        await get_statistics()

        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("\n📖 Next steps:")
        print("  1. Start the backend: uvicorn main:app --reload")
        print("  2. Test API: http://localhost:8000/docs")
        print("  3. Send test alert via POST /api/v1/security-alerts/ingest")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
