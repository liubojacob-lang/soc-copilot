"""Unit tests for AlertService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from schemas.alert import AlertAnalysisResponse
from services.alert_service import AlertService
from utils.ioc_extract import IOCs


class TestAlertServiceIOCExtraction:
    """Tests for IOC extraction and merging."""

    def test_merge_iocs_basic(self):
        """Test basic IOC merging."""
        service = AlertService(session=None)

        local_iocs = IOCs(
            ips=["192.168.1.1", "10.0.0.1"],
            domains=["evil.com"],
            urls=["http://malicious.com/payload"],
            hashes=["abc123"],
        )

        result = AlertAnalysisResponse(
            event_type="malware",
            severity="high",
            summary="Test",
            confidence=80,
            iocs={"ips": ["192.168.1.1"], "domains": ["another-evil.com"]},
            entities={"hosts": [], "users": [], "processes": []},
            evidence_points=["Test evidence"],
            recommended_actions=[],
            escalation_needed=False,
            degraded=False,
        )

        merged = service._merge_iocs(result, local_iocs)

        assert "192.168.1.1" in merged.iocs["ips"]
        assert "10.0.0.1" in merged.iocs["ips"]
        assert "evil.com" in merged.iocs["domains"]
        assert "another-evil.com" in merged.iocs["domains"]
        assert "abc123" in merged.iocs["hashes"]

    def test_merge_iocs_empty_local(self):
        """Test merging with empty local IOCs."""
        service = AlertService(session=None)

        local_iocs = IOCs(ips=[], domains=[], urls=[], hashes=[])

        result = AlertAnalysisResponse(
            event_type="scan",
            severity="low",
            summary="Test",
            confidence=50,
            iocs={"ips": ["1.1.1.1"], "domains": []},
            entities={"hosts": [], "users": [], "processes": []},
            evidence_points=[],
            recommended_actions=[],
            escalation_needed=False,
            degraded=False,
        )

        merged = service._merge_iocs(result, local_iocs)

        assert "1.1.1.1" in merged.iocs["ips"]

    def test_merge_iocs_local_precedence(self):
        """Test that local IOCs take precedence."""
        service = AlertService(session=None)

        local_iocs = IOCs(
            ips=["192.168.1.1"],
            domains=[],
            urls=[],
            hashes=[],
        )

        result = AlertAnalysisResponse(
            event_type="bruteforce",
            severity="medium",
            summary="Test",
            confidence=70,
            iocs={"ips": ["192.168.1.1", "10.0.0.1"]},
            entities={"hosts": [], "users": [], "processes": []},
            evidence_points=[],
            recommended_actions=[],
            escalation_needed=False,
            degraded=False,
        )

        merged = service._merge_iocs(result, local_iocs)

        assert "192.168.1.1" in merged.iocs["ips"]
        assert "10.0.0.1" in merged.iocs["ips"]


class TestAlertServiceMarkdownFormatting:
    """Tests for markdown formatting."""

    def test_format_as_markdown_basic(self):
        """Test basic markdown formatting."""
        service = AlertService(session=None)

        result = AlertAnalysisResponse(
            event_type="malware",
            severity="critical",
            summary="Malware detected on workstation",
            confidence=95,
            iocs={"ips": ["192.168.1.100"], "domains": ["evil.com"]},
            entities={
                "hosts": ["workstation-01"],
                "users": ["admin"],
                "processes": ["malware.exe"],
            },
            evidence_points=[
                "Suspicious process execution",
                "Network connection to C2",
            ],
            recommended_actions=[
                {
                    "action": "Isolate host",
                    "priority": "high",
                    "details": "Disconnect from network",
                    "verification": "Check network status",
                }
            ],
            escalation_needed=True,
            degraded=False,
        )

        markdown = service._format_as_markdown(result)

        assert "# Alert Analysis" in markdown
        assert "**Event Type:** malware" in markdown
        assert "**Severity:** critical" in markdown
        assert "**Confidence:** 95%" in markdown
        assert "Malware detected on workstation" in markdown
        assert "192.168.1.100" in markdown
        assert "evil.com" in markdown
        assert "workstation-01" in markdown
        assert "**Escalation Required:** Yes" in markdown

    def test_format_as_markdown_degraded(self):
        """Test markdown formatting with degraded mode."""
        service = AlertService(session=None)

        result = AlertAnalysisResponse(
            event_type="unknown",
            severity="low",
            summary="Analysis unavailable",
            confidence=0,
            iocs={"ips": [], "domains": []},
            entities={"hosts": [], "users": [], "processes": []},
            evidence_points=[],
            recommended_actions=[],
            escalation_needed=False,
            degraded=True,
            error_reason="LLM service unavailable",
        )

        markdown = service._format_as_markdown(result)

        assert "Degraded mode" in markdown
        assert "LLM service unavailable" in markdown


class TestAlertServiceAnalysis:
    """Tests for the analyze method."""

    @pytest.mark.asyncio
    async def test_analyze_with_session(self):
        """Test analysis with database session."""
        mock_session = AsyncMock()
        mock_history_service = AsyncMock()
        mock_history_service.create_history = AsyncMock(
            return_value=MagicMock(id="test-history-id")
        )

        with patch(
            "services.alert_service.HistoryService", return_value=mock_history_service
        ):
            with patch("services.alert_service.get_llm_retry_service") as mock_llm:
                mock_llm_service = AsyncMock()
                mock_llm_service.generate_structured = AsyncMock(
                    return_value=(
                        AlertAnalysisResponse(
                            event_type="scan",
                            severity="low",
                            summary="Port scan detected",
                            confidence=60,
                            iocs={"ips": ["192.168.1.1"], "domains": []},
                            entities={"hosts": [], "users": [], "processes": []},
                            evidence_points=["Port scan activity"],
                            recommended_actions=[],
                            escalation_needed=False,
                            degraded=False,
                        ),
                        "test-model",
                        False,
                    )
                )
                mock_llm.return_value = mock_llm_service

                service = AlertService(session=mock_session)
                result = await service.analyze(
                    "Port scan from 192.168.1.1", save_history=False
                )

                assert result.event_type == "scan"
                assert result.severity == "low"

    @pytest.mark.asyncio
    async def test_analyze_without_session(self):
        """Test analysis without database session."""
        with patch("services.alert_service.get_llm_retry_service") as mock_llm:
            mock_llm_service = AsyncMock()
            mock_llm_service.generate_structured = AsyncMock(
                return_value=(
                    AlertAnalysisResponse(
                        event_type="phishing",
                        severity="medium",
                        summary="Phishing email detected",
                        confidence=75,
                        iocs={"ips": [], "domains": ["phishing.com"]},
                        entities={
                            "hosts": [],
                            "users": ["victim@company.com"],
                            "processes": [],
                        },
                        evidence_points=["Suspicious email link"],
                        recommended_actions=[],
                        escalation_needed=False,
                        degraded=False,
                    ),
                    "test-model",
                    False,
                )
            )
            mock_llm.return_value = mock_llm_service

            service = AlertService(session=None)
            result = await service.analyze("Phishing email from phishing.com")

            assert result.event_type == "phishing"
            assert result.severity == "medium"

    @pytest.mark.asyncio
    async def test_analyze_degraded_mode(self):
        """Test analysis in degraded mode."""
        with patch("services.alert_service.get_llm_retry_service") as mock_llm:
            mock_llm_service = AsyncMock()
            mock_llm_service.generate_structured = AsyncMock(
                return_value=(
                    AlertAnalysisResponse(
                        event_type="unknown",
                        severity="low",
                        summary="Degraded analysis",
                        confidence=0,
                        iocs={"ips": [], "domains": []},
                        entities={"hosts": [], "users": [], "processes": []},
                        evidence_points=[],
                        recommended_actions=[],
                        escalation_needed=False,
                        degraded=True,
                        error_reason="Service degraded",
                    ),
                    "fallback",
                    True,
                )
            )
            mock_llm.return_value = mock_llm_service

            service = AlertService(session=None)
            result = await service.analyze("Test log")

            assert result.degraded is True
            assert result.error_reason == "Service degraded"


class TestAlertServiceIOCCount:
    """Tests for IOC count functionality."""

    def test_ioc_count_in_response(self):
        """Test that IOC count is included in response."""
        service = AlertService(session=None)

        local_iocs = IOCs(
            ips=["1.1.1.1", "2.2.2.2"],
            domains=["a.com", "b.com", "c.com"],
            urls=["http://x.com/1"],
            hashes=["hash1", "hash2"],
        )

        result = AlertAnalysisResponse(
            event_type="malware",
            severity="high",
            summary="Test",
            confidence=80,
            iocs={},
            entities={"hosts": [], "users": [], "processes": []},
            evidence_points=[],
            recommended_actions=[],
            escalation_needed=False,
            degraded=False,
        )

        merged = service._merge_iocs(result, local_iocs)

        assert merged.ioc_count["ips"] == 2
        assert merged.ioc_count["domains"] == 3
        assert merged.ioc_count["urls"] == 1
        assert merged.ioc_count["hashes"] == 2
        assert merged.ioc_count["total"] == 8
