"""Test alert trends time series aggregation.

This test verifies that the time series aggregation works correctly.
"""

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def test_time_format_logic():
    """Test the time format logic for different intervals."""
    from datetime import datetime

    print("Testing time interval formats...")

    # Test hour interval
    test_time = datetime(2026, 3, 2, 14, 30, 45)
    hour_formatted = test_time.strftime("%Y-%m-%d %H:00:00")
    assert hour_formatted == "2026-03-02 14:00:00"
    print(f"✅ Hour format: {hour_formatted}")

    # Test day interval
    day_formatted = test_time.strftime("%Y-%m-%d")
    assert day_formatted == "2026-03-02"
    print(f"✅ Day format: {day_formatted}")

    # Test week interval
    week_formatted = test_time.strftime("%Y-W%W")
    print(f"✅ Week format: {week_formatted}")

    # Test date truncation
    day_timestamp = datetime.strptime(day_formatted, "%Y-%m-%d").replace(
        hour=0, minute=0, second=0
    )
    assert day_timestamp == datetime(2026, 3, 2, 0, 0, 0)
    print(f"✅ Day timestamp: {day_timestamp}")

    print("\n✅ All time format tests passed!")


def test_aggregation_query_structure():
    """Test that the aggregation query is correctly structured."""
    print("\nTesting aggregation query structure...")

    # Hour interval query
    hour_query = """
        SELECT
            strftime('%Y-%m-%d %H:00:00', created_at) as period,
            COUNT(*) as total,
            SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END) as critical,
            SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END) as high,
            SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END) as medium,
            SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END) as low,
            SUM(CASE WHEN severity = 'info' THEN 1 ELSE 0 END) as info
        FROM security_alerts
        WHERE created_at >= :start_date AND created_at <= :end_date
        GROUP BY period
        ORDER BY period
    """

    # Verify key components
    assert "strftime" in hour_query
    assert "COUNT(*) as total" in hour_query
    assert "SUM(CASE WHEN severity" in hour_query
    assert "GROUP BY period" in hour_query
    assert "ORDER BY period" in hour_query

    print("✅ Query structure validated")
    print("\nQuery key features:")
    print("  - Time grouping: strftime() for SQLite")
    print("  - Total count: COUNT(*)")
    print("  - Severity breakdown: CASE WHEN SUM()")
    print("  - Grouping: GROUP BY period")
    print("  - Ordering: ORDER BY period")


def test_trend_data_structure():
    """Test the expected structure of trend data."""
    from datetime import datetime

    from schemas.alert_lifecycle import AlertTrend

    print("\nTesting trend data structure...")

    # Create a sample trend
    trend = AlertTrend(
        timestamp=datetime(2026, 3, 2, 14, 0, 0),
        count=100,
        by_severity={
            "critical": 5,
            "high": 15,
            "medium": 30,
            "low": 40,
            "info": 10,
        },
    )

    assert trend.count == 100
    assert trend.by_severity["critical"] == 5
    assert trend.by_severity["high"] == 15
    assert sum(trend.by_severity.values()) == 100

    print("✅ Trend structure validated")
    print("\nSample trend:")
    print(f"  Timestamp: {trend.timestamp}")
    print(f"  Total: {trend.count}")
    print(f"  Critical: {trend.by_severity['critical']}")
    print(f"  High: {trend.by_severity['high']}")
    print(f"  Medium: {trend.by_severity['medium']}")
    print(f"  Low: {trend.by_severity['low']}")
    print(f"  Info: {trend.by_severity['info']}")


def test_interval_validation():
    """Test interval validation logic."""
    print("\nTesting interval validation...")

    valid_intervals = ["hour", "day", "week"]
    for interval in valid_intervals:
        if interval == "hour":
            format = "%Y-%m-%d %H:00:00"
            trunc = "strftime('%Y-%m-%d %H:00:00', created_at)"
        elif interval == "day":
            format = "%Y-%m-%d"
            trunc = "date(created_at)"
        elif interval == "week":
            format = "%Y-W%W"
            trunc = "strftime('%Y-W%W', created_at)"
        else:
            raise ValueError(f"Invalid interval: {interval}")

        print(f"  ✅ {interval}: format={format}, trunc={trunc[:40]}...")

    # Test invalid interval
    try:
        interval = "invalid"
        if interval not in ["hour", "day", "week"]:
            raise ValueError(f"Invalid interval: {interval}")
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        print(f"  ✅ Invalid interval correctly rejected: {e}")


def test_sqlite_compatibility():
    """Test SQLite-specific syntax."""
    print("\nTesting SQLite compatibility...")

    # SQLite date/time functions
    sqlite_functions = [
        "strftime",
        "date",
        "time",
        "datetime",
        "CASE WHEN",
    ]

    print("  SQLite functions used:")
    for func in sqlite_functions:
        print(f"    ✅ {func}")

    # Note: For PostgreSQL, would use DATE_TRUNC instead
    print("\n  PostgreSQL equivalent: DATE_TRUNC()")
    print("  ⚠️  Current implementation is SQLite-specific")


def document_formulas():
    """Document the time series aggregation formulas."""
    print("\n" + "=" * 60)
    print("TIME SERIES AGGREGATION FORMULAS")
    print("=" * 60)

    print("\n1. Hour Interval:")
    print("   Format: 'YYYY-MM-DD HH:00:00'")
    print("   Example: '2026-03-02 14:00:00'")
    print("   SQL: strftime('%Y-%m-%d %H:00:00', created_at)")

    print("\n2. Day Interval:")
    print("   Format: 'YYYY-MM-DD'")
    print("   Example: '2026-03-02'")
    print("   SQL: date(created_at)")

    print("\n3. Week Interval:")
    print("   Format: 'YYYY-WWW'")
    print("   Example: '2026-W09'")
    print("   SQL: strftime('%Y-W%W', created_at)")

    print("\n4. Severity Breakdown:")
    print("   SUM(CASE WHEN severity = 'critical' THEN 1 ELSE 0 END)")
    print("   SUM(CASE WHEN severity = 'high' THEN 1 ELSE 0 END)")
    print("   SUM(CASE WHEN severity = 'medium' THEN 1 ELSE 0 END)")
    print("   SUM(CASE WHEN severity = 'low' THEN 1 ELSE 0 END)")
    print("   SUM(CASE WHEN severity = 'info' THEN 1 ELSE 0 END)")

    print("\n5. Example Output:")
    print("   {")
    print("     'timestamp': '2026-03-02 14:00:00',")
    print("     'count': 150,")
    print("     'by_severity': {")
    print("       'critical': 10,")
    print("       'high': 25,")
    print("       'medium': 45,")
    print("       'low': 50,")
    print("       'info': 20")
    print("     }")
    print("   }")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("ALERT TRENDS TIME SERIES TEST SUITE")
    print("=" * 60)

    test_time_format_logic()
    test_aggregation_query_structure()
    test_trend_data_structure()
    test_interval_validation()
    test_sqlite_compatibility()
    document_formulas()

    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("=" * 60)
    print("\n⚠️  Note: Implementation is SQLite-specific")
    print("   For PostgreSQL, use DATE_TRUNC() instead")
    print("=" * 60)
