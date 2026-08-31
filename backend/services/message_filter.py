"""
Server-side Message Filter Engine

This service provides server-side filtering for WebSocket messages,
allowing users to control which messages they receive based on:
- Severity levels
- Event types
- Agent IDs
- Source IPs
- Content search
- Rate limiting

Features:
- Per-user filter rules
- Priority-based rule evaluation
- Real-time filter updates
- Performance metrics
"""

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

from core.logger import get_logger
from models.message_filters import (
    FilterSet,
    FilterStats,
    FilterValidationResult,
)

logger = get_logger(__name__)


class MessageFilterEngine:
    """
    Engine for evaluating WebSocket messages against user filter rules.

    Rules are evaluated in priority order (highest first).
    First matching rule determines the action.
    """

    def __init__(self):
        # User filter sets: {user_id: FilterSet}
        self.user_filters: dict[str, FilterSet] = {}
        # Filter stats: {user_id: FilterStats}
        self.filter_stats: dict[str, FilterStats] = {}
        self._lock = asyncio.Lock()

    async def set_filters(self, user_id: str, filter_set: FilterSet) -> None:
        """
        Set or replace filters for a user.

        Args:
            user_id: User identifier
            filter_set: Filter set to apply
        """
        async with self._lock:
            self.user_filters[user_id] = filter_set

            # Initialize stats if not exists
            if user_id not in self.filter_stats:
                self.filter_stats[user_id] = FilterStats(
                    user_id=user_id,
                    total_rules=len(filter_set.rules),
                    active_rules=len(filter_set.get_active_rules()),
                )

        logger.info(f"Set {len(filter_set.rules)} filter rules for user {user_id}")

    async def get_filters(self, user_id: str) -> FilterSet | None:
        """Get filter set for a user."""
        async with self._lock:
            return self.user_filters.get(user_id)

    async def remove_filters(self, user_id: str) -> bool:
        """Remove all filters for a user."""
        async with self._lock:
            if user_id in self.user_filters:
                del self.user_filters[user_id]
                logger.info(f"Removed filters for user {user_id}")
                return True
            return False

    async def evaluate_message(
        self, user_id: str, message_data: dict[str, Any]
    ) -> FilterValidationResult:
        """
        Evaluate a message against user's filter rules.

        Args:
            user_id: User identifier
            message_data: Message data to evaluate

        Returns:
            FilterValidationResult with decision and details
        """
        start_time = time.time()

        try:
            # Get user's filters
            filter_set = await self.get_filters(user_id)

            if not filter_set:
                # No filters configured, allow message
                return FilterValidationResult(
                    user_id=user_id,
                    should_send=True,
                    processing_time_ms=(time.time() - start_time) * 1000,
                )

            # Evaluate message against rules
            sorted_rules = filter_set.get_sorted_rules()
            matched_rules = []

            for rule in sorted_rules:
                if rule.matches(message_data):
                    matched_rules.append(rule.id or rule.name)
                    # Update last triggered time
                    rule.last_triggered_at = datetime.now(UTC)

            # Make decision
            should_send = filter_set.should_send_message(message_data)

            # Update stats
            await self._update_stats(user_id, should_send, matched_rules, start_time)

            return FilterValidationResult(
                user_id=user_id,
                should_send=should_send,
                matched_rules=matched_rules,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"Error evaluating filters for user {user_id}: {e}")
            # On error, allow message (fail-open)
            return FilterValidationResult(
                user_id=user_id,
                should_send=True,
                rejected_by=f"Error: {e!s}",
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    async def _update_stats(
        self,
        user_id: str,
        should_send: bool,
        matched_rules: list[str],
        start_time: float,
    ) -> None:
        """Update filter statistics."""
        if user_id not in self.filter_stats:
            self.filter_stats[user_id] = FilterStats(user_id=user_id)

        stats = self.filter_stats[user_id]
        stats.total_messages_evaluated += 1

        if should_send:
            stats.messages_allowed += 1
        else:
            stats.messages_blocked += 1

        # Update processing time average
        processing_time_ms = (time.time() - start_time) * 1000
        n = stats.total_messages_evaluated
        stats.avg_processing_time_ms = (
            stats.avg_processing_time_ms * (n - 1) + processing_time_ms
        ) / n

        # Track most matched rule
        for rule_id in matched_rules:
            if stats.most_matched_rule is None:
                stats.most_matched_rule = rule_id

    async def get_stats(self, user_id: str) -> FilterStats | None:
        """Get filter statistics for a user."""
        async with self._lock:
            return self.filter_stats.get(user_id)

    async def reset_stats(self, user_id: str) -> bool:
        """Reset filter statistics for a user."""
        async with self._lock:
            if user_id in self.filter_stats:
                self.filter_stats[user_id] = FilterStats(user_id=user_id)
                return True
            return False

    async def get_all_stats(self) -> dict[str, FilterStats]:
        """Get statistics for all users."""
        async with self._lock:
            return dict(self.filter_stats)


class RateLimiter:
    """
    Rate limiter for message delivery.

    Ensures users don't receive more messages than configured
    in their filter rules.
    """

    def __init__(self):
        # Track message counts: {user_id: [(timestamp, count)]}
        self.message_counts: dict[str, list[datetime]] = {}
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, user_id: str, max_per_minute: int | None) -> bool:
        """
        Check if user is within their rate limit.

        Args:
            user_id: User identifier
            max_per_minute: Maximum messages per minute (0 = unlimited)

        Returns:
            True if within limit, False if exceeded
        """
        if not max_per_minute or max_per_minute <= 0:
            return True

        async with self._lock:
            now = datetime.now(UTC)

            # Clean old entries (older than 1 minute)
            if user_id in self.message_counts:
                self.message_counts[user_id] = [
                    ts
                    for ts in self.message_counts[user_id]
                    if (now - ts).total_seconds() < 60
                ]

            # Check current count
            current_count = len(self.message_counts.get(user_id, []))

            if current_count >= max_per_minute:
                return False

            # Add current message
            if user_id not in self.message_counts:
                self.message_counts[user_id] = []

            self.message_counts[user_id].append(now)
            return True


class FilterService:
    """
    High-level service for message filtering.

    Combines filter engine with rate limiting and caching.
    """

    def __init__(self):
        self.filter_engine = MessageFilterEngine()
        self.rate_limiter = RateLimiter()

    async def should_send_message(
        self,
        user_id: str,
        message_data: dict[str, Any],
        max_per_minute: int | None = None,
    ) -> FilterValidationResult:
        """
        Determine if a message should be sent to a user.

        Args:
            user_id: User identifier
            message_data: Message data
            max_per_minute: Optional rate limit

        Returns:
            FilterValidationResult with decision
        """
        # First, check rate limit
        if not await self.rate_limiter.check_rate_limit(user_id, max_per_minute):
            logger.debug(f"User {user_id} exceeded rate limit")
            return FilterValidationResult(
                user_id=user_id,
                should_send=False,
                rejected_by="Rate limit exceeded",
                processing_time_ms=0.0,
            )

        # Then, evaluate filters
        return await self.filter_engine.evaluate_message(user_id, message_data)

    async def set_user_filters(self, user_id: str, filter_set: FilterSet) -> None:
        """Set filter rules for a user."""
        await self.filter_engine.set_filters(user_id, filter_set)

    async def get_user_filters(self, user_id: str) -> FilterSet | None:
        """Get filter rules for a user."""
        return await self.filter_engine.get_filters(user_id)

    async def remove_user_filters(self, user_id: str) -> bool:
        """Remove filter rules for a user."""
        return await self.filter_engine.remove_filters(user_id)

    async def get_user_stats(self, user_id: str) -> FilterStats | None:
        """Get filter statistics for a user."""
        return await self.filter_engine.get_stats(user_id)

    async def reset_user_stats(self, user_id: str) -> bool:
        """Reset filter statistics for a user."""
        return await self.filter_engine.reset_stats(user_id)

    async def get_all_stats(self) -> dict[str, FilterStats]:
        """Get statistics for all users."""
        return await self.filter_engine.get_all_stats()


# Global instance
_filter_service: FilterService | None = None


def get_filter_service() -> FilterService:
    """Get or create the global filter service instance."""
    global _filter_service
    if _filter_service is None:
        _filter_service = FilterService()
    return _filter_service


async def start_filter_service():
    """Initialize the filter service."""
    service = get_filter_service()
    logger.info("Filter service initialized")
    return service
