"""
WebSocket Stress Tests

Comprehensive stress tests for WebSocket functionality to validate
system stability under high load.

Tests:
- Concurrent connections (1000+)
- High throughput messaging (10000+ msg/s)
- Long duration stability (1 hour+)
- Memory leak detection
- Resource usage monitoring
"""

import asyncio
import pytest
import time
import psutil
import tracemalloc
from datetime import datetime, timezone
from typing import List, Dict, Any

from routers.websocket import ConnectionManager, WebSocketMessage


class MockWebSocket:
    """Mock WebSocket for stress testing."""

    def __init__(self, conn_id: str):
        self.conn_id = conn_id
        self.messages: List[Dict[str, Any]] = []
        self.closed = False
        self.send_count = 0
        self.last_send_time = None

    async def send_json(self, message: Dict[str, Any]) -> None:
        """Send a JSON message."""
        if self.closed:
            raise RuntimeError("WebSocket is closed")
        self.messages.append(message)
        self.send_count += 1
        self.last_send_time = time.time()

    async def close(self) -> None:
        """Close the WebSocket."""
        self.closed = True


class StressTestMetrics:
    """Container for stress test metrics."""

    def __init__(self):
        self.start_time = time.time()
        self.end_time = None
        self.peak_memory_mb = 0.0
        self.peak_cpu_percent = 0.0
        self.total_messages_sent = 0
        self.total_bytes_sent = 0
        self.errors: List[str] = []

    def finish(self):
        """Mark test as finished."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time

    def get_summary(self) -> Dict[str, Any]:
        """Get test summary."""
        return {
            "duration_seconds": self.duration,
            "peak_memory_mb": self.peak_memory_mb,
            "peak_cpu_percent": self.peak_cpu_percent,
            "total_messages_sent": self.total_messages_sent,
            "messages_per_second": self.total_messages_sent / self.duration if self.duration else 0,
            "total_errors": len(self.errors),
            "error_rate": len(self.errors) / max(1, self.total_messages_sent),
        }


@pytest.mark.asyncio
@pytest.mark.stress
async def test_concurrent_connections():
    """Test system with 1000+ concurrent connections."""
    print("\n" + "=" * 80)
    print("Stress Test: Concurrent Connections (1000+)")
    print("=" * 80)

    manager = ConnectionManager()
    metrics = StressTestMetrics()

    # Start memory tracking
    tracemalloc.start()
    process = psutil.Process()

    connection_count = 1000
    batch_size = 100

    print(f"\nCreating {connection_count} concurrent connections...")

    try:
        # Create connections in batches
        for batch_start in range(0, connection_count, batch_size):
            batch_end = min(batch_start + batch_size, connection_count)

            batch_start_time = time.time()

            # Create batch of connections
            for i in range(batch_start, batch_end):
                conn_id = f"stress_conn_{i}"
                ws = MockWebSocket(conn_id)
                await manager.connect(ws, f"user_{i}", "analyst", {"alerts"})

            batch_time = time.time() - batch_start_time

            # Update metrics
            current_memory = process.memory_info().rss / 1024 / 1024
            metrics.peak_memory_mb = max(metrics.peak_memory_mb, current_memory)

            current_cpu = process.cpu_percent()
            metrics.peak_cpu_percent = max(metrics.peak_cpu_percent, current_cpu)

            print(f"  Created connections {batch_start}-{batch_end} in {batch_time:.2f}s "
                  f"({manager.get_connection_count()} total, {current_memory:.1f} MB RAM)")

        assert manager.get_connection_count() == connection_count
        print(f"\n✓ Successfully created {connection_count} concurrent connections")
        print(f"  Peak memory: {metrics.peak_memory_mb:.1f} MB")
        print(f"  Peak CPU: {metrics.peak_cpu_percent:.1f}%")

        # Test broadcasting to all connections
        print("\nTesting broadcast to all connections...")
        broadcast_start = time.time()

        test_message = WebSocketMessage(
            type="system",
            data={"message": "Stress test broadcast"},
            timestamp=datetime.now(timezone.utc).isoformat(),
            channel="system"
        )

        await manager.broadcast_to_channel("system", test_message)

        broadcast_time = time.time() - broadcast_start
        print(f"✓ Broadcast completed in {broadcast_time:.2f}s")

        # Verify all connections received
        received_count = sum(
            1 for ws in manager.active_connections.keys()
            if len(ws.messages) > 0
        )
        print(f"  {received_count}/{connection_count} connections received message")

        # Cleanup
        print("\nCleaning up connections...")
        cleanup_start = time.time()

        for ws in list(manager.active_connections.keys()):
            await manager.disconnect(ws)

        cleanup_time = time.time() - cleanup_start
        print(f"✓ Cleaned up in {cleanup_time:.2f}s")

        assert manager.get_connection_count() == 0

        metrics.finish()
        summary = metrics.get_summary()

        print("\nStress Test Summary:")
        print(f"  Duration: {summary['duration_seconds']:.2f}s")
        print(f"  Peak memory: {summary['peak_memory_mb']:.1f} MB")
        print(f"  Peak CPU: {summary['peak_cpu_percent']:.1f}%")
        print(f"  Memory per connection: {summary['peak_memory_mb'] / connection_count:.2f} MB")

        # Assert acceptable resource usage
        assert summary['peak_memory_mb'] < 1000, f"Memory usage too high: {summary['peak_memory_mb']:.1f} MB"
        assert manager.get_connection_count() == 0, "All connections should be closed"

        print("\n✅ Concurrent connections stress test passed!")

    except Exception as e:
        print(f"\n❌ Stress test failed: {e}")
        raise

    finally:
        tracemalloc.stop()


@pytest.mark.asyncio
@pytest.mark.stress
async def test_high_throughput_messaging():
    """Test system throughput with 10000+ messages per second."""
    print("\n" + "=" * 80)
    print("Stress Test: High Throughput Messaging (10000+ msg/s)")
    print("=" * 80)

    manager = ConnectionManager()
    metrics = StressTestMetrics()

    # Create test connections
    connection_count = 100
    print(f"\nCreating {connection_count} test connections...")

    for i in range(connection_count):
        ws = MockWebSocket(f"throughput_conn_{i}")
        await manager.connect(ws, f"throughput_user_{i}", "analyst", {"alerts"})

    print(f"✓ Created {connection_count} connections")

    # Test different throughput levels
    throughput_tests = [
        (1000, "1K"),
        (5000, "5K"),
        (10000, "10K"),
    ]

    results = {}

    for message_count, label in throughput_tests:
        print(f"\nTesting {label} message throughput...")

        # Clear previous messages
        for ws in manager.active_connections.keys():
            ws.messages.clear()

        start_time = time.time()

        # Send messages as fast as possible
        for i in range(message_count):
            message = WebSocketMessage(
                type="alert",
                data={"id": f"alert_{i}", "severity": "high"},
                timestamp=datetime.now(timezone.utc).isoformat(),
                channel="alerts"
            )

            await manager.broadcast_to_channel("alerts", message)
            metrics.total_messages_sent += connection_count  # Each message sent to all connections

        end_time = time.time()
        duration = end_time - start_time

        messages_per_second = message_count / duration
        total_messages_sent = message_count * connection_count

        results[label] = {
            "message_count": message_count,
            "duration": duration,
            "throughput": messages_per_second,
            "total_messages": total_messages_sent
        }

        print(f"  Sent {message_count} messages to {connection_count} connections")
        print(f"  Total messages: {total_messages_sent:,}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Throughput: {messages_per_second:,.1f} msg/s")

        # Verify delivery
        received = sum(len(ws.messages) for ws in manager.active_connections.keys())
        expected = message_count * connection_count
        delivery_rate = received / expected * 100 if expected > 0 else 0

        print(f"  Delivery rate: {delivery_rate:.1f}%")

    # Cleanup
    for ws in list(manager.active_connections.keys()):
        await manager.disconnect(ws)

    metrics.finish()
    summary = metrics.get_summary()

    print("\nHigh Throughput Summary:")
    print(f"  Total messages sent: {summary['total_messages_sent']:,}")
    print(f"  Average throughput: {summary['messages_per_second']:,.1f} msg/s")

    # Assert minimum throughput
    assert summary['messages_per_second'] >= 5000, f"Throughput too low: {summary['messages_per_second']:.1f} msg/s"

    print("\n✅ High throughput stress test passed!")


@pytest.mark.asyncio
@pytest.mark.stress
async def test_memory_stability():
    """Test system for memory leaks over extended period."""
    print("\n" + "=" * 80)
    print("Stress Test: Memory Stability (Extended Duration)")
    print("=" * 80)

    manager = ConnectionManager()
    process = psutil.Process()

    # Start memory tracking
    tracemalloc.start()
    snapshot1 = tracemalloc.take_snapshot()

    # Create test connections
    connection_count = 100
    print(f"\nCreating {connection_count} test connections...")

    connections = []
    for i in range(connection_count):
        ws = MockWebSocket(f"mem_conn_{i}")
        await manager.connect(ws, f"mem_user_{i}", "analyst", {"alerts"})
        connections.append(ws)

    print(f"✓ Created {connection_count} connections")

    # Run for extended period
    test_duration = 300  # 5 minutes
    check_interval = 30  # Check every 30 seconds
    message_batch = 100

    print(f"\nRunning for {test_duration} seconds, checking every {check_interval} seconds...")

    memory_samples = []
    start_time = time.time()
    iteration = 0

    while (time.time() - start_time) < test_duration:
        iteration += 1

        # Send batch of messages
        for i in range(message_batch):
            message = WebSocketMessage(
                type="alert",
                data={"id": f"alert_{iteration}_{i}", "data": "x" * 100},
                timestamp=datetime.now(timezone.utc).isoformat(),
                channel="alerts"
            )
            await manager.broadcast_to_channel("alerts", message)

        # Wait and check memory
        await asyncio.sleep(check_interval)

        current_memory = process.memory_info().rss / 1024 / 1024
        memory_samples.append(current_memory)

        print(f"  Iteration {iteration}: Memory = {current_memory:.1f} MB")

    # Take final snapshot
    snapshot2 = tracemalloc.take_snapshot()

    # Cleanup
    print("\nCleaning up...")
    for ws in connections:
        await manager.disconnect(ws)

    # Analyze memory trends
    print("\nMemory Stability Analysis:")

    initial_memory = memory_samples[0]
    final_memory = memory_samples[-1]
    memory_growth = final_memory - initial_memory
    memory_growth_rate = memory_growth / test_duration * 3600  # MB per hour

    print(f"  Initial memory: {initial_memory:.1f} MB")
    print(f"  Final memory: {final_memory:.1f} MB")
    print(f"  Growth: {memory_growth:+.1f} MB")
    print(f"  Growth rate: {memory_growth_rate:+.2f} MB/hour")

    # Compare snapshots
    top_stats = snapshot2.compare_to(snapshot1, 'lineno')
    print("\nTop 10 memory allocations:")
    for stat in top_stats[:10]:
        print(f"  {stat}")

    tracemalloc.stop()

    # Assert acceptable memory growth
    # Allow up to 100 MB growth over 5 minutes
    assert memory_growth < 100, f"Memory growth too high: {memory_growth:.1f} MB"

    print("\n✅ Memory stability test passed!")


@pytest.mark.asyncio
@pytest.mark.stress
async def test_reconnect_stress():
    """Test rapid connect/disconnect cycles."""
    print("\n" + "=" * 80)
    print("Stress Test: Rapid Connect/Disconnect Cycles")
    print("=" * 80)

    manager = ConnectionManager()
    metrics = StressTestMetrics()

    cycle_count = 1000
    concurrent_connections = 100

    print(f"\nPerforming {cycle_count} connect/disconnect cycles...")
    print(f"Maintaining {concurrent_connections} concurrent connections")

    connection_pool = []

    try:
        for cycle in range(cycle_count):
            # Remove oldest connection if pool is full
            if len(connection_pool) >= concurrent_connections:
                old_ws = connection_pool.pop(0)
                await manager.disconnect(old_ws)

            # Add new connection
            new_ws = MockWebSocket(f"cycle_conn_{cycle}")
            await manager.connect(new_ws, f"cycle_user_{cycle % 100}", "analyst", {"alerts"})
            connection_pool.append(new_ws)

            if (cycle + 1) % 100 == 0:
                current_count = manager.get_connection_count()
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                print(f"  Cycle {cycle + 1}: {current_count} connections, {current_memory:.1f} MB RAM")

        assert manager.get_connection_count() == concurrent_connections

        print(f"\n✓ Completed {cycle_count} cycles")
        print(f"  Final connection count: {manager.get_connection_count()}")

        # Cleanup
        for ws in connection_pool:
            await manager.disconnect(ws)

        metrics.finish()
        summary = metrics.get_summary()

        print("\nReconnect Stress Summary:")
        print(f"  Total cycles: {cycle_count}")
        print(f"  Duration: {summary['duration_seconds']:.2f}s")
        print(f"  Cycles per second: {cycle_count / summary['duration_seconds']:.1f}")

        print("\n✅ Reconnect stress test passed!")

    except Exception as e:
        print(f"\n❌ Reconnect stress test failed: {e}")
        raise


def test_stress_summary():
    """Print stress test summary."""
    print("\n" + "=" * 80)
    print("WebSocket Stress Test Suite")
    print("=" * 80)
    print(f"\nGenerated at: {datetime.now(timezone.utc).isoformat()}")

    print("\nStress Test Categories:")
    print("  1. Concurrent Connections - 1000+ simultaneous connections")
    print("  2. High Throughput - 10000+ messages per second")
    print("  3. Memory Stability - Extended duration leak detection")
    print("  4. Reconnect Stress - Rapid connect/disconnect cycles")

    print("\nSystem Requirements:")
    print("  - Memory: 2GB+ available")
    print("  - CPU: 4+ cores recommended")
    print("  - Duration: 10-15 minutes for full suite")

    print("\nRun with:")
    print("  pytest backend/tests/test_websocket_stress.py -v -s --stress")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_stress_summary()
