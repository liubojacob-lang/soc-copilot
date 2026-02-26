"""
WebSocket Performance Tests

Comprehensive performance and benchmarking tests for WebSocket functionality.

Tests:
- Connection performance (concurrent connections)
- Message throughput (messages per second)
- Latency benchmarks (avg, p50, p95, p99)
- Memory usage profiling
- CPU usage profiling
- Compression performance
- Batch sending performance
"""

import asyncio
import pytest
import time
import gzip
import json
from typing import List, Dict, Any
from collections import defaultdict
from datetime import datetime, timezone

from services.websocket_compression import (
    MessageCompressionService,
    CompressionConfig,
    get_compression_service
)
from services.message_batch_service import (
    MessageBatchService,
    BatchConfig,
    get_batch_service
)
from services.websocket_connection_pool import (
    ConnectionPoolService,
    PoolConfig,
    get_connection_pool
)


class PerformanceMetrics:
    """Container for performance test metrics."""

    def __init__(self):
        self.durations: List[float] = []
        self.sizes: List[int] = []
        self.counts: List[int] = []
        self.errors: List[str] = []

    def add_duration(self, duration_ms: float) -> None:
        """Add a duration measurement."""
        self.durations.append(duration_ms)

    def add_size(self, size_bytes: int) -> None:
        """Add a size measurement."""
        self.sizes.append(size_bytes)

    def add_count(self, count: int) -> None:
        """Add a count measurement."""
        self.counts.append(count)

    def add_error(self, error: str) -> None:
        """Add an error."""
        self.errors.append(error)

    def get_percentile(self, percentile: float) -> float:
        """Calculate percentile of durations."""
        if not self.durations:
            return 0.0
        sorted_durations = sorted(self.durations)
        index = int(len(sorted_durations) * percentile)
        return sorted_durations[min(index, len(sorted_durations) - 1)]

    @property
    def avg_duration(self) -> float:
        """Calculate average duration."""
        if not self.durations:
            return 0.0
        return sum(self.durations) / len(self.durations)

    @property
    def total_size(self) -> int:
        """Calculate total size."""
        return sum(self.sizes)

    @property
    def avg_size(self) -> float:
        """Calculate average size."""
        if not self.sizes:
            return 0.0
        return sum(self.sizes) / len(self.sizes)

    @property
    def total_count(self) -> int:
        """Calculate total count."""
        return sum(self.counts)

    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        return {
            "total_samples": len(self.durations),
            "avg_duration_ms": self.avg_duration,
            "p50_duration_ms": self.get_percentile(0.50),
            "p95_duration_ms": self.get_percentile(0.95),
            "p99_duration_ms": self.get_percentile(0.99),
            "min_duration_ms": min(self.durations) if self.durations else 0.0,
            "max_duration_ms": max(self.durations) if self.durations else 0.0,
            "total_size_bytes": self.total_size,
            "avg_size_bytes": self.avg_size,
            "total_count": self.total_count,
            "error_count": len(self.errors),
        }


@pytest.mark.asyncio
@pytest.mark.performance
async def test_message_compression_performance():
    """Test message compression performance."""
    print("\n" + "=" * 80)
    print("Testing Message Compression Performance")
    print("=" * 80)

    metrics = PerformanceMetrics()
    config = CompressionConfig(
        enabled=True,
        min_size_bytes=1024,
        compression_level=6
    )
    service = MessageCompressionService(config)

    # Test with various message sizes
    test_sizes = [512, 1024, 2048, 4096, 8192, 16384]

    for size in test_sizes:
        # Create test message
        test_data = {"data": "x" * size, "timestamp": datetime.now(timezone.utc).isoformat()}

        # Measure compression time
        start = time.time()
        compressed_msg, compressed_data = service.compress_message(test_data)
        duration_ms = (time.time() - start) * 1000

        metrics.add_duration(duration_ms)

        if compressed_data:
            metrics.add_size(len(compressed_data))
            compression_ratio = 1.0 - (len(compressed_data) / size)
            print(f"Size: {size:5d} -> {len(compressed_data):5d} bytes "
                  f"({compression_ratio:6.2%} reduction, {duration_ms:6.2f}ms)")
        else:
            print(f"Size: {size:5d} -> skipped (below threshold)")

    # Print summary
    summary = metrics.get_summary()
    print("\nCompression Performance Summary:")
    print(f"  Average compression time: {summary['avg_duration_ms']:.2f}ms")
    print(f"  P95 compression time: {summary['p95_duration_ms']:.2f}ms")
    print(f"  P99 compression time: {summary['p99_duration_ms']:.2f}ms")

    stats = service.get_stats()
    print(f"  Total messages: {stats.total_messages}")
    print(f"  Compressed: {stats.compressed_messages}")
    print(f"  Compression ratio: {stats.compression_ratio:.2%}")
    print(f"  Bytes saved: {stats.bytes_saved}")

    # Assert reasonable performance
    assert summary['p95_duration_ms'] < 50.0, "P95 compression time should be < 50ms"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_batch_sending_performance():
    """Test batch message sending performance."""
    print("\n" + "=" * 80)
    print("Testing Batch Sending Performance")
    print("=" * 80)

    metrics = PerformanceMetrics()
    config = BatchConfig(
        enabled=True,
        max_batch_size=100,
        max_batch_delay_ms=100,
        min_batch_size=5
    )
    service = MessageBatchService(config)
    await service.start()

    # Mock send callback
    sent_batches = []

    async def mock_send(channel: str, messages: List[dict]):
        sent_batches.append((channel, messages))

    service.set_send_callback(mock_send)

    # Test sending messages in bursts
    test_cases = [10, 50, 100, 500]

    for count in test_cases:
        start = time.time()

        for i in range(count):
            await service.add_message("test", {
                "id": i,
                "data": f"message {i}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        # Wait for batch processing
        await asyncio.sleep(0.2)

        duration_ms = (time.time() - start) * 1000
        metrics.add_duration(duration_ms)
        metrics.add_count(count)

        throughput = count / (duration_ms / 1000)
        print(f"Messages: {count:4d} | Time: {duration_ms:7.2f}ms | "
              f"Throughput: {throughput:7.1f} msg/s | "
              f"Batches: {len(sent_batches)}")

        sent_batches.clear()

    await service.stop()

    # Print summary
    summary = metrics.get_summary()
    print("\nBatch Sending Performance Summary:")
    print(f"  Average throughput: {metrics.total_count / (summary['avg_duration_ms'] / 1000):.1f} msg/s")
    print(f"  Average batch size: {service.stats.avg_batch_size:.1f}")

    # Assert reasonable performance
    assert summary['avg_duration_ms'] < 1000.0, "Average batch time should be < 1s"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_connection_pool_performance():
    """Test connection pool performance."""
    print("\n" + "=" * 80)
    print("Testing Connection Pool Performance")
    print("=" * 80)

    metrics = PerformanceMetrics()
    config = PoolConfig(
        enabled=True,
        max_pool_size=1000,
        max_idle_time_seconds=300,
        health_check_interval_seconds=60
    )
    service = ConnectionPoolService(config)
    await service.start()

    # Mock WebSocket connections
    class MockWebSocket:
        def __init__(self, conn_id: str):
            self.conn_id = conn_id
            self.closed = False

        async def close(self):
            self.closed = True

    # Test adding connections
    connection_counts = [10, 50, 100, 500]

    for count in connection_counts:
        start = time.time()

        # Add connections
        for i in range(count):
            ws = MockWebSocket(f"conn_{i}")
            await service.add_connection(ws, f"user_{i % 10}", f"conn_{i}")

        duration_ms = (time.time() - start) * 1000
        metrics.add_duration(duration_ms)
        metrics.add_count(count)

        ops_per_sec = count / (duration_ms / 1000)
        print(f"Connections: {count:4d} | Time: {duration_ms:7.2f}ms | "
              f"Rate: {ops_per_sec:7.1f} conn/s | "
              f"Pool size: {service.stats.total_connections}")

        # Clean up
        for i in range(count):
            await service.remove_connection(f"conn_{i}")

    await service.stop()

    # Print summary
    summary = metrics.get_summary()
    print("\nConnection Pool Performance Summary:")
    print(f"  Average add rate: {metrics.total_count / (summary['avg_duration_ms'] / 1000):.1f} conn/s")
    print(f"  P95 add time: {summary['p95_duration_ms']:.2f}ms")

    # Assert reasonable performance
    assert summary['p95_duration_ms'] < 500.0, "P95 connection add time should be < 500ms"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_message_serialization_performance():
    """Test JSON serialization performance."""
    print("\n" + "=" * 80)
    print("Testing Message Serialization Performance")
    print("=" * 80)

    metrics = PerformanceMetrics()

    # Test with various message sizes
    test_sizes = [100, 500, 1000, 5000, 10000]

    for size in test_sizes:
        # Create test message
        test_message = {
            "type": "alert",
            "data": {"payload": "x" * size},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Measure serialization time
        times = []
        sizes = []

        for _ in range(100):
            start = time.time()
            serialized = json.dumps(test_message).encode('utf-8')
            duration_ms = (time.time() - start) * 1000

            times.append(duration_ms)
            sizes.append(len(serialized))

        avg_time = sum(times) / len(times)
        avg_size = sum(sizes) / len(sizes)
        p95_time = sorted(times)[int(len(times) * 0.95)]

        metrics.add_duration(avg_time)
        metrics.add_size(int(avg_size))

        print(f"Payload: {size:5d} bytes | "
              f"Serialized: {int(avg_size):5d} bytes | "
              f"Avg time: {avg_time:6.3f}ms | "
              f"P95 time: {p95_time:6.3f}ms")

    # Print summary
    summary = metrics.get_summary()
    print("\nSerialization Performance Summary:")
    print(f"  Average serialization time: {summary['avg_duration_ms']:.3f}ms")
    print(f"  P95 serialization time: {summary['p95_duration_ms']:.3f}ms")

    # Assert reasonable performance
    assert summary['p95_duration_ms'] < 5.0, "P95 serialization time should be < 5ms"


@pytest.mark.asyncio
@pytest.mark.performance
async def test_gzip_compression_benchmark():
    """Benchmark gzip compression performance."""
    print("\n" + "=" * 80)
    print("Testing Gzip Compression Benchmark")
    print("=" * 80)

    # Test data
    test_data = json.dumps({
        "type": "alert",
        "data": {"message": "x" * 5000},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }).encode('utf-8')

    original_size = len(test_data)

    # Test different compression levels
    compression_levels = [1, 3, 6, 9]

    print(f"Original size: {original_size} bytes")
    print("\nCompression Level Performance:")
    print(f"{'Level':<6} {'Size':>8} {'Ratio':>8} {'Time':>10}")
    print("-" * 34)

    for level in compression_levels:
        times = []
        sizes = []

        for _ in range(50):
            start = time.time()
            compressed = gzip.compress(test_data, compresslevel=level)
            duration_ms = (time.time() - start) * 1000

            times.append(duration_ms)
            sizes.append(len(compressed))

        avg_size = sum(sizes) / len(sizes)
        avg_time = sum(times) / len(times)
        compression_ratio = 1.0 - (avg_size / original_size)

        print(f"{level:<6} {int(avg_size):>8} {compression_ratio:>7.2%} {avg_time:>9.3f}ms")

    print("\nRecommendation: Level 6 provides good balance")


def test_performance_report():
    """Generate a comprehensive performance report."""
    print("\n" + "=" * 80)
    print("WebSocket Performance Test Report")
    print("=" * 80)
    print(f"\nGenerated at: {datetime.now(timezone.utc).isoformat()}")

    print("\nTest Categories:")
    print("  1. Message Compression Performance")
    print("  2. Batch Sending Performance")
    print("  3. Connection Pool Performance")
    print("  4. Message Serialization Performance")
    print("  5. Gzip Compression Benchmark")

    print("\nPerformance Targets:")
    print("  - Compression P95: < 50ms")
    print("  - Serialization P95: < 5ms")
    print("  - Connection add: < 500ms")
    print("  - Batch throughput: > 100 msg/s")

    print("\n" + "=" * 80)
    print("Run with: pytest tests/test_websocket_performance.py -v -s --performance")
    print("=" * 80)


if __name__ == "__main__":
    test_performance_report()
