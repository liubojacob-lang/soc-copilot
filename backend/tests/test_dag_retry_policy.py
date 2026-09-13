"""Unit tests for the DAG retry policy and retry executor."""

import asyncio

import pytest

from playbook_engine.dag.retry_policy import (
    RetryExecutor,
    RetryPolicy,
    RetryResult,
)

pytestmark = [pytest.mark.unit]


class TestRetryPolicy:
    def test_defaults(self):
        policy = RetryPolicy()
        assert policy.max_attempts == 3
        assert policy.backoff_base == 1.0
        assert policy.backoff_max == 60.0
        assert policy.timeout == 300

    def test_backoff_doubles_without_jitter(self):
        policy = RetryPolicy(backoff_base=1.0, backoff_max=60.0, jitter_enabled=False)
        assert policy.calculate_backoff(1) == 1.0
        assert policy.calculate_backoff(2) == 2.0
        assert policy.calculate_backoff(3) == 4.0

    def test_backoff_caps_at_max(self):
        policy = RetryPolicy(backoff_base=10.0, backoff_max=20.0, jitter_enabled=False)
        assert policy.calculate_backoff(5) == 20.0

    def test_backoff_clamps_attempt_below_one(self):
        policy = RetryPolicy(backoff_base=1.0, jitter_enabled=False)
        assert policy.calculate_backoff(0) == 1.0
        assert policy.calculate_backoff(-5) == 1.0

    def test_backoff_jitter_stays_within_bounds(self):
        policy = RetryPolicy(backoff_base=10.0, backoff_max=60.0, jitter_enabled=True)
        for _ in range(20):
            delay = policy.calculate_backoff(1)
            assert 10.0 <= delay <= 11.0

    def test_should_retry(self):
        policy = RetryPolicy(max_attempts=3)
        assert policy.should_retry(1) is True
        assert policy.should_retry(2) is True
        assert policy.should_retry(3) is False

    def test_get_timeout_seconds(self):
        assert RetryPolicy(timeout=42).get_timeout_seconds() == 42


class TestRetryExecutor:
    async def test_success_on_first_attempt(self):
        executor = RetryExecutor(RetryPolicy(max_attempts=3))
        calls = 0

        async def func():
            nonlocal calls
            calls += 1
            return "ok"

        result = await executor.execute_with_retry(func)
        assert isinstance(result, RetryResult)
        assert result.success is True
        assert result.attempt_number == 1
        assert result.error is None
        assert calls == 1

    async def test_retries_then_succeeds_without_real_sleep(self):
        policy = RetryPolicy(
            max_attempts=3, backoff_base=0.0, jitter_enabled=False, timeout=5
        )
        executor = RetryExecutor(policy)
        attempts = 0

        async def flaky():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("transient")
            return "ok"

        result = await executor.execute_with_retry(flaky)
        assert result.success is True
        assert result.attempt_number == 3
        assert attempts == 3

    async def test_exhaustion_returns_last_error(self):
        policy = RetryPolicy(
            max_attempts=2, backoff_base=0.0, jitter_enabled=False, timeout=5
        )
        executor = RetryExecutor(policy)
        attempts = 0

        async def always_fails():
            nonlocal attempts
            attempts += 1
            raise RuntimeError("boom")

        result = await executor.execute_with_retry(always_fails)
        assert result.success is False
        assert result.error == "boom"
        # Both attempts ran; note the executor under-reports the attempt
        # count by one on exhaustion (returns attempt_number - 1).
        assert attempts == 2
        assert result.attempt_number == 1

    async def test_timeout_is_retried_and_reported(self):
        policy = RetryPolicy(
            max_attempts=2, backoff_base=0.0, jitter_enabled=False, timeout=0
        )
        executor = RetryExecutor(policy)

        async def too_slow():
            await asyncio.sleep(5)

        result = await executor.execute_with_retry(too_slow)
        assert result.success is False
        # Attempt count is under-reported by one on exhaustion (see above).
        assert result.attempt_number == 1
        assert result.error == "Timeout after 0s"

    def test_get_next_retry_time(self):
        executor = RetryExecutor(
            RetryPolicy(max_attempts=3, backoff_base=1.0, jitter_enabled=False)
        )
        assert executor.get_next_retry_time(1) is not None
        assert executor.get_next_retry_time(3) is None
