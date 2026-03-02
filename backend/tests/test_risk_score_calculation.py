"""Test risk score calculation in event correlation service.

This test verifies that the risk scoring algorithm works correctly.
"""

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from datetime import datetime, timezone
from services.event_correlation_service import (
    EventCorrelationService,
    SEVERITY_SCORES,
    CRITICALITY_WEIGHTS,
)


def test_severity_scores():
    """Test severity score constants."""
    print("Testing severity scores...")
    assert SEVERITY_SCORES["critical"] == 90
    assert SEVERITY_SCORES["high"] == 70
    assert SEVERITY_SCORES["medium"] == 50
    assert SEVERITY_SCORES["low"] == 30
    assert SEVERITY_SCORES["info"] == 10
    print("✅ Severity scores are correct")


def test_criticality_weights():
    """Test criticality weight constants."""
    print("\nTesting criticality weights...")
    assert CRITICALITY_WEIGHTS["critical"] == 1.5
    assert CRITICALITY_WEIGHTS["high"] == 1.3
    assert CRITICALITY_WEIGHTS["medium"] == 1.0
    assert CRITICALITY_WEIGHTS["low"] == 0.8
    print("✅ Criticality weights are correct")


def test_risk_score_calculation():
    """Test risk score calculation logic."""
    print("\nTesting risk score calculation...")

    # Mock service (database not needed for this test)
    class MockDB:
        pass

    service = EventCorrelationService(MockDB())

    # Test case 1: Critical severity, single event
    score1 = service._calculate_risk_score(
        severity="critical",
        common_entities={"ip_addresses": ["192.168.1.1"], "usernames": [], "hostnames": []},
        event_count=1
    )
    expected1 = 90 * 1.0 * 1.0  # base * weight * multiplier
    assert abs(score1 - expected1) < 0.1, f"Expected {expected1}, got {score1}"
    print(f"✅ Critical, 1 event: {score1}")

    # Test case 2: High severity, single event
    score2 = service._calculate_risk_score(
        severity="high",
        common_entities={"ip_addresses": [], "usernames": ["admin"], "hostnames": []},
        event_count=1
    )
    expected2 = 70 * 1.0 * 1.0
    assert abs(score2 - expected2) < 0.1, f"Expected {expected2}, got {score2}"
    print(f"✅ High, 1 event: {score2}")

    # Test case 3: Medium severity, multiple events
    score3 = service._calculate_risk_score(
        severity="medium",
        common_entities={"ip_addresses": ["10.0.0.1", "10.0.0.2"], "usernames": [], "hostnames": []},
        event_count=5
    )
    expected3 = 50 * 1.0 * min(1.0 + (5 - 1) * 0.05, 1.5)  # base * weight * multiplier(1.2)
    assert abs(score3 - expected3) < 0.1, f"Expected {expected3}, got {score3}"
    print(f"✅ Medium, 5 events: {score3}")

    # Test case 4: Low severity, many events
    score4 = service._calculate_risk_score(
        severity="low",
        common_entities={"ip_addresses": [], "usernames": [], "hostnames": ["server1"]},
        event_count=15
    )
    expected4 = 30 * 1.0 * 1.5  # multiplier capped at 1.5
    assert abs(score4 - expected4) < 0.1, f"Expected {expected4}, got {score4}"
    print(f"✅ Low, 15 events: {score4}")

    # Test case 5: Info severity
    score5 = service._calculate_risk_score(
        severity="info",
        common_entities={"ip_addresses": [], "usernames": [], "hostnames": []},
        event_count=1
    )
    expected5 = 10 * 1.0 * 1.0
    assert abs(score5 - expected5) < 0.1, f"Expected {expected5}, got {score5}"
    print(f"✅ Info, 1 event: {score5}")

    # Test case 6: Verify score doesn't exceed 100
    score6 = service._calculate_risk_score(
        severity="critical",
        common_entities={"ip_addresses": [], "usernames": [], "hostnames": []},
        event_count=50  # Many events
    )
    assert score6 <= 100.0, f"Score should not exceed 100, got {score6}"
    print(f"✅ Critical, 50 events (capped at 100): {score6}")

    print("\n✅ All risk score calculations passed!")


def test_scoring_formula():
    """Test and document the scoring formula."""
    print("\n" + "="*60)
    print("RISK SCORING FORMULA")
    print("="*60)
    print("\n1. Base Score (from severity):")
    print("   - Critical: 90")
    print("   - High: 70")
    print("   - Medium: 50")
    print("   - Low: 30")
    print("   - Info: 10")

    print("\n2. Asset Criticality Weight:")
    print("   - Critical: ×1.5")
    print("   - High: ×1.3")
    print("   - Medium: ×1.0")
    print("   - Low: ×0.8")

    print("\n3. Event Count Multiplier:")
    print("   - 1 event: ×1.0")
    print("   - 2 events: ×1.05")
    print("   - 5 events: ×1.2")
    print("   - 10+ events: ×1.5 (capped)")

    print("\n4. Final Formula:")
    print("   risk_score = min(base × weight × multiplier, 100)")
    print("="*60)

    # Example calculation
    print("\nEXAMPLE: Critical severity, 3 events, medium asset")
    base = 90
    weight = 1.0
    multiplier = 1.0 + (3 - 1) * 0.05  # 1.1
    result = min(base * weight * multiplier, 100)
    print(f"   {base} × {weight} × {multiplier:.2f} = {result:.1f}")
    print("="*60 + "\n")


if __name__ == "__main__":
    print("="*60)
    print("RISK SCORE CALCULATION TEST SUITE")
    print("="*60)

    test_severity_scores()
    test_criticality_weights()
    test_risk_score_calculation()
    test_scoring_formula()

    print("\n" + "="*60)
    print("🎉 ALL TESTS PASSED!")
    print("="*60)
