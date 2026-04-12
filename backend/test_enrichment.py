#!/usr/bin/env python3
"""
Test script for Alert Enrichment
"""

import asyncio
import json

from sqlalchemy import select

from db.session import AsyncSessionLocal
from models.security_alert import SecurityAlert


async def show_enriched_alerts():
    """Display enriched alerts"""
    async with AsyncSessionLocal() as session:
        query = select(SecurityAlert).order_by(SecurityAlert.created_at.desc()).limit(5)
        result = await session.execute(query)
        alerts = result.scalars().all()

        print("\n🔍 Recently Enriched Alerts")
        print("=" * 60)

        for alert in alerts:
            print(f"\n📋 Alert #{alert.id}")
            print(f"   Source: {alert.source}")
            print(f"   Title: {alert.title}")
            print(f"   Severity: {alert.severity}")
            print(f"   IP: {alert.source_ip}")

            if alert.raw_data and alert.raw_data.get("threat_intel"):
                ti = alert.raw_data["threat_intel"]
                print("\n   🎯 Threat Intel:")

                # Show indicators
                indicators = ti.get("indicators", {})
                if indicators:
                    for indicator_type, data in indicators.items():
                        print(f"      {indicator_type}:")
                        if isinstance(data, dict):
                            reputation = data.get("reputation", "unknown")
                            scores = data.get("scores", {})
                            print(f"         Reputation: {reputation}")
                            if scores:
                                print(f"         Scores: {scores}")

                # Show MITRE info
                mitre_info = ti.get("mitre_info", {})
                if mitre_info:
                    print("\n      MITRE ATT&CK Tactics:")
                    for tactic_id, tactic_data in mitre_info.items():
                        print(
                            f"         {tactic_id}: {tactic_data.get('name', 'Unknown')}"
                        )

                enriched_at = ti.get("enriched_at")
                if enriched_at:
                    print(f"\n      Enriched at: {enriched_at}")
            else:
                print("\n   ⚠️  Not enriched yet")


async def test_enrichment_api():
    """Test the enrichment service"""
    from services.alert_enrichment import AlertEnrichmentService

    print("\n🧪 Testing Enrichment Service")
    print("=" * 60)

    service = AlertEnrichmentService()

    # Get alert ID
    async with AsyncSessionLocal() as session:
        query = select(SecurityAlert).order_by(SecurityAlert.created_at.desc()).limit(1)
        result = await session.execute(query)
        alert = result.scalar_one_or_none()

        if alert:
            print(f"\n🔄 Enriching alert #{alert.id}: {alert.title}")
            success = await service.process_alert(alert.id)

            if success:
                print("✅ Enrichment successful")

                # Show the enriched data
                await session.refresh(alert)
                if alert.raw_data and alert.raw_data.get("threat_intel"):
                    ti = alert.raw_data["threat_intel"]
                    print("\n📊 Enrichment Data:")
                    print(json.dumps(ti, indent=2, default=str))
            else:
                print("ℹ️  Alert was skipped (already enriched or not found)")


async def get_enrichment_stats():
    """Get enrichment statistics"""
    from sqlalchemy import func, select

    from db.session import AsyncSessionLocal
    from models.security_alert import SecurityAlert

    print("\n📈 Enrichment Statistics")
    print("=" * 60)

    async with AsyncSessionLocal() as session:
        # Total alerts
        total_query = select(func.count()).select_from(SecurityAlert)
        total = (await session.execute(total_query)).scalar() or 0

        # Count enriched
        query = select(SecurityAlert)
        result = await session.execute(query)
        alerts = result.scalars().all()

        enriched = sum(
            1 for a in alerts if a.raw_data and a.raw_data.get("threat_intel")
        )

        print(f"\n   Total Alerts: {total}")
        print(f"   Enriched: {enriched}")
        print(f"   Rate: {enriched/total*100:.1f}%" if total > 0 else "   Rate: 0%")


async def main():
    """Run all tests"""
    print("🎯 Alert Enrichment Test Suite")
    print("=" * 60)

    try:
        # Test enrichment
        await test_enrichment_api()

        # Show enriched alerts
        await show_enriched_alerts()

        # Show statistics
        await get_enrichment_stats()

        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("\n💡 Next steps:")
        print("   1. Start backend: uvicorn main:app --reload")
        print("   2. Test API: POST /api/v1/alert-enrichment/process/{id}")
        print("   3. View stats: GET /api/v1/alert-enrichment/stats")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
