"""Pre-launch regression tests for the v0.9.4 schema / threat-intel changes.

Covers three risky, previously untested behaviour changes in the release batch:

1. ``IOCHitCreate.ioc_type`` / ``.source`` were relaxed from ``IOCType`` /
   ``IOCSource`` enums to bare ``str`` (enum validation removed at the edge).
2. ``ThreatIntelService.lookup`` was reordered: cache → internal IOC hits →
   external-provider-enabled check. This inverted the "external TI disabled"
   short circuit and broke 3 pre-existing tests.
3. ``AlertAnalysisRequest.raw_log`` became optional, with the router
   synthesising a log from title/severity/source/description.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from schemas.alert import AlertAnalysisRequest, RecommendedAction
from schemas.ioc_hit import IOCSource, IOCType
from schemas.threat_intel import Verdict

# --------------------------------------------------------------------------- #
# 1. IOC hit schema: enum validation removed
# --------------------------------------------------------------------------- #


class TestIOCHitSchemaValidation:
    def test_valid_enum_values_still_accepted(self):
        from schemas.ioc_hit import IOCHitCreate

        hit = IOCHitCreate(ioc_type="ip", ioc_value="8.8.8.8", source="local")
        assert hit.ioc_type == "ip"
        assert hit.source == "local"

    def test_enum_members_still_accepted(self):
        from schemas.ioc_hit import IOCHitCreate

        hit = IOCHitCreate(ioc_type=IOCType.domain, ioc_value="a.com", source=IOCSource.llm)
        assert hit.ioc_type is IOCType.domain or hit.ioc_type == "domain"

    def test_arbitrary_strings_accepted_characterisation(self):
        """DEFECT QA-007 (characterisation): enum validation was removed in v0.9.4.

        Any string is now persisted as ``ioc_type`` / ``source``. The API layer
        no longer rejects typos or hostile values at the boundary.
        """
        from schemas.ioc_hit import IOCHitCreate

        hit = IOCHitCreate(ioc_type="totally-bogus", ioc_value="x", source="<script>")
        assert hit.ioc_type == "totally-bogus"
        assert hit.source == "<script>"

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "DEFECT QA-007: ioc_type/source were relaxed from enums to str, so the "
            "request boundary no longer rejects unknown IOC types/sources."
        ),
    )
    def test_unknown_ioc_type_should_be_rejected(self):
        from schemas.ioc_hit import IOCHitCreate

        with pytest.raises(Exception):
            IOCHitCreate(ioc_type="totally-bogus", ioc_value="x", source="local")


# --------------------------------------------------------------------------- #
# 2. Threat intel lookup ordering
# --------------------------------------------------------------------------- #


def _ti_service(session=None):
    from services.threat_intel_service import ThreatIntelService

    service = ThreatIntelService(session or AsyncMock())
    service.repository = MagicMock()
    service.repository.get_by_ioc = AsyncMock(return_value=None)
    return service


def _allow_filter():
    decision = MagicMock()
    decision.allowed = True
    decision.reason = None
    return decision


def _ioc_hit(confidence=95, source="local", ioc_type="ip", notes=None, context="ctx"):
    hit = MagicMock()
    hit.confidence = confidence
    hit.source = source
    hit.ioc_type = ioc_type
    hit.notes = notes
    hit.context_snippet = context
    return hit


class TestThreatIntelLookupOrdering:
    async def test_cache_hit_short_circuits_before_ioc_hits(self):
        service = _ti_service()
        cached = MagicMock()
        cached.response_json = '{"verdict": "malicious", "score": 90}'
        cached.score = 90
        cached.pulse_count = 5
        cached.tags = '["c2"]'
        service.repository.get_by_ioc = AsyncMock(return_value=cached)

        with patch(
            "services.threat_intel_service.should_send_ioc_to_external_ti",
            return_value=_allow_filter(),
        ), patch(
            "repositories.ioc_hit_repository.IOCHitRepository"
        ) as repo_cls:
            repo_cls.return_value.list_by_ioc = AsyncMock(return_value=[])
            resp = await service.lookup("ip", "1.2.3.4")

        assert resp.cached is True
        assert resp.verdict == Verdict.malicious
        repo_cls.return_value.list_by_ioc.assert_not_called()

    async def test_internal_ioc_hit_returned_without_external_provider(self):
        service = _ti_service()
        is_enabled = AsyncMock(return_value=(True, None))

        with patch.object(service, "is_enabled", is_enabled), patch(
            "services.threat_intel_service.should_send_ioc_to_external_ti",
            return_value=_allow_filter(),
        ), patch("repositories.ioc_hit_repository.IOCHitRepository") as repo_cls:
            repo_cls.return_value.list_by_ioc = AsyncMock(
                return_value=[_ioc_hit(confidence=95)]
            )
            resp = await service.lookup("ip", "9.9.9.9")

        assert resp.verdict == Verdict.malicious
        assert resp.score == 95
        assert resp.provider == "local"
        # External provider was never consulted
        is_enabled.assert_not_called()

    async def test_confidence_thresholds_map_to_verdicts(self):
        cases = [(95, Verdict.malicious), (60, Verdict.suspicious), (10, Verdict.benign)]
        for confidence, expected in cases:
            service = _ti_service()
            with patch(
                "services.threat_intel_service.should_send_ioc_to_external_ti",
                return_value=_allow_filter(),
            ), patch("repositories.ioc_hit_repository.IOCHitRepository") as repo_cls:
                repo_cls.return_value.list_by_ioc = AsyncMock(
                    return_value=[_ioc_hit(confidence=confidence)]
                )
                resp = await service.lookup("ip", "5.5.5.5")
            assert resp.verdict is expected, f"confidence={confidence}"

    async def test_disabled_provider_still_reports_disabled_when_nothing_cached(self):
        service = _ti_service()
        is_enabled = AsyncMock(return_value=(False, "Disabled"))

        with patch.object(service, "is_enabled", is_enabled), patch(
            "services.threat_intel_service.should_send_ioc_to_external_ti",
            return_value=_allow_filter(),
        ), patch("repositories.ioc_hit_repository.IOCHitRepository") as repo_cls:
            repo_cls.return_value.list_by_ioc = AsyncMock(return_value=[])
            resp = await service.lookup("ip", "8.8.8.8")

        assert resp.disabled is True
        assert resp.error_reason == "Disabled"

    async def test_disabled_provider_is_masked_by_internal_ioc_hit(self):
        """DEFECT QA-002 (characterisation): the disabled short-circuit moved.

        With external TI disabled, an internal IOC hit now produces a
        ``disabled=False`` response, so the "external TI off" switch no longer
        guarantees "no threat-intel answer is returned".
        """
        service = _ti_service()
        is_enabled = AsyncMock(return_value=(False, "Disabled"))

        with patch.object(service, "is_enabled", is_enabled), patch(
            "services.threat_intel_service.should_send_ioc_to_external_ti",
            return_value=_allow_filter(),
        ), patch("repositories.ioc_hit_repository.IOCHitRepository") as repo_cls:
            repo_cls.return_value.list_by_ioc = AsyncMock(
                return_value=[_ioc_hit(confidence=90)]
            )
            resp = await service.lookup("ip", "8.8.8.8")

        assert resp.disabled is False
        assert resp.verdict == Verdict.malicious


# --------------------------------------------------------------------------- #
# 3. Alert analysis request: raw_log optional
# --------------------------------------------------------------------------- #


class TestAlertAnalysisRequest:
    def test_raw_log_is_now_optional(self):
        req = AlertAnalysisRequest()
        assert req.raw_log is None

    def test_raw_log_accepts_short_strings(self):
        """min_length=10 was dropped in v0.9.4; short logs are now allowed."""
        req = AlertAnalysisRequest(raw_log="short")
        assert req.raw_log == "short"

    def test_attribute_fields_accepted(self):
        req = AlertAnalysisRequest(
            title="Suspicious login", severity="high", source="wazuh"
        )
        assert req.title == "Suspicious login"
        assert req.severity == "high"

    def test_recommended_action_details_optional(self):
        action = RecommendedAction(action="Block IP", priority="high")
        assert action.details == ""
        assert action.verification == ""
        assert action.automated is False
        # NOTE (minor, QA-008): ``description`` stays None when ``details`` is
        # empty because model_post_init only mirrors *truthy* values. Consumers
        # must fall back to ``details or description or ""``.
        assert action.description is None

    def test_recommended_action_description_mirrors_details(self):
        action = RecommendedAction(action="Block IP", priority="high", details="do it")
        assert action.description == "do it"
