"""
Tests for alert deduplication and aggregation service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from services.alert_deduplication import (
    AlertDeduplicator,
    AlertAggregator,
    AlertStormSuppressor,
    get_alert_deduplicator,
    get_alert_aggregator,
    get_alert_aggregator,
    get_alert_storm_suppressor,
)


class TestAlertDeduplicator:
    """Tests for AlertDeduplicator class."""
    
    def test_generate_fingerprint_strict(self):
        """Test fingerprint generation with strict method."""
        alert = {
            "source": "wazuh",
            "event_type": "bruteforce",
            "source_ip": "192.168.1.100",
            "destination_ip": "10.0.0.1",
            "rule_id": "5710",
            "agent_name": "server-01",
        }
        
        session = Mock()
        deduplicator = AlertDeduplicator(session)
        
        fingerprint = deduplicator.generate_fingerprint(alert, method="strict")
        
        assert fingerprint is not None
        assert len(fingerprint) == 64  # SHA256 hex length
    
    def test_generate_fingerprint_balanced(self):
        """Test fingerprint generation with balanced method."""
        alert = {
            "source": "wazuh",
            "event_type": "bruteforce",
            "source_ip": "192.168.1.100",
            "rule_id": "5710",
        }
        
        session = Mock()
        deduplicator = AlertDeduplicator(session)
        
        fingerprint1 = deduplicator.generate_fingerprint(alert, method="balanced")
        fingerprint2 = deduplicator.generate_fingerprint(alert, method="balanced")
        
        assert fingerprint1 == fingerprint2
    
    def test_generate_fingerprint_relaxed(self):
        """Test fingerprint generation with relaxed method."""
        alert1 = {
            "event_type": "bruteforce",
            "source_ip": "192.168.1.100",
        }
        
        alert2 = {
            "event_type": "bruteforce",
            "source_ip": "192.168.1.100",
            "other_field": "different",
        }
        
        session = Mock()
        deduplicator = AlertDeduplicator(session)
        
        fingerprint1 = deduplicator.generate_fingerprint(alert1, method="relaxed")
        fingerprint2 = deduplicator.generate_fingerprint(alert2, method="relaxed")
        
        assert fingerprint1 == fingerprint2
    
    def test_fingerprint_different_alerts(self):
        """Test that different alerts have different fingerprints."""
        alert1 = {
            "source": "wazuh",
            "event_type": "bruteforce",
            "source_ip": "192.168.1.100",
        }
        
        alert2 = {
            "source": "wazuh",
            "event_type": "malware",
            "source_ip": "10.0.0.1",
        }
        
        session = Mock()
        deduplicator = AlertDeduplicator(session)
        
        fingerprint1 = deduplicator.generate_fingerprint(alert1, method="balanced")
        fingerprint2 = deduplicator.generate_fingerprint(alert2, method="balanced")
        
        assert fingerprint1 != fingerprint2


class TestAlertStormSuppressor:
    """Tests for AlertStormSuppressor class."""
    
    def test_threshold_config(self):
        """Test threshold configuration."""
        session = Mock()
        suppressor = AlertStormSuppressor(session)
        
        assert "critical" in suppressor.thresholds
        assert "high" in suppressor.thresholds
        assert "medium" in suppressor.thresholds
        assert "low" in suppressor.thresholds
        assert "info" in suppressor.thresholds
        
        assert suppressor.thresholds["critical"] == 10
        assert suppressor.thresholds["high"] == 20
        assert suppressor.thresholds["medium"] == 50


class TestFactoryFunctions:
    """Tests for factory functions."""
    
    def test_get_alert_deduplicator(self):
        """Test get_alert_deduplicator factory."""
        session = Mock()
        deduplicator = get_alert_deduplicator(session)
        assert isinstance(deduplicator, AlertDeduplicator)
    
    def test_get_alert_aggregator(self):
        """Test get_alert_aggregator factory."""
        session = Mock()
        aggregator = get_alert_aggregator(session)
        assert isinstance(aggregator, AlertAggregator)
    
    def test_get_alert_storm_suppressor(self):
        """Test get_alert_storm_suppressor factory."""
        session = Mock()
        suppressor = get_alert_storm_suppressor(session)
        assert isinstance(suppressor, AlertStormSuppressor)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
