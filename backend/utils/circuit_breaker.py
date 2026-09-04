"""Circuit Breaker Pattern implementation for SOC Copilot.

Provides protection against cascading failures when calling external
dependencies (LLMs, TI feeds, Wazuh, etc.).
"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

from core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is attempted while the circuit is OPEN."""

    def __init__(self, message: str = "Circuit breaker is OPEN. Request rejected.", name: str = "default"):
        super().__init__(f"[{name}] {message}")
        self.name = name


class CircuitBreaker:
    """Asynchronous thread-safe Circuit Breaker.

    - CLOSED: Normal operation. Consecutive failures exceeding threshold transition circuit to OPEN.
    - OPEN: Calls immediately fail with CircuitBreakerOpenException.
    - HALF_OPEN: Single trial call allowed. If successful -> CLOSED. If fails -> OPEN.
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        expected_exceptions: tuple[type[Exception], ...] = (Exception,),
    ):
        self.name = name
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_timeout = max(0.1, recovery_timeout)
        self.expected_exceptions = expected_exceptions

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = time.time()
        self.last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()

    @property
    def is_available(self) -> bool:
        """Check if circuit can process requests without acquiring lock."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            return (time.time() - self.last_state_change) > self.recovery_timeout
        return True

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute async function protected by circuit breaker."""
        async with self._lock:
            now = time.time()
            if self.state == CircuitState.OPEN:
                if now - self.last_state_change >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    logger.warning(f"CircuitBreaker[{self.name}] transitioned to HALF_OPEN. Probing downstream...")
                else:
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker is OPEN (cooldown: {self.recovery_timeout - (now - self.last_state_change):.1f}s remaining)",
                        name=self.name,
                    )

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
        except self.expected_exceptions as exc:
            await self._record_failure(exc)
            raise exc

        await self._record_success()
        return result

    async def _record_success(self) -> None:
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.last_state_change = time.time()
                logger.info(f"CircuitBreaker[{self.name}] recovered to CLOSED after successful probe.")
            elif self.state == CircuitState.CLOSED and self.failure_count > 0:
                self.failure_count = 0

    async def _record_failure(self, exc: Exception) -> None:
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.last_state_change = time.time()
                logger.error(
                    f"CircuitBreaker[{self.name}] probe failed in HALF_OPEN ({exc}). Re-opening circuit for {self.recovery_timeout}s."
                )
            elif self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.last_state_change = time.time()
                logger.error(
                    f"CircuitBreaker[{self.name}] reached {self.failure_count} consecutive failures. Tripped to OPEN state ({exc})."
                )

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()
