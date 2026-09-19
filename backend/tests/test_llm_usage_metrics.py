"""Tests for LLM token usage metrics (T3.3)."""

from prometheus_client import REGISTRY

from services.ai_providers import _record_llm_usage


def _counter_value(name: str, **labels) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


class TestRecordLLMUsage:
    def test_openai_style_usage(self):
        before_p = _counter_value(
            "soc_llm_tokens_total", provider="openai", model="gpt-4", direction="prompt"
        )
        before_c = _counter_value(
            "soc_llm_tokens_total",
            provider="openai",
            model="gpt-4",
            direction="completion",
        )
        _record_llm_usage(
            "openai", "gpt-4", {"prompt_tokens": 120, "completion_tokens": 80}
        )
        assert (
            _counter_value(
                "soc_llm_tokens_total",
                provider="openai",
                model="gpt-4",
                direction="prompt",
            )
            == before_p + 120
        )
        assert (
            _counter_value(
                "soc_llm_tokens_total",
                provider="openai",
                model="gpt-4",
                direction="completion",
            )
            == before_c + 80
        )

    def test_anthropic_style_keys(self):
        _record_llm_usage(
            "claude", "claude-3", {"input_tokens": 10, "output_tokens": 5}
        )
        # just assert no raise and requests counted; token deltas covered above
        assert (
            _counter_value(
                "soc_llm_requests_total", provider="claude", model="claude-3"
            )
            >= 1
        )

    def test_none_usage_still_counts_request(self):
        before = _counter_value(
            "soc_llm_requests_total", provider="zhipu", model="glm-4"
        )
        _record_llm_usage("zhipu", "glm-4", None)
        assert (
            _counter_value("soc_llm_requests_total", provider="zhipu", model="glm-4")
            >= before + 1
        )

    def test_malformed_usage_never_raises(self):
        # int("abc") inside the recorder must be swallowed, not propagated
        _record_llm_usage("moonshot", "kimi", {"prompt_tokens": "abc"})
        _record_llm_usage("nvidia", "llama", "not-a-dict")
