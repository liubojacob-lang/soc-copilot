"""Unit tests for EnhancedAIService — P0-2 regression coverage.

Covers the two methods added to repair the AttributeError that broke the
LLM success path for AlertService / TimelineService / ReportService /
AITaskService: ``get_model_name`` and ``generate``.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.ai_service_enhanced import EnhancedAIService


@pytest.fixture
def service_with_mock_llm():
    """Build an EnhancedAIService with a mocked LLM provider (no real API call)."""
    with patch.object(EnhancedAIService, "_init_llm", lambda self: None):
        svc = EnhancedAIService()
    svc.llm = MagicMock()
    svc.llm.model = "glm-4-test"
    svc._initialized = True
    return svc


class TestGetModelName:
    """get_model_name must never raise, even in degraded/uninitialised states."""

    def test_returns_provider_model_when_initialised(self, service_with_mock_llm):
        assert service_with_mock_llm.get_model_name() == "glm-4-test"

    def test_falls_back_to_settings_provider_when_llm_is_none(self):
        with patch.object(EnhancedAIService, "_init_llm", lambda self: None):
            svc = EnhancedAIService()
        svc.llm = None
        # Should fall back to settings.ai_provider, not raise
        name = svc.get_model_name()
        assert isinstance(name, str)
        assert len(name) > 0

    def test_falls_back_when_model_attr_missing(self):
        with patch.object(EnhancedAIService, "_init_llm", lambda self: None):
            svc = EnhancedAIService()
        svc.llm = MagicMock(spec=[])  # no .model attribute
        name = svc.get_model_name()
        assert isinstance(name, str)


class TestGenerate:
    """generate() returns raw model text and exercises the LLM provider."""

    @pytest.mark.asyncio
    async def test_generate_returns_content(self, service_with_mock_llm):
        service_with_mock_llm.llm.chat_completion = AsyncMock(
            return_value="analysis complete"
        )
        result = await service_with_mock_llm.generate("explain this alert")
        assert result == "analysis complete"
        # Verify provider was called with the expected message shape
        call_kwargs = service_with_mock_llm.llm.chat_completion.call_args
        messages = call_kwargs.kwargs["messages"]
        assert any(m["content"] == "explain this alert" for m in messages)

    @pytest.mark.asyncio
    async def test_generate_raises_when_uninitialised(self):
        with patch.object(EnhancedAIService, "_init_llm", lambda self: None):
            svc = EnhancedAIService()
        svc.llm = None
        with pytest.raises(ValueError, match="not initialized"):
            await svc.generate("anything")

    @pytest.mark.asyncio
    async def test_generate_passes_custom_system_prompt(self, service_with_mock_llm):
        service_with_mock_llm.llm.chat_completion = AsyncMock(return_value="ok")
        await service_with_mock_llm.generate("prompt", system_prompt="custom system")
        messages = service_with_mock_llm.llm.chat_completion.call_args.kwargs[
            "messages"
        ]
        assert messages[0] == {"role": "system", "content": "custom system"}

    @pytest.mark.asyncio
    async def test_analyze_alert_activates_fallback_on_failure(self, service_with_mock_llm):
        service_with_mock_llm.llm.chat_completion = AsyncMock(side_effect=RuntimeError("API Quota exceeded"))
        alert = {
            "title": "Port scan reconnaissance activity",
            "description": "Nmap scan from 192.168.1.50",
            "severity": "high",
            "source_ip": "192.168.1.50",
            "alert_type": "reconnaissance"
        }
        res = await service_with_mock_llm.analyze_alert(alert)
        assert "[Degraded Mode]" in res.summary
        assert res.confidence == 0.6
        assert len(res.recommendations) > 0
        assert "T1046 - Network Service Discovery" in res.attack_techniques
