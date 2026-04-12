"""Rate limiter lifecycle service.

Manages the async rate limiter initialization and cleanup.
"""

from __future__ import annotations

from core.lifecycle import LifecycleService, ServicePriority
from core.logger import get_logger

logger = get_logger(__name__)


class RateLimiterService(LifecycleService):
    """Rate limiter lifecycle service.

    This service handles:
    - Redis-based rate limiter initialization
    - Cleanup on shutdown

    Priority: ESSENTIAL
    """

    @property
    def name(self) -> str:
        return "rate_limiter"

    @property
    def priority(self) -> ServicePriority:
        return ServicePriority.ESSENTIAL

    async def start(self) -> None:
        """Initialize the rate limiter.

        Sets up async rate limiter for API protection.
        """
        logger.info("Initializing rate limiter...")

        from middleware.rate_limiter import init_rate_limiter

        await init_rate_limiter()

        logger.info("Rate limiter initialized")

    async def stop(self) -> None:
        """Close rate limiter connections.

        Cleans up any Redis connections used by the rate limiter.
        """
        logger.info("Closing rate limiter...")

        from middleware.rate_limiter import close_rate_limiter

        await close_rate_limiter()

        logger.info("Rate limiter closed")
