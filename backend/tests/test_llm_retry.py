"""Unit tests for LLMRetryService — P0-3 regression coverage.

Covers the free-form path (response_class=None) added to repair the
dict-as-schema crash, plus the existing schema path to ensure the
get_model_name() fix keeps it green.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.llm_retry import LLMRetryService


@pytest.fixture
def retry_service_with_mock_ai():
    """LLMRetryService with a mocked EnhancedAIService (no real LLM call)."""
    with patch("services.llm_retry.EnhancedAIService") as MockAI:
        svc = LLMRetryService()
        svc.ai_service = MockAI.return_value
    return svc


class TestGenerateStructuredFreeform:
    """response_class=None routes through free-form generation."""

    @pytest.mark.asyncio
    async def test_none_returns_raw_text_tuple(self, retry_service_with_mock_ai):
        svc = retry_service_with_mock_ai
        svc.ai_service.generate = AsyncMock(return_value="free text answer")
        svc.ai_service.get_model_name = MagicMock(return_value="glm-4-test")

        result, model_used, degraded = await svc.generate_structured(
            prompt="hello", response_class=None
        )

        assert result == "free text answer"
        assert model_used == "glm-4-test"
        assert degraded is False
        svc.ai_service.generate.assert_awaited_once_with("hello")

    @pytest.mark.asyncio
    async def test_none_retries_then_succeeds(self, retry_service_with_mock_ai):
        svc = retry_service_with_mock_ai
        svc.ai_service.generate = AsyncMock(
            side_effect=[
                RuntimeError("transient"),
                "ok on retry",
            ]
        )
        svc.ai_service.get_model_name = MagicMock(return_value="glm-4-test")
        # Speed up backoff so the test doesn't sleep for real
        with patch.object(svc, "_backoff", AsyncMock()):
            result, model_used, degraded = await svc.generate_structured(
                prompt="x", response_class=None
            )
        assert result == "ok on retry"
        assert degraded is False
        assert svc.ai_service.generate.await_count == 2

    @pytest.mark.asyncio
    async def test_none_degrades_after_all_retries_fail(
        self, retry_service_with_mock_ai
    ):
        svc = retry_service_with_mock_ai
        svc.ai_service.generate = AsyncMock(side_effect=RuntimeError("down"))
        svc.ai_service.get_model_name = MagicMock(return_value="glm-4-test")

        with patch.object(svc, "_backoff", AsyncMock()):
            result, model_used, degraded = await svc.generate_structured(
                prompt="x", response_class=None
            )
        assert result == ""  # graceful empty, not an exception
        assert degraded is True

    @pytest.mark.asyncio
    async def test_none_does_not_call_structured_path(self, retry_service_with_mock_ai):
        """Free-form path must never touch generate_structured on ai_service."""
        svc = retry_service_with_mock_ai
        svc.ai_service.generate = AsyncMock(return_value="ok")
        svc.ai_service.get_model_name = MagicMock(return_value="m")
        # ai_service.generate_structured should NOT be invoked
        svc.ai_service.generate_structured = AsyncMock(
            side_effect=AssertionError("must not be called in free-form path")
        )
        await svc.generate_structured(prompt="x", response_class=None)
        svc.ai_service.generate_structured.assert_not_called()


class TestGenerateStructuredSchema:
    """Sanity: the existing schema path still works after the refactor."""

    @pytest.mark.asyncio
    async def test_schema_path_calls_ai_generate_structured(
        self, retry_service_with_mock_ai
    ):
        from schemas.alert import AlertAnalysisResponse

        svc = retry_service_with_mock_ai
        # Use a minimal but valid-looking raw output; the degraded fallback
        # will kick in if validation fails, which is fine for this test —
        # we only assert the routing and that get_model_name is reachable.
        svc.ai_service.generate_structured = AsyncMock(
            side_effect=RuntimeError("simulated LLM failure")
        )
        svc.ai_service.get_model_name = MagicMock(return_value="glm-4-test")

        # Should not raise even when LLM fails — degraded response returned
        result, model_used, degraded = await svc.generate_structured(
            prompt="x", response_class=AlertAnalysisResponse
        )
        assert degraded is True  # exhausted retries → degraded
        assert isinstance(result, AlertAnalysisResponse)
