"""Pre-launch regression tests for the v0.9.4 schema / threat-intel changes.

Covers three risky, previously untested behaviour changes in the release batch:

1. ``IOCHitCreate.ioc_type`` / ``.source`` were relaxed from ``IOCType`` /
   ``IOCSource`` enums to bare ``str`` (enum validation removed at the edge).
2. ``ThreatIntelService.lookup`` ordering. G8 (0112966) fixed DEFECT QA-002 by
   putting the ``is_enabled()`` short circuit first, so the contract asserted
   here is: compliance filter → ``is_enabled()`` → cache → internal IOC hits →
   external provider. Every test drives ``is_enabled`` explicitly because
   ``settings.allow_external_ti`` defaults to False and the ambient value
   differs between a developer laptop with ``.env`` and CI without one.
3. ``AlertAnalysisRequest.raw_log`` became optional, with the router
   synthesising a log from title/severity/source/description.
"""

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

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

        hit = IOCHitCreate(
            ioc_type=IOCType.domain, ioc_value="a.com", source=IOCSource.llm
        )
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

        with pytest.raises(ValidationError):
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


class _LookupPatches:
    """Context manager patching the three collaborators ``lookup()`` touches.

    ``IOCHitRepository`` is patched on the *service* module because G8 promoted
    the import to top level there; patching the defining module no longer
    intercepts the call and lets the repository hit the mock session.
    """

    def __init__(self, service, enabled=(True, None), hits=None):
        self.service = service
        self.enabled = enabled
        self.hits = hits if hits is not None else []

    def __enter__(self):
        self._stack = ExitStack()
        self._stack.enter_context(
            patch(
                "services.threat_intel_service.should_send_ioc_to_external_ti",
                return_value=_allow_filter(),
            )
        )
        self.is_enabled = self._stack.enter_context(
            patch.object(
                self.service, "is_enabled", AsyncMock(return_value=self.enabled)
            )
        )
        repo_cls = self._stack.enter_context(
            patch("services.threat_intel_service.IOCHitRepository")
        )
        self.list_by_ioc = repo_cls.return_value.list_by_ioc = AsyncMock(
            return_value=self.hits
        )
        return self

    def __exit__(self, *exc):
        self._stack.close()
        return False


class TestThreatIntelLookupOrdering:
    async def test_cache_hit_short_circuits_before_ioc_hits(self):
        service = _ti_service()
        cached = MagicMock()
        cached.response_json = '{"verdict": "malicious", "score": 90}'
        cached.score = 90
        cached.pulse_count = 5
        cached.tags = '["c2"]'
        service.repository.get_by_ioc = AsyncMock(return_value=cached)

        with _LookupPatches(service) as patches:
            resp = await service.lookup("ip", "1.2.3.4")

        assert resp.cached is True
        assert resp.verdict == Verdict.malicious
        patches.list_by_ioc.assert_not_called()

    async def test_internal_ioc_hit_returned_without_external_provider(self):
        service = _ti_service()

        with _LookupPatches(service, hits=[_ioc_hit(confidence=95)]) as patches:
            resp = await service.lookup("ip", "9.9.9.9")

        assert resp.verdict == Verdict.malicious
        assert resp.score == 95
        assert resp.provider == "local"
        # G8 made is_enabled() the gate for the whole lookup, so it is consulted
        # before the cache and the internal IOC hits.
        patches.is_enabled.assert_awaited_once()

    async def test_confidence_thresholds_map_to_verdicts(self):
        cases = [
            (95, Verdict.malicious),
            (60, Verdict.suspicious),
            (10, Verdict.benign),
        ]
        for confidence, expected in cases:
            service = _ti_service()
            with _LookupPatches(service, hits=[_ioc_hit(confidence=confidence)]):
                resp = await service.lookup("ip", "5.5.5.5")
            assert resp.verdict is expected, f"confidence={confidence}"

    async def test_disabled_provider_still_reports_disabled_when_nothing_cached(self):
        service = _ti_service()

        with _LookupPatches(service, enabled=(False, "Disabled")) as patches:
            resp = await service.lookup("ip", "8.8.8.8")

        assert resp.disabled is True
        assert resp.error_reason == "Disabled"
        patches.list_by_ioc.assert_not_called()

    async def test_disabled_short_circuits_before_internal_ioc_hits(self):
        """DEFECT QA-002, closed by G8: external TI off means no verdict at all.

        Internal IOC hits are no longer consulted once ``is_enabled()`` reports
        disabled, so the switch does guarantee that no threat-intel answer is
        returned.
        """
        service = _ti_service()

        with _LookupPatches(
            service, enabled=(False, "Disabled"), hits=[_ioc_hit(confidence=90)]
        ) as patches:
            resp = await service.lookup("ip", "8.8.8.8")

        assert resp.disabled is True
        assert resp.verdict is Verdict.unknown
        patches.list_by_ioc.assert_not_called()


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
