"""Retry policy with exponential backoff for DAG nodes."""

import asyncio
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass
class RetryPolicy:
    """Configuration for retrying failed node executions.

    Attributes:
        max_attempts: Maximum number of retry attempts (including initial)
        backoff_base: Base multiplier for exponential backoff in seconds
        backoff_max: Maximum backoff time in seconds
        timeout: Per-attempt timeout in seconds
        jitter_enabled: Whether to add random jitter to backoff
    """

    max_attempts: int = 3
    backoff_base: float = 1.0
    backoff_max: float = 60.0
    timeout: int = 300
    jitter_enabled: bool = True

    def calculate_backoff(self, attempt_number: int) -> float:
        """Calculate exponential backoff delay for an attempt.

        Args:
            attempt_number: The attempt number (1-indexed)

        Returns:
            Delay in seconds before the next retry
        """
        if attempt_number < 1:
            attempt_number = 1

        # Exponential backoff: base * 2^(attempt - 1)
        delay = self.backoff_base * (2 ** (attempt_number - 1))

        # Cap at maximum
        delay = min(delay, self.backoff_max)

        # Add jitter to prevent thundering herd
        if self.jitter_enabled:
            jitter = random.uniform(0, delay * 0.1)  # Up to 10% jitter
            delay += jitter

        return delay

    def should_retry(self, attempt_number: int) -> bool:
        """Check if another retry attempt should be made.

        Args:
            attempt_number: The attempt number (1-indexed)

        Returns:
            True if should retry, False otherwise
        """
        return attempt_number < self.max_attempts

    def get_timeout_seconds(self) -> int:
        """Get the per-attempt timeout in seconds.

        Returns:
            Timeout in seconds
        """
        return self.timeout


@dataclass
class RetryResult:
    """Result of a retry attempt.

    Attributes:
        success: Whether the attempt succeeded
        attempt_number: Which attempt this was (1-indexed)
        error: Error message if failed
        next_retry_at: When the next retry should occur (if applicable)
    """

    success: bool
    attempt_number: int
    error: str | None = None
    next_retry_at: datetime | None = None


class RetryExecutor:
    """Executor for handling retries with exponential backoff."""

    def __init__(self, policy: RetryPolicy):
        """Initialize the retry executor.

        Args:
            policy: Retry policy configuration
        """
        self.policy = policy

    async def execute_with_retry(self, func, *args, **kwargs) -> RetryResult:
        """Execute a function with retry policy.

        Args:
            func: Async function to execute
            *args: Positional arguments to pass to func
            **kwargs: Keyword arguments to pass to func

        Returns:
            RetryResult with execution outcome
        """
        attempt_number = 1
        last_error = None

        while attempt_number <= self.policy.max_attempts:
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    func(*args, **kwargs), timeout=self.policy.get_timeout_seconds()
                )

                return RetryResult(
                    success=True,
                    attempt_number=attempt_number,
                )

            except TimeoutError:
                last_error = f"Timeout after {self.policy.timeout}s"
            except Exception as e:
                last_error = str(e)

            # Check if we should retry
            if not self.policy.should_retry(attempt_number):
                break

            # Calculate backoff and wait
            backoff = self.policy.calculate_backoff(attempt_number)
            next_retry_at = datetime.now(UTC) + timedelta(seconds=backoff)

            attempt_number += 1

            # Wait before retry (except on last attempt)
            if attempt_number <= self.policy.max_attempts:
                await asyncio.sleep(backoff)

        # All attempts exhausted
        return RetryResult(
            success=False,
            attempt_number=attempt_number - 1,
            error=last_error,
        )

    def get_next_retry_time(self, attempt_number: int) -> datetime | None:
        """Calculate when the next retry should occur.

        Args:
            attempt_number: The current attempt number (1-indexed)

        Returns:
            Datetime of next retry, or None if no more retries
        """
        if not self.policy.should_retry(attempt_number):
            return None

        backoff = self.policy.calculate_backoff(attempt_number)
        return datetime.now(UTC) + timedelta(seconds=backoff)
