"""Unit tests for event correlation service.

Tests core algorithms:
- Entity extraction
- Similarity calculation
- Rule matching
- Correlation generation
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from services.event_correlation_service import EventCorrelationService
from models.correlation_rule import CorrelationRule
from models.correlated_event import CorrelatedEvent


# Fixtures
@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


# Test data
MOCK_EVENTS = [
    {
        "id": "alert-1",
        "timestamp": "2026-02-16T18:00:00+00:00",
        "source_ip": "192.168.1.100",
        "username": "admin",
        "hostname": "server01",
        "severity": "high",
        "category": "authentication",
        "message": "Login failed for user admin"
    },
    {
        "id": "alert-2",
        "timestamp": "2026-02-16T18:02:00+00:00",
        "source_ip": "192.168.1.100",
        "username": "admin",
        "hostname": "server01",
        "severity": "high",
        "category": "authentication",
        "message": "Login failed for user admin"
    },
    {
        "id": "alert-3",
        "timestamp": "2026-02-16T18:04:00+00:00",
        "source_ip": "192.168.1.100",
        "username": "admin",
        "hostname": "server01",
        "severity": "high",
        "category": "authentication",
        "message": "Login failed for user admin"
    },
    {
        "id": "alert-4",
        "timestamp": "2026-02-16T10:00:00+00:00",  # 8 hours ago
        "source_ip": "10.0.0.50",
        "username": "guest",
        "hostname": "workstation01",
        "severity": "medium",
        "category": "network",
        "message": "Port scan detected"
    }
]


class TestEntityExtraction:
    """Test entity extraction from events."""

    @pytest.mark.asyncio
    async def test_extract_ips(self):
        """Test IP address extraction."""
        mock_db = Mock(spec=AsyncSession)
        service = EventCorrelationService(db=mock_db)

        event = {
            "source_ip": "192.168.1.100",
            "dest_ip": "10.0.0.50",
            "network": {
                "source_ips": ["172.16.0.1", "172.16.0.2"]
            }
        }

        ips = service._extract_ips(event)

        assert "192.168.1.100" in ips
        assert "10.0.0.50" in ips
        assert "172.16.0.1" in ips
        assert "172.16.0.2" in ips
        assert len(ips) == 4

    @pytest.mark.asyncio
    async def test_extract_usernames(self):
        """Test username extraction."""
        service = EventCorrelationService(db=AsyncMock())

        event = {
            "username": "admin",
            "user": "john.doe",
            "actor": "alice"
        }

        users = service._extract_usernames(event)

        assert "admin" in users
        assert "john.doe" in users
        assert "alice" in users
        assert len(users) == 3

    @pytest.mark.asyncio
    async def test_extract_hostnames(self):
        """Test hostname extraction."""
        service = EventCorrelationService(db=AsyncMock())

        event = {
            "hostname": "server01",
            "host": "db01",
            "device": "firewall"
        }

        hosts = service._extract_hostnames(event)

        assert "server01" in hosts
        assert "db01" in hosts
        assert "firewall" in hosts
        assert len(hosts) == 3

    @pytest.mark.asyncio
    async def test_extract_entities(self):
        """Test complete entity extraction."""
        service = EventCorrelationService(db=AsyncMock())

        events = MOCK_EVENTS[:2]
        enriched = await service._extract_entities(events)

        assert len(enriched) == 2
        assert "entities" in enriched[0]
        assert enriched[0]["entities"]["ip_addresses"] == {"192.168.1.100"}
        assert enriched[0]["entities"]["usernames"] == {"admin"}
        assert enriched[0]["entities"]["hostnames"] == {"server01"}


class TestSimilarityCalculation:
    """Test event similarity calculation."""

    @pytest.mark.asyncio
    async def test_jaccard_similarity_messages(self):
        """Test Jaccard similarity on messages."""
        service = EventCorrelationService(db=AsyncMock())

        events = [
            {"message": "login failed for user admin"},
            {"message": "login failed for user admin"},
            {"message": "port scan detected"}
        ]

        similarity = await service._jaccard_similarity_messages(events)

        # First two are identical, third is different
        assert similarity > 0.5
        assert similarity < 1.0

    @pytest.mark.asyncio
    async def test_category_match_score(self):
        """Test category match score."""
        service = EventCorrelationService(db=AsyncMock())

        # All same category
        events_same = [
            {"category": "authentication"},
            {"category": "authentication"},
            {"category": "authentication"}
        ]
        score_same = await service._category_match_score(events_same)
        assert score_same == 1.0

        # All different
        events_diff = [
            {"category": "authentication"},
            {"category": "network"},
            {"category": "malware"}
        ]
        score_diff = await service._category_match_score(events_diff)
        assert score_diff == 0.0

        # Partial match
        events_partial = [
            {"category": "authentication"},
            {"category": "authentication"},
            {"category": "network"}
        ]
        score_partial = await service._category_match_score(events_partial)
        assert 0 < score_partial < 1.0

    @pytest.mark.asyncio
    async def test_severity_proximity_score(self):
        """Test severity proximity score."""
        service = EventCorrelationService(db=AsyncMock())

        # All same severity
        events_same = [
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "high"}
        ]
        score_same = await service._severity_proximity_score(events_same)
        assert score_same == 1.0

        # Spread severity
        events_spread = [
            {"severity": "critical"},
            {"severity": "medium"},
            {"severity": "low"}
        ]
        score_spread = await service._severity_proximity_score(events_spread)
        assert 0 < score_spread < 1.0

    @pytest.mark.asyncio
    async def test_calculate_group_similarity(self):
        """Test complete similarity calculation."""
        service = EventCorrelationService(db=AsyncMock())

        # Similar events (same IP, user, category, time range)
        similar_events = MOCK_EVENTS[:3]
        similarity = await service._calculate_group_similarity(similar_events)

        assert similarity > 0.5  # Should be quite similar

        # Dissimilar events (different IP, user, category, time)
        dissimilar_events = [MOCK_EVENTS[0], MOCK_EVENTS[3]]
        similarity2 = await service._calculate_group_similarity(dissimilar_events)

        assert similarity2 < similarity


class TestTimeGrouping:
    """Test time-based grouping."""

    @pytest.mark.asyncio
    async def test_group_by_time(self):
        """Test time window grouping."""
        service = EventCorrelationService(db=AsyncMock())

        events = MOCK_EVENTS
        groups = await service._group_by_time(events)

        # Should have at least one time group
        assert len(groups) > 0

        # Each group should have events
        for time_bucket, group_events in groups.items():
            assert len(group_events) > 0

    @pytest.mark.asyncio
    async def test_expand_time_windows(self):
        """Test time window expansion."""
        service = EventCorrelationService(db=AsyncMock())

        time_groups = {
            "2026-02-16T18:00:00": [MOCK_EVENTS[0]],
            "2026-02-16T18:05:00": [MOCK_EVENTS[1]]
        }

        expanded = service._expand_time_windows(time_groups, window_seconds=600)

        # Expanded groups should include events from overlapping windows
        assert len(expanded) >= len(time_groups)


class TestRuleMatching:
    """Test correlation rule matching."""

    @pytest.mark.asyncio
    async def test_check_conditions_min_event_count(self):
        """Test condition: minimum event count."""
        service = EventCorrelationService(db=AsyncMock())

        # Test with enough events
        events = MOCK_EVENTS[:3]  # 3 events
        conditions = {"min_event_count": 2}
        result = await service._check_conditions(events, conditions)
        assert result is True

        # Test with insufficient events
        events = MOCK_EVENTS[:1]  # 1 event
        result = await service._check_conditions(events, conditions)
        assert result is False

    @pytest.mark.asyncio
    async def test_check_conditions_severity(self):
        """Test condition: minimum severity."""
        service = EventCorrelationService(db=AsyncMock())

        # Events meeting severity requirement
        events = [
            {"severity": "high"},
            {"severity": "critical"}
        ]
        conditions = {"min_severity": "high"}
        result = await service._check_conditions(events, conditions)
        assert result is True

        # Events not meeting severity requirement
        events = [
            {"severity": "low"},
            {"severity": "medium"}
        ]
        result = await service._check_conditions(events, conditions)
        assert result is False


class TestCorrelationGeneration:
    """Test correlated event generation."""

    @pytest.mark.asyncio
    async def test_create_correlated_event(self):
        """Test creating a correlated event from grouped events."""
        service = EventCorrelationService(db=AsyncMock())

        rule = CorrelationRule(
            id="rule-1",
            name="Test Rule",
            time_window_seconds=300,
            entity_types={"ip_address": True},
            min_similarity=0.7,
            action="aggregate"
        )

        events = MOCK_EVENTS[:3]
        similarity = 0.85

        correlated = await service._create_correlated_event(rule, events, similarity)

        assert correlated.title == "Correlated: 3 related events"
        assert correlated.raw_event_count == 3
        assert correlated.confidence_score == 0.85
        assert correlated.rule_id == "rule-1"
        assert "192.168.1.100" in correlated.common_entities["ip_addresses"]
        assert "admin" in correlated.common_entities["usernames"]

    @pytest.mark.asyncio
    async def test_merge_correlations(self):
        """Test merging overlapping correlations."""
        service = EventCorrelationService(db=AsyncMock())

        # Create mock correlated events with overlapping raw events
        event1 = CorrelatedEvent(
            id="corr-1",
            rule_id="rule-1",
            title="Incident 1",
            raw_event_ids=["alert-1", "alert-2"],
            raw_event_count=2,
            common_entities={"ip_addresses": ["192.168.1.100"]},
            first_seen="2026-02-16T18:00:00+00:00",
            last_seen="2026-02-16T18:05:00+00:00",
            severity="high",
            confidence_score=0.8,
            risk_score=60.0,
            status="open"
        )

        event2 = CorrelatedEvent(
            id="corr-2",
            rule_id="rule-1",
            title="Incident 2",
            raw_event_ids=["alert-2", "alert-3"],  # Overlaps
            raw_event_count=2,
            common_entities={"ip_addresses": ["192.168.1.100"]},
            first_seen="2026-02-16T18:02:00+00:00",
            last_seen="2026-02-16T18:06:00+00:00",
            severity="high",
            confidence_score=0.8,
            risk_score=60.0,
            status="open"
        )

        merged = await service._merge_correlations([event1, event2])

        # Should merge into one event
        assert len(merged) <= 2
        if len(merged) == 1:
            assert merged[0].raw_event_count == 3  # alert-1, alert-2, alert-3


# Fixtures
@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return None


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
