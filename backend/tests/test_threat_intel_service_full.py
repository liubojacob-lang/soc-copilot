"""
Comprehensive Unit Tests for ThreatIntelService
Covers compliance filtering, caching, OTX lookups, bulk lookups, and alert enrichment.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.threat_intel import ThreatIntelResponse, Verdict
from services.threat_intel_service import (
    ThreatIntelService,
    _parse_blocked_tlds,
    _parse_internal_domains,
    get_degraded_threat_intel,
)


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


class TestThreatIntelHelpers:
    """Test helper functions and config parsing."""

    def test_parse_internal_domains(self):
        with patch("services.threat_intel_service.settings") as mock_settings:
            mock_settings.ti_internal_domain_suffixes = "corp.local, internal.net,  "
            domains = _parse_internal_domains()
            assert domains == ["corp.local", "internal.net"]

            mock_settings.ti_internal_domain_suffixes = ""
            assert _parse_internal_domains() == []

    def test_parse_blocked_tlds(self):
        with patch("services.threat_intel_service.settings") as mock_settings:
            mock_settings.ti_blocked_tlds = ".onion, .local"
            tlds = _parse_blocked_tlds()
            assert tlds == [".onion", ".local"]

            mock_settings.ti_blocked_tlds = ""
            assert _parse_blocked_tlds() == []

    def test_get_degraded_threat_intel(self):
        degraded = get_degraded_threat_intel()
        assert degraded.degraded is True
        assert "degraded mode" in degraded.error_reason
        assert degraded.items == []


@pytest.mark.asyncio
class TestThreatIntelServiceIsEnabled:
    """Test is_enabled check under various configuration states."""

    async def test_is_enabled_when_disabled_by_config(self, mock_session):
        service = ThreatIntelService(mock_session)
        with patch("services.threat_intel_service.settings") as mock_settings:
            mock_settings.allow_external_ti = False
            enabled, reason = await service.is_enabled()
            assert enabled is False
            assert "disabled by configuration" in reason

    async def test_is_enabled_when_missing_api_key(self, mock_session):
        service = ThreatIntelService(mock_session)
        with patch("services.threat_intel_service.settings") as mock_settings:
            mock_settings.allow_external_ti = True
            mock_settings.otx_api_key = ""
            enabled, reason = await service.is_enabled()
            assert enabled is False
            assert "API key not configured" in reason

    async def test_is_enabled_success(self, mock_session):
        service = ThreatIntelService(mock_session)
        with patch("services.threat_intel_service.settings") as mock_settings:
            mock_settings.allow_external_ti = True
            # Dummy key generated at runtime (no literal in source)
            mock_settings.otx_api_key = "test-" + uuid.uuid4().hex
            enabled, reason = await service.is_enabled()
            assert enabled is True
            assert reason is None


@pytest.mark.asyncio
class TestThreatIntelServiceLookup:
    """Test single IOC lookup with filtering, caching, and external calls."""

    async def test_lookup_filtered_by_compliance(self, mock_session):
        """Private IP should be blocked by compliance filter."""
        service = ThreatIntelService(mock_session)
        with patch("services.threat_intel_service.settings") as mock_settings:
            mock_settings.ti_allow_private_ip = False
            mock_settings.ti_allow_url_with_private_host = False

            resp = await service.lookup("ip", "192.168.1.50")
            assert resp.verdict == Verdict.unknown
            assert resp.skipped_reason is not None
            assert resp.disabled is False
            assert resp.degraded is False

    async def test_lookup_disabled(self, mock_session):
        service = ThreatIntelService(mock_session)
        with patch.object(service, "is_enabled", AsyncMock(return_value=(False, "Disabled"))):
            with patch("services.threat_intel_service.should_send_ioc_to_external_ti") as mock_filter:
                mock_decision = MagicMock()
                mock_decision.allowed = True
                mock_filter.return_value = mock_decision

                resp = await service.lookup("ip", "8.8.8.8")
                assert resp.disabled is True
                assert resp.error_reason == "Disabled"

    async def test_lookup_cached_hit(self, mock_session):
        service = ThreatIntelService(mock_session)
        with patch.object(service, "is_enabled", AsyncMock(return_value=(True, None))):
            with patch("services.threat_intel_service.should_send_ioc_to_external_ti") as mock_filter:
                mock_decision = MagicMock()
                mock_decision.allowed = True
                mock_filter.return_value = mock_decision

                # Mock cached record in repository
                cached_mock = MagicMock()
                cached_mock.response_json = '{"verdict": "malicious", "score": 90}'
                cached_mock.score = 90
                cached_mock.pulse_count = 5
                cached_mock.tags = '["c2", "ransomware"]'
                service.repository.get_by_ioc = AsyncMock(return_value=cached_mock)

                resp = await service.lookup("ip", "1.2.3.4")
                assert resp.cached is True
                assert resp.verdict == Verdict.malicious
                assert resp.score == 90
                assert resp.tags == ["c2", "ransomware"]

    async def test_lookup_otx_success(self, mock_session):
        service = ThreatIntelService(mock_session)
        with patch.object(service, "is_enabled", AsyncMock(return_value=(True, None))):
            with patch("services.threat_intel_service.should_send_ioc_to_external_ti") as mock_filter:
                mock_decision = MagicMock()
                mock_decision.allowed = True
                mock_filter.return_value = mock_decision

                service.repository.get_by_ioc = AsyncMock(return_value=None)
                service.repository.create = AsyncMock()

                # Patch IOCHitRepository so internal-hit DB path doesn't touch the mock session
                with patch(
                    "services.threat_intel_service.IOCHitRepository"
                ) as mock_ioc_hit_repo_cls:
                    mock_ioc_hit_repo_cls.return_value.list_by_ioc = AsyncMock(return_value=[])

                    mock_client = MagicMock()
                    with patch.object(service, "_get_otx_client", return_value=mock_client):
                        with patch.object(
                            service,
                            "_lookup_otx",
                            AsyncMock(return_value={
                                "verdict": "suspicious",
                                "score": 65,
                                "pulse_count": 2,
                                "tags": ["phishing"],
                                "references": ["https://otx.alienvault.com"],
                                "raw": {},
                            }),
                        ):
                            resp = await service.lookup("domain", "suspicious-bank.com")
                            assert resp.cached is False
                            assert resp.verdict == Verdict.suspicious
                            assert resp.score == 65
                            assert resp.tags == ["phishing"]
                            service.repository.create.assert_awaited_once()

    async def test_lookup_otx_exception_degraded(self, mock_session):
        service = ThreatIntelService(mock_session)
        with patch.object(service, "is_enabled", AsyncMock(return_value=(True, None))):
            with patch("services.threat_intel_service.should_send_ioc_to_external_ti") as mock_filter:
                mock_decision = MagicMock()
                mock_decision.allowed = True
                mock_filter.return_value = mock_decision

                service.repository.get_by_ioc = AsyncMock(return_value=None)

                # Patch IOCHitRepository so internal-hit DB path doesn't touch the mock session
                with patch(
                    "services.threat_intel_service.IOCHitRepository"
                ) as mock_ioc_hit_repo_cls:
                    mock_ioc_hit_repo_cls.return_value.list_by_ioc = AsyncMock(return_value=[])

                    mock_client = MagicMock()
                    with patch.object(service, "_get_otx_client", return_value=mock_client):
                        with patch.object(
                            service,
                            "_lookup_otx",
                            AsyncMock(side_effect=RuntimeError("OTX API 503 Service Unavailable")),
                        ):
                            resp = await service.lookup("hash", "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
                            assert resp.degraded is True
                            assert "503" in resp.error_reason


@pytest.mark.asyncio
class TestThreatIntelServiceBulkAndEnrich:
    """Test bulk lookup and alert enrichment routines."""

    async def test_bulk_lookup_disabled(self, mock_session):
        service = ThreatIntelService(mock_session)
        with patch.object(service, "is_enabled", AsyncMock(return_value=(False, "Disabled"))):
            resp = await service.bulk_lookup([{"ioc_type": "ip", "ioc_value": "8.8.8.8"}])
            assert resp.disabled is True
            assert resp.results == []

    async def test_bulk_lookup_with_filtered_and_rate_limited(self, mock_session):
        service = ThreatIntelService(mock_session)
        with patch.object(service, "is_enabled", AsyncMock(return_value=(True, None))):
            with patch("services.threat_intel_service.settings") as mock_settings:
                mock_settings.ti_allow_private_ip = False
                mock_settings.ti_allow_url_with_private_host = False
                mock_settings.ti_max_iocs_per_request = 1  # only allow 1, rest rate-limited

                fake_res = ThreatIntelResponse(
                    request_id="test",
                    provider="otx",
                    disabled=False,
                    cached=False,
                    degraded=False,
                    ioc_type="ip",
                    ioc_value="8.8.8.8",
                    verdict=Verdict.benign,
                    score=0,
                    pulse_count=0,
                    tags=[],
                    references=[],
                    raw={},
                )
                with patch.object(service, "lookup", AsyncMock(return_value=fake_res)):
                    items = [
                        {"ioc_type": "ip", "ioc_value": "192.168.1.1"},  # filtered compliance
                        {"ioc_type": "ip", "ioc_value": "8.8.8.8"},      # processed
                        {"ioc_type": "domain", "ioc_value": "example.com"}, # rate-limited
                    ]
                    bulk_resp = await service.bulk_lookup(items)

                    assert bulk_resp.filtered_count == 1
                    assert bulk_resp.filtered_items[0].ioc_value == "192.168.1.1"
                    assert len(bulk_resp.results) == 1
                    assert bulk_resp.skipped_count == 1
                    assert bulk_resp.skipped_items[0].skipped_reason == "rate_limit"

    async def test_enrich_iocs_disabled(self, mock_session):
        service = ThreatIntelService(mock_session)
        with patch.object(service, "is_enabled", AsyncMock(return_value=(False, "Disabled"))):
            analysis = await service.enrich_iocs({"ips": ["8.8.8.8"]})
            assert analysis.disabled is True
            assert analysis.items == []

    async def test_enrich_iocs_success(self, mock_session):
        service = ThreatIntelService(mock_session)
        with patch.object(service, "is_enabled", AsyncMock(return_value=(True, None))):
            fake_bulk = MagicMock()
            fake_bulk.results = [
                ThreatIntelResponse(
                    request_id="test-1",
                    provider="otx",
                    disabled=False,
                    cached=False,
                    degraded=False,
                    ioc_type="ip",
                    ioc_value="8.8.8.8",
                    verdict=Verdict.benign,
                    score=10,
                    pulse_count=0,
                    tags=[],
                    references=[],
                    raw={},
                )
            ]
            fake_bulk.filtered_items = []
            with patch.object(service, "bulk_lookup", AsyncMock(return_value=fake_bulk)):
                analysis = await service.enrich_iocs({
                    "ips": ["8.8.8.8"],
                    "domains": ["safe.com"],
                    "other": ["ignore_me"],
                })
                assert analysis.disabled is False
                assert len(analysis.items) == 1
                assert analysis.items[0].ioc_value == "8.8.8.8"
