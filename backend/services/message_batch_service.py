"""
Message Batch Service for WebSocket

This service provides batch message sending optimization to reduce
network overhead and improve throughput.

Features:
- Accumulate messages into batches
- Send multiple messages in a single network call
- Configurable batch size and timeout
- Batch statistics tracking
"""

import asyncio
import time
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from core.logger import get_logger

logger = get_logger(__name__)


class BatchConfig(BaseModel):
    """Configuration for message batching."""

    enabled: bool = True
    max_batch_size: int = 100  # Maximum messages per batch
    max_batch_delay_ms: int = 100  # Maximum wait time before flushing (milliseconds)
    min_batch_size: int = 5  # Minimum messages before flushing


class BatchStats(BaseModel):
    """Statistics for batch operations."""

    total_batches: int = 0
    total_messages_batched: int = 0
    avg_batch_size: float = 0.0
    total_batch_time_ms: float = 0.0
    avg_batch_time_ms: float = 0.0


class MessageBatch:
    """A batch of messages to be sent together."""

    def __init__(self, channel: str, max_size: int = 100):
        self.channel = channel
        self.max_size = max_size
        self.messages: list[dict[str, Any]] = []
        self.created_at = time.time()
        self.size_bytes = 0

    def add_message(self, message: dict[str, Any]) -> bool:
        """
        Add a message to the batch.

        Args:
            message: Message dictionary

        Returns:
            True if message was added, False if batch is full
        """
        if len(self.messages) >= self.max_size:
            return False

        self.messages.append(message)
        self.size_bytes += len(str(message).encode("utf-8"))
        return True

    def is_ready(self, min_size: int, max_delay_ms: int) -> bool:
        """
        Check if batch is ready to be sent.

        Args:
            min_size: Minimum number of messages required
            max_delay_ms: Maximum delay before forcing send

        Returns:
            True if batch should be sent
        """
        # Ready if batch is full
        if len(self.messages) >= self.max_size:
            return True

        # Ready if minimum size reached
        if len(self.messages) >= min_size:
            return True

        # Ready if max delay exceeded
        age_ms = (time.time() - self.created_at) * 1000
        if age_ms >= max_delay_ms and len(self.messages) > 0:
            return True

        return False

    def can_fit_more(self, min_size: int) -> bool:
        """Check if batch can accept more messages."""
        return len(self.messages) < self.max_size

    def get_messages(self) -> list[dict[str, Any]]:
        """Get all messages in the batch."""
        return self.messages

    def clear(self) -> None:
        """Clear all messages from the batch."""
        self.messages = []
        self.size_bytes = 0
        self.created_at = time.time()


class MessageBatchService:
    """
    Service for batching WebSocket messages.

    Accumulates messages and sends them in batches to reduce
    network overhead.
    """

    def __init__(self, config: BatchConfig | None = None):
        self.config = config or BatchConfig()
        self.stats = BatchStats()

        # Per-channel batches: {channel: MessageBatch}
        self.batches: dict[str, MessageBatch] = {}
        self._lock = asyncio.Lock()

        # Send callback: async def send_batch(channel: str, messages: List[dict]) -> None
        self._send_callback: Callable | None = None

        # Background flush task
        self._flush_task: asyncio.Task | None = None
        self._running = False

    def set_send_callback(self, callback: Callable) -> None:
        """
        Set the callback function for sending batches.

        Args:
            callback: Async function to send batches
        """
        self._send_callback = callback

    async def start(self) -> None:
        """Start the batch service background tasks."""
        if self._running:
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("Message batch service started")

    async def stop(self) -> None:
        """Stop the batch service."""
        if not self._running:
            return

        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Flush all pending batches
        await self.flush_all()

        logger.info("Message batch service stopped")

    async def add_message(self, channel: str, message: dict[str, Any]) -> bool:
        """
        Add a message to the appropriate batch.

        Args:
            channel: Channel name
            message: Message dictionary

        Returns:
            True if message was added to batch
        """
        if not self.config.enabled:
            return False

        async with self._lock:
            # Get or create batch for channel
            if channel not in self.batches:
                self.batches[channel] = MessageBatch(
                    channel, max_size=self.config.max_batch_size
                )

            batch = self.batches[channel]

            # Add message to batch
            if not batch.add_message(message):
                # Batch is full, flush it first
                await self._flush_batch(channel)

                # Try adding again to new batch
                batch = self.batches[channel]
                if not batch.add_message(message):
                    logger.warning(
                        f"Failed to add message to batch for channel {channel}"
                    )
                    return False

            # Check if batch is ready to send
            if batch.is_ready(
                self.config.min_batch_size, self.config.max_batch_delay_ms
            ):
                await self._flush_batch(channel)

            return True

    async def _flush_loop(self) -> None:
        """Background loop to periodically flush batches."""
        while self._running:
            try:
                await asyncio.sleep(self.config.max_batch_delay_ms / 1000)
                await self._flush_ready_batches()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")

    async def _flush_ready_batches(self) -> None:
        """Flush all batches that are ready to send."""
        async with self._lock:
            for channel in list(self.batches.keys()):
                batch = self.batches[channel]

                if batch.is_ready(
                    self.config.min_batch_size, self.config.max_batch_delay_ms
                ):
                    await self._flush_batch(channel)

    async def _flush_batch(self, channel: str) -> None:
        """Flush a single channel's batch."""
        if channel not in self.batches:
            return

        batch = self.batches[channel]

        if len(batch.messages) == 0:
            return

        messages = batch.get_messages()
        batch.clear()

        # Update stats
        self.stats.total_batches += 1
        self.stats.total_messages_batched += len(messages)

        # Calculate average batch size
        if self.stats.total_batches > 0:
            self.stats.avg_batch_size = (
                self.stats.total_messages_batched / self.stats.total_batches
            )

        # Send batch via callback
        if self._send_callback:
            start_time = time.time()
            try:
                await self._send_callback(channel, messages)

                batch_time_ms = (time.time() - start_time) * 1000
                self.stats.total_batch_time_ms += batch_time_ms
                self.stats.avg_batch_time_ms = (
                    self.stats.total_batch_time_ms / self.stats.total_batches
                )

                logger.debug(
                    f"Flushed batch: channel={channel}, "
                    f"messages={len(messages)}, "
                    f"time={batch_time_ms:.2f}ms"
                )

            except Exception as e:
                logger.error(f"Error sending batch for channel {channel}: {e}")

    async def flush_all(self) -> None:
        """Flush all pending batches."""
        async with self._lock:
            for channel in list(self.batches.keys()):
                await self._flush_batch(channel)

    def get_stats(self) -> BatchStats:
        """Get batch statistics."""
        return self.stats

    def reset_stats(self) -> None:
        """Reset batch statistics."""
        self.stats = BatchStats()


# Global instance
_batch_service: MessageBatchService | None = None


def get_batch_service() -> MessageBatchService:
    """Get or create the global batch service instance."""
    global _batch_service
    if _batch_service is None:
        _batch_service = MessageBatchService()
    return _batch_service


async def start_batch_service():
    """Initialize and start the batch service."""
    service = get_batch_service()
    await service.start()
    logger.info(
        f"Message batch service initialized "
        f"(max_batch_size={service.config.max_batch_size}, "
        f"max_delay={service.config.max_batch_delay_ms}ms)"
    )
    return service
