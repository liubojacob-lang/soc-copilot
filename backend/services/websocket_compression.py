"""
WebSocket Message Compression Service

This service provides compression for WebSocket messages to reduce
network bandwidth usage and improve performance.

Features:
- Gzip compression for large messages
- Configurable compression threshold
- Per-message compression control
- Compression statistics tracking
"""

import gzip
import json
import time
from typing import Any

from pydantic import BaseModel

from core.logger import get_logger

logger = get_logger(__name__)


class CompressionConfig(BaseModel):
    """Configuration for message compression."""

    enabled: bool = True
    min_size_bytes: int = 1024  # Only compress messages larger than 1KB
    compression_level: int = 6  # Gzip compression level (0-9, 6 is default)
    max_compression_ratio: float = 0.9  # Skip if compression ratio > 90%


class CompressionStats(BaseModel):
    """Statistics for compression performance."""

    total_messages: int = 0
    compressed_messages: int = 0
    original_size_bytes: int = 0
    compressed_size_bytes: int = 0
    compression_time_ms: float = 0.0
    bytes_saved: int = 0

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio (0-1)."""
        if self.original_size_bytes == 0:
            return 0.0
        return 1.0 - (self.compressed_size_bytes / self.original_size_bytes)

    @property
    def avg_compression_time_ms(self) -> float:
        """Calculate average compression time."""
        if self.compressed_messages == 0:
            return 0.0
        return self.compression_time_ms / self.compressed_messages


class MessageCompressionService:
    """
    Service for compressing WebSocket messages.

    Uses gzip compression to reduce message size for large payloads.
    """

    def __init__(self, config: CompressionConfig | None = None):
        self.config = config or CompressionConfig()
        self.stats = CompressionStats()

    def should_compress(self, data: bytes) -> bool:
        """
        Determine if message should be compressed.

        Args:
            data: Raw message data

        Returns:
            True if message should be compressed
        """
        if not self.config.enabled:
            return False

        # Check size threshold
        if len(data) < self.config.min_size_bytes:
            return False

        return True

    def compress_message(
        self, message: dict[str, Any]
    ) -> tuple[dict[str, Any], bytes | None]:
        """
        Compress a WebSocket message.

        Args:
            message: Message dictionary

        Returns:
            (message_with_flag, compressed_data) tuple
            - message_with_flag: Message with compression metadata
            - compressed_data: Compressed binary data (None if not compressed)
        """
        start_time = time.time()

        # Serialize message
        json_data = json.dumps(message).encode("utf-8")
        original_size = len(json_data)

        # Update stats
        self.stats.total_messages += 1
        self.stats.original_size_bytes += original_size

        # Check if should compress
        if not self.should_compress(json_data):
            return message, None

        try:
            # Compress with gzip
            compressed_data = gzip.compress(
                json_data, compresslevel=self.config.compression_level
            )

            compressed_size = len(compressed_data)
            compression_ratio = 1.0 - (compressed_size / original_size)

            # Skip if compression doesn't help enough
            if compression_ratio < (1.0 - self.config.max_compression_ratio):
                logger.debug(
                    f"Compression ratio {compression_ratio:.2%} below threshold, "
                    f"skipping compression"
                )
                return message, None

            # Update stats
            self.stats.compressed_messages += 1
            self.stats.compressed_size_bytes += compressed_size
            self.stats.bytes_saved += original_size - compressed_size

            compression_time_ms = (time.time() - start_time) * 1000
            self.stats.compression_time_ms += compression_time_ms

            # Add compression metadata to message
            message_with_meta = {
                **message,
                "_compressed": True,
                "_original_size": original_size,
                "_compressed_size": compressed_size,
                "_compression_ratio": compression_ratio,
            }

            logger.debug(
                f"Compressed message: {original_size} -> {compressed_size} bytes "
                f"({compression_ratio:.1%} reduction, {compression_time_ms:.2f}ms)"
            )

            return message_with_meta, compressed_data

        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return message, None

    def decompress_message(self, compressed_data: bytes) -> dict[str, Any] | None:
        """
        Decompress a compressed message.

        Args:
            compressed_data: Compressed binary data

        Returns:
            Decompressed message dictionary, or None if decompression fails
        """
        try:
            decompressed_data = gzip.decompress(compressed_data)
            message = json.loads(decompressed_data.decode("utf-8"))

            # Remove compression metadata
            message.pop("_compressed", None)
            message.pop("_original_size", None)
            message.pop("_compressed_size", None)
            message.pop("_compression_ratio", None)

            return message

        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            return None

    def get_stats(self) -> CompressionStats:
        """Get compression statistics."""
        return self.stats

    def reset_stats(self) -> None:
        """Reset compression statistics."""
        self.stats = CompressionStats()


class BatchCompressionService:
    """
    Service for compressing batches of messages.

    More efficient for multiple small messages.
    """

    def __init__(self, config: CompressionConfig | None = None):
        self.compression_service = MessageCompressionService(config)

    async def compress_batch(
        self, messages: list[dict[str, Any]]
    ) -> list[tuple[dict[str, Any], bytes | None]]:
        """
        Compress a batch of messages.

        Args:
            messages: List of message dictionaries

        Returns:
            List of (message_with_flag, compressed_data) tuples
        """
        results = []

        for message in messages:
            compressed_msg, compressed_data = self.compression_service.compress_message(
                message
            )
            results.append((compressed_msg, compressed_data))

        logger.debug(
            f"Compressed batch: {len(messages)} messages, "
            f"{self.compression_service.stats.compressed_messages} compressed"
        )

        return results

    def get_stats(self) -> CompressionStats:
        """Get compression statistics."""
        return self.compression_service.get_stats()

    def reset_stats(self) -> None:
        """Reset compression statistics."""
        self.compression_service.reset_stats()


# Global instances
_compression_service: MessageCompressionService | None = None
_batch_compression_service: BatchCompressionService | None = None


def get_compression_service() -> MessageCompressionService:
    """Get or create the global compression service instance."""
    global _compression_service
    if _compression_service is None:
        _compression_service = MessageCompressionService()
    return _compression_service


def get_batch_compression_service() -> BatchCompressionService:
    """Get or create the global batch compression service instance."""
    global _batch_compression_service
    if _batch_compression_service is None:
        _batch_compression_service = BatchCompressionService()
    return _batch_compression_service


async def start_compression_service():
    """Initialize the compression service."""
    service = get_compression_service()
    logger.info(
        f"WebSocket compression service initialized "
        f"(enabled={service.config.enabled}, "
        f"min_size={service.config.min_size_bytes} bytes)"
    )
    return service
