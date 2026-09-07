"""
Comprehensive Unit Tests for TimelineService
Tests log timeline reconstruction, dual-engine IOC merging, impact analysis, threat intel enrichment, and markdown formatting.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.impact import ImpactAnalysis, Severity
from schemas.threat_intel import ThreatIntelAnalysis
from schemas.timeline import (
    IOCCount,
    IOCsFinal,
    IOCsLLM,
    IOCsLocal,
    SuspiciousEvent,
    TimelineEvent,
    TimelineResponse,
)
from services.timeline_service import TimelineService
from utils.ioc_extract import IOCs


@pytest.fixture
def mock_session():
    return AsyncMock(spec=AsyncSession)


def create_dummy_timeline_response(degraded=False) -> TimelineResponse:
    return TimelineResponse(
        timeline=[
            TimelineEvent(
                timestamp="2024-03-01T12:00:00Z",
                type="auth_failure",
                description="Failed SSH login from 192.168.1.100",
                key_fields={"src_ip": "192.168.1.100", "hostname": "web-server-01"},
            )
        ],
        suspicious_top5=[
            SuspiciousEvent(
                timestamp="2024-03-01T12:00:00Z",
                description="Repeated failed SSH logins",
                reasoning="Brute-force attack pattern detected",
                severity="high",
            )
        ],
        next_steps=["Check firewall rules", "Block attacker IP"],
        iocs=IOCsFinal(ips=["192.168.1.100"], domains=[], urls=[], hashes=[]),
        iocs_local=IOCsLocal(ips=[], domains=[], urls=[], hashes=[]),
        iocs_llm=IOCsLLM(ips=[], domains=[], urls=[], hashes=[]),
        ioc_count=IOCCount(ips=1, domains=0, urls=0, hashes=0, total=1),
        impact_analysis=ImpactAnalysis(
            affected_assets=[],
            business_impact="Low impact",
            risk_score=20,
            severity=Severity.low,
            containment_priority=[],
            recommended_next_queries=[],
        ),
        threat_intel=ThreatIntelAnalysis(
            provider="otx",
            disabled=False,
            degraded=False,
            skipped=False,
            items=[],
            filtered_items=[],
        ),
        request_id="req-123",
        model_used="test-llm",
        degraded=degraded,
        error_reason="Test error" if degraded else None,
    )


class TestTimelineServiceUnit:
    """Unit tests for TimelineService components."""

    def test_merge_iocs(self, mock_session):
        service = TimelineService(mock_session)
        dummy_res = create_dummy_timeline_response()
        local_iocs = IOCs(
            ips=["10.0.0.1", "192.168.1.100"],
            domains=["evil.com"],
            urls=["http://evil.com/malware.exe"],
            hashes=["d41d8cd98f00b204e9800998ecf8427e"],
        )

        merged = service._merge_iocs(dummy_res, local_iocs)
        assert "10.0.0.1" in merged.iocs.ips
        assert "192.168.1.100" in merged.iocs.ips
        assert merged.iocs.domains == ["evil.com"]
        assert merged.iocs.hashes == ["d41d8cd98f00b204e9800998ecf8427e"]
        assert merged.ioc_count.total == 5
        assert merged.iocs_local.ips == ["10.0.0.1", "192.168.1.100"]

    def test_format_as_markdown(self, mock_session):
        service = TimelineService(mock_session)
        dummy_res = create_dummy_timeline_response(degraded=True)

        md = service._format_as_markdown(dummy_res)
        assert "# Security Timeline" in md
        assert "**Total Events:** 1" in md
        assert "Failed SSH login" in md
        assert "Top 5 Suspicious Events" in md
        assert "Brute-force attack pattern" in md
        assert "Check firewall rules" in md
        assert "⚠️ Degraded mode: Test error" in md

    @pytest.mark.asyncio
    async def test_create_ioc_hits(self, mock_session):
        service = TimelineService(mock_session)
        service.ioc_hits_service = AsyncMock()

        local_iocs = IOCs(
            ips=["192.168.1.50"],
            domains=["phishing.com"],
            urls=["https://phishing.com/login"],
            hashes=["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
        )

        fake_asset = MagicMock()
        fake_asset.id = "asset-001"
        fake_asset.ip = "192.168.1.50"
        fake_asset.hostname = "srv-ldap"

        await service._create_ioc_hits(
            history_id="hist-999",
            local_iocs=local_iocs,
            affected_assets=[fake_asset],
        )

        assert service.ioc_hits_service.create_from_analysis.await_count == 4


@pytest.mark.asyncio
class TestTimelineServiceBuild:
    """Tests for the end-to-end build workflow."""

    async def test_build_success_with_history(self, mock_session):
        service = TimelineService(mock_session)
        service.history_service = AsyncMock()
        mock_history = MagicMock()
        mock_history.id = "hist-abc-123"
        service.history_service.create_history.return_value = mock_history

        dummy_llm_res = create_dummy_timeline_response(degraded=False)
        service.llm_service.generate_structured = AsyncMock(
            return_value=(dummy_llm_res, "test-model", False)
        )

        # Mock subservices
        service.asset_service = AsyncMock()
        service.asset_service.get_by_ips.return_value = []
        service.asset_service.get_by_hostnames.return_value = []

        service.impact_service = AsyncMock()
        mock_impact = MagicMock()
        mock_impact.model_dump.return_value = {
            "severity": "medium",
            "risk_score": 50,
            "business_impact": "Medium impact",
            "affected_assets": [],
            "containment_priority": [],
            "recommended_next_queries": [],
        }
        service.impact_service.analyze.return_value = mock_impact

        service.threat_intel_service = AsyncMock()
        mock_ti = MagicMock()
        mock_ti.model_dump.return_value = {
            "provider": "otx",
            "disabled": False,
            "degraded": False,
            "skipped": False,
            "items": [],
            "filtered_items": [],
        }
        service.threat_intel_service.enrich_iocs.return_value = mock_ti
        service.ioc_hits_service = AsyncMock()

        raw_log = "2024-03-01 12:00:00 [ALERT] SSH login failed for user admin from 192.168.1.100 host web-server-01"
        res = await service.build(raw_log=raw_log, log_type="linux", save_history=True)

        assert res.history_id == "hist-abc-123"
        assert res.degraded is False
        assert len(res.timeline) >= 1
        service.history_service.create_history.assert_awaited_once()

    async def test_build_degraded_mode(self, mock_session):
        service = TimelineService(mock_session)
        service.history_service = None  # no session/history

        dummy_llm_res = create_dummy_timeline_response(degraded=True)
        service.llm_service.generate_structured = AsyncMock(
            return_value=(dummy_llm_res, "fallback-model", True)
        )

        raw_log = "2024-03-01 12:05:00 [ERROR] Connection timed out"
        res = await service.build(raw_log=raw_log, log_type=None, save_history=False)

        assert res.degraded is True
        assert res.history_id is None
        assert res.impact_analysis.severity == Severity.low
