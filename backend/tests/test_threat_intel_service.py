"""Unit tests for ThreatIntelService."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.threat_intel_service import ThreatIntelService
from schemas.threat_intel import (
    ThreatIntelResponse,
    IOCAnalysisResult,
    ThreatActorInfo,
    TTPInfo,
)


class TestThreatIntelServiceIOCAnalysis:
    """Tests for IOC analysis functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ThreatIntelService(session=None)

    @pytest.mark.asyncio
    async def test_analyze_ip_malicious(self, service):
        """Test analyzing malicious IP."""
        with patch.object(service, '_query_threat_feeds') as mock_query:
            mock_query.return_value = {
                "malicious": True,
                "confidence": 95,
                "threat_types": ["c2", "malware"],
                "first_seen": "2024-01-01",
                "last_seen": "2024-12-01",
                "reports": 150,
            }
            
            result = await service.analyze_ioc("192.168.1.1", "ip")
            
            assert result.is_malicious is True
            assert result.confidence == 95
            assert "c2" in result.threat_types

    @pytest.mark.asyncio
    async def test_analyze_ip_benign(self, service):
        """Test analyzing benign IP."""
        with patch.object(service, '_query_threat_feeds') as mock_query:
            mock_query.return_value = {
                "malicious": False,
                "confidence": 80,
                "threat_types": [],
                "reports": 0,
            }
            
            result = await service.analyze_ioc("8.8.8.8", "ip")
            
            assert result.is_malicious is False
            assert result.confidence == 80

    @pytest.mark.asyncio
    async def test_analyze_domain(self, service):
        """Test analyzing domain."""
        with patch.object(service, '_query_threat_feeds') as mock_query:
            mock_query.return_value = {
                "malicious": True,
                "confidence": 90,
                "threat_types": ["phishing"],
                "domain_age_days": 5,
                "reports": 50,
            }
            
            result = await service.analyze_ioc("malicious-domain.com", "domain")
            
            assert result.is_malicious is True
            assert "phishing" in result.threat_types

    @pytest.mark.asyncio
    async def test_analyze_hash(self, service):
        """Test analyzing file hash."""
        with patch.object(service, '_query_threat_feeds') as mock_query:
            mock_query.return_value = {
                "malicious": True,
                "confidence": 99,
                "threat_types": ["malware", "ransomware"],
                "file_type": "exe",
                "file_size": 1024000,
                "reports": 200,
            }
            
            result = await service.analyze_ioc(
                "5d41402abc4b2a76b9719d911017c592", 
                "hash"
            )
            
            assert result.is_malicious is True
            assert "malware" in result.threat_types
            assert "ransomware" in result.threat_types

    @pytest.mark.asyncio
    async def test_analyze_url(self, service):
        """Test analyzing URL."""
        with patch.object(service, '_query_threat_feeds') as mock_query:
            mock_query.return_value = {
                "malicious": True,
                "confidence": 85,
                "threat_types": ["malware_delivery"],
                "reports": 30,
            }
            
            result = await service.analyze_ioc(
                "http://malicious-site.com/payload.exe", 
                "url"
            )
            
            assert result.is_malicious is True
            assert "malware_delivery" in result.threat_types


class TestThreatIntelServiceEnrichment:
    """Tests for threat intelligence enrichment."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ThreatIntelService(session=None)

    @pytest.mark.asyncio
    async def test_enrich_with_mitre_attack(self, service):
        """Test enriching with MITRE ATT&CK data."""
        with patch.object(service, '_get_mitre_ttps') as mock_mitre:
            mock_mitre.return_value = [
                TTPInfo(
                    technique_id="T1059",
                    technique_name="Command and Scripting Interpreter",
                    tactic="Execution",
                    description="Adversaries may abuse command and script interpreters",
                ),
                TTPInfo(
                    technique_id="T1071",
                    technique_name="Application Layer Protocol",
                    tactic="Command and Control",
                    description="Adversaries may communicate using application layer protocols",
                ),
            ]
            
            result = await service.enrich_threat_data(
                threat_type="apt",
                iocs=["192.168.1.1"],
            )
            
            assert len(result.ttps) == 2
            assert result.ttps[0].technique_id == "T1059"

    @pytest.mark.asyncio
    async def test_enrich_with_threat_actors(self, service):
        """Test enriching with threat actor information."""
        with patch.object(service, '_get_threat_actors') as mock_actors:
            mock_actors.return_value = [
                ThreatActorInfo(
                    name="APT29",
                    aliases=["Cozy Bear", "The Dukes"],
                    country="Russia",
                    motivation="Espionage",
                    target_sectors=["Government", "Think Tanks"],
                    first_seen="2008",
                ),
            ]
            
            result = await service.enrich_threat_data(
                threat_type="apt",
                iocs=["192.168.1.1"],
            )
            
            assert len(result.threat_actors) == 1
            assert result.threat_actors[0].name == "APT29"

    @pytest.mark.asyncio
    async def test_enrich_with_campaigns(self, service):
        """Test enriching with campaign information."""
        with patch.object(service, '_get_related_campaigns') as mock_campaigns:
            mock_campaigns.return_value = [
                {
                    "name": "Operation Cozy Bear",
                    "description": "Targeting government entities",
                    "start_date": "2024-01-01",
                    "status": "active",
                },
            ]
            
            result = await service.enrich_threat_data(
                threat_type="apt",
                iocs=["192.168.1.1"],
            )
            
            assert len(result.campaigns) == 1
            assert result.campaigns[0]["name"] == "Operation Cozy Bear"


class TestThreatIntelServiceBulkAnalysis:
    """Tests for bulk IOC analysis."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ThreatIntelService(session=None)

    @pytest.mark.asyncio
    async def test_bulk_analyze_mixed_iocs(self, service):
        """Test bulk analyzing mixed IOCs."""
        iocs = [
            {"value": "192.168.1.1", "type": "ip"},
            {"value": "malicious.com", "type": "domain"},
            {"value": "5d41402abc4b2a76b9719d911017c592", "type": "hash"},
        ]
        
        with patch.object(service, 'analyze_ioc') as mock_analyze:
            mock_analyze.side_effect = [
                IOCAnalysisResult(
                    ioc_value="192.168.1.1",
                    ioc_type="ip",
                    is_malicious=True,
                    confidence=90,
                    threat_types=["c2"],
                ),
                IOCAnalysisResult(
                    ioc_value="malicious.com",
                    ioc_type="domain",
                    is_malicious=True,
                    confidence=85,
                    threat_types=["phishing"],
                ),
                IOCAnalysisResult(
                    ioc_value="5d41402abc4b2a76b9719d911017c592",
                    ioc_type="hash",
                    is_malicious=False,
                    confidence=60,
                    threat_types=[],
                ),
            ]
            
            results = await service.bulk_analyze_iocs(iocs)
            
            assert len(results) == 3
            assert results[0].is_malicious is True
            assert results[1].is_malicious is True
            assert results[2].is_malicious is False

    @pytest.mark.asyncio
    async def test_bulk_analyze_empty_list(self, service):
        """Test bulk analyzing empty list."""
        results = await service.bulk_analyze_iocs([])
        assert results == []

    @pytest.mark.asyncio
    async def test_bulk_analyze_with_cache(self, service):
        """Test bulk analysis with caching."""
        iocs = [
            {"value": "192.168.1.1", "type": "ip"},
            {"value": "192.168.1.1", "type": "ip"},
        ]
        
        with patch.object(service, 'analyze_ioc') as mock_analyze:
            mock_analyze.return_value = IOCAnalysisResult(
                ioc_value="192.168.1.1",
                ioc_type="ip",
                is_malicious=True,
                confidence=90,
                threat_types=["c2"],
            )
            
            results = await service.bulk_analyze_iocs(iocs)
            
            assert len(results) == 2
            assert mock_analyze.call_count == 2


class TestThreatIntelServiceCache:
    """Tests for caching functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ThreatIntelService(session=None)

    @pytest.mark.asyncio
    async def test_cache_hit(self, service):
        """Test cache hit scenario."""
        service._cache["192.168.1.1:ip"] = IOCAnalysisResult(
            ioc_value="192.168.1.1",
            ioc_type="ip",
            is_malicious=True,
            confidence=95,
            threat_types=["c2"],
        )
        
        result = await service.analyze_ioc("192.168.1.1", "ip")
        
        assert result.confidence == 95

    @pytest.mark.asyncio
    async def test_cache_miss(self, service):
        """Test cache miss scenario."""
        with patch.object(service, '_query_threat_feeds') as mock_query:
            mock_query.return_value = {
                "malicious": True,
                "confidence": 85,
                "threat_types": ["malware"],
                "reports": 10,
            }
            
            result = await service.analyze_ioc("10.0.0.1", "ip")
            
            assert result.confidence == 85
            assert "10.0.0.1:ip" in service._cache


class TestThreatIntelServiceValidation:
    """Tests for input validation."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ThreatIntelService(session=None)

    def test_validate_ip_address(self, service):
        """Test IP address validation."""
        assert service._validate_ioc_type("192.168.1.1", "ip") is True
        assert service._validate_ioc_type("256.256.256.256", "ip") is False
        assert service._validate_ioc_type("2001:db8::1", "ip") is True

    def test_validate_domain(self, service):
        """Test domain validation."""
        assert service._validate_ioc_type("example.com", "domain") is True
        assert service._validate_ioc_type("sub.example.com", "domain") is True
        assert service._validate_ioc_type("not a domain", "domain") is False

    def test_validate_hash(self, service):
        """Test hash validation."""
        assert service._validate_ioc_type(
            "5d41402abc4b2a76b9719d911017c592", 
            "hash"
        ) is True
        assert service._validate_ioc_type(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "hash"
        ) is True
        assert service._validate_ioc_type("not-a-hash", "hash") is False

    def test_validate_url(self, service):
        """Test URL validation."""
        assert service._validate_ioc_type("http://example.com", "url") is True
        assert service._validate_ioc_type("https://example.com/path", "url") is True
        assert service._validate_ioc_type("not a url", "url") is False


class TestThreatIntelServiceStatistics:
    """Tests for statistics functionality."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return ThreatIntelService(session=None)

    @pytest.mark.asyncio
    async def test_get_statistics(self, service):
        """Test getting threat intelligence statistics."""
        with patch.object(service, '_get_feed_statistics') as mock_stats:
            mock_stats.return_value = {
                "total_iocs": 1000000,
                "malicious_iocs": 500000,
                "feeds_active": 15,
                "last_update": "2024-12-01T00:00:00Z",
            }
            
            stats = await service.get_statistics()
            
            assert stats["total_iocs"] == 1000000
            assert stats["feeds_active"] == 15

    @pytest.mark.asyncio
    async def test_get_feed_health(self, service):
        """Test getting feed health status."""
        with patch.object(service, '_check_feed_health') as mock_health:
            mock_health.return_value = [
                {"name": "AlienVault", "status": "healthy", "latency_ms": 150},
                {"name": "VirusTotal", "status": "healthy", "latency_ms": 200},
                {"name": "MISP", "status": "degraded", "latency_ms": 5000},
            ]
            
            health = await service.get_feed_health()
            
            assert len(health) == 3
            assert health[0]["status"] == "healthy"
            assert health[2]["status"] == "degraded"
