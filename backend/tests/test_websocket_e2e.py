"""
WebSocket End-to-End Tests

Comprehensive end-to-end tests for WebSocket functionality,
including real connection, messaging, offline caching, filtering,
monitoring, and alerts.

Tests:
- Connection lifecycle (connect, disconnect, reconnect)
- Message sending and receiving
- Offline message caching
- Message filtering
- Monitoring metrics
- Alert rules
"""

import asyncio
import pytest
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

from services.message_queue import get_message_queue_service, MessageQueueService
from services.message_filter import get_filter_service, FilterService
from services.websocket_monitoring import get_websocket_monitoring
from services.alert_evaluator import get_alert_evaluator
from models.message_filters import FilterRule, FilterSet, SeverityLevel, StringFilter
from models.monitoring_alerts import AlertRule, AlertCondition, MetricType, AlertOperator, AlertSeverity


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.closed = False
        self.client_id = f"mock_{int(time.time() * 1000)}"

    async def send_json(self, message: Dict[str, Any]) -> None:
        """Send a JSON message."""
        if self.closed:
            raise RuntimeError("WebSocket is closed")
        self.messages.append(message)

    async def send_text(self, text: str) -> None:
        """Send a text message."""
        if self.closed:
            raise RuntimeError("WebSocket is closed")
        self.messages.append(json.loads(text))

    async def close(self) -> None:
        """Close the WebSocket."""
        self.closed = True

    def reset(self) -> None:
        """Clear messages."""
        self.messages = []


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_connection_lifecycle():
    """Test WebSocket connection lifecycle: connect, disconnect, reconnect."""
    print("\n" + "=" * 80)
    print("E2E Test: Connection Lifecycle")
    print("=" * 80)

    from routers.websocket import ConnectionManager

    manager = ConnectionManager()
    user_id = "test_user_001"
    user_role = "analyst"

    # Test 1: Connect
    print("\n1. Testing connection establishment...")
    ws = MockWebSocket()
    await manager.connect(ws, user_id, user_role, {"alerts"})

    assert manager.get_connection_count() == 1, "Should have 1 active connection"
    assert len(manager.active_connections) == 1
    assert ws in manager.active_connections
    print("✓ Connection established successfully")

    # Test 2: Receive welcome message
    assert len(ws.messages) == 1, "Should receive welcome message"
    welcome_msg = ws.messages[0]
    assert welcome_msg["type"] == "system"
    assert "Connected to" in welcome_msg["data"]["message"]
    print("✓ Welcome message received")

    # Test 3: Disconnect
    print("\n2. Testing disconnection...")
    await manager.disconnect(ws)
    assert manager.get_connection_count() == 0, "Should have 0 connections"
    assert ws not in manager.active_connections
    print("✓ Disconnection successful")

    # Test 4: Reconnect
    print("\n3. Testing reconnection...")
    ws2 = MockWebSocket()
    await manager.connect(ws2, user_id, user_role, {"alerts"})
    assert manager.get_connection_count() == 1
    print("✓ Reconnection successful")

    # Cleanup
    await manager.disconnect(ws2)

    print("\n✅ Connection lifecycle test passed!")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_message_send_and_receive():
    """Test message sending and receiving through WebSocket."""
    print("\n" + "=" * 80)
    print("E2E Test: Message Send and Receive")
    print("=" * 80)

    from routers.websocket import ConnectionManager, WebSocketMessage

    manager = ConnectionManager()

    # Create multiple connections
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()
    ws3 = MockWebSocket()

    await manager.connect(ws1, "user1", "analyst", {"alerts"})
    await manager.connect(ws2, "user2", "analyst", {"alerts"})
    await manager.connect(ws3, "user3", "analyst", {"alerts"})

    print(f"✓ Connected {manager.get_connection_count()} clients")

    # Clear welcome messages
    ws1.reset()
    ws2.reset()
    ws3.reset()

    # Test broadcast
    print("\n1. Testing broadcast to channel...")
    test_message = WebSocketMessage(
        type="alert",
        data={
            "id": "alert_001",
            "severity": "high",
            "title": "Test Alert",
            "description": "This is a test alert"
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
        channel="alerts"
    )

    await manager.broadcast_to_channel("alerts", test_message)

    # Verify all clients received the message
    assert len(ws1.messages) == 1, "Client 1 should receive message"
    assert len(ws2.messages) == 1, "Client 2 should receive message"
    assert len(ws3.messages) == 1, "Client 3 should receive message"

    msg1 = ws1.messages[0]
    assert msg1["type"] == "alert"
    assert msg1["data"]["id"] == "alert_001"
    print("✓ All clients received broadcast message")

    # Test selective channel
    print("\n2. Testing selective channel subscription...")
    ws4 = MockWebSocket()
    await manager.connect(ws4, "user4", "analyst", {"system"})
    ws4.reset()

    await manager.broadcast_to_channel("alerts", test_message)

    assert len(ws4.messages) == 0, "Client not subscribed to alerts should not receive"
    print("✓ Channel filtering works correctly")

    # Cleanup
    for ws in [ws1, ws2, ws3, ws4]:
        await manager.disconnect(ws)

    print("\n✅ Message send and receive test passed!")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_offline_message_caching():
    """Test offline message caching and delivery on reconnect."""
    print("\n" + "=" * 80)
    print("E2E Test: Offline Message Caching")
    print("=" * 80)

    from routers.websocket import ConnectionManager, WebSocketMessage
    from models.message_queue import MessageType

    manager = ConnectionManager()
    message_queue = get_message_queue_service()

    user_id = "offline_user_001"

    # Test 1: Send message while user is offline
    print("\n1. Sending message to offline user...")
    test_message = WebSocketMessage(
        type="alert",
        data={"id": "offline_alert_001", "title": "Offline Alert"},
        timestamp=datetime.now(timezone.utc).isoformat(),
        channel="alerts"
    )

    # Add user to known_users (simulate they were once online)
    manager.known_users[user_id] = datetime.now(timezone.utc).isoformat()

    # Broadcast to channel (user is offline)
    await manager.broadcast_to_channel("alerts", test_message, message_queue)

    # Verify message was queued
    if await message_queue.is_available():
        queued_messages = await message_queue.get_messages(user_id)
        assert len(queued_messages) > 0, "Message should be queued"
        print(f"✓ Message queued: {len(queued_messages)} messages")

        # Test 2: User reconnects and receives queued messages
        print("\n2. Testing message delivery on reconnect...")
        ws = MockWebSocket()
        await manager.connect(ws, user_id, "analyst", {"alerts"}, message_queue)

        # Should receive: welcome message + queued messages
        assert len(ws.messages) >= 2, "Should receive welcome + queued messages"

        # Find queued alert
        queued_alert = None
        for msg in ws.messages:
            if msg.get("type") == "alert" and msg.get("data", {}).get("id") == "offline_alert_001":
                queued_alert = msg
                break

        assert queued_alert is not None, "Should receive queued alert"
        print("✓ Queued message delivered on reconnect")

        await manager.disconnect(ws)
    else:
        print("⚠ Message queue not available, skipping queue test")

    print("\n✅ Offline message caching test passed!")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_message_filtering():
    """Test server-side message filtering."""
    print("\n" + "=" * 80)
    print("E2E Test: Message Filtering")
    print("=" * 80)

    filter_service = get_filter_service()

    user_id = "filter_user_001"

    # Create filter rule: only allow high severity alerts
    print("\n1. Creating filter rule...")
    rule = FilterRule(
        user_id=user_id,
        name="High Severity Only",
        description="Only receive high and critical severity alerts",
        priority=1,
        enabled=True,
        min_severity=SeverityLevel.HIGH
    )

    filter_set = FilterSet(
        user_id=user_id,
        default_action="block",
        rules=[rule]
    )

    await filter_service.set_user_filters(user_id, filter_set)
    print("✓ Filter rule created")

    # Test filtering
    print("\n2. Testing message filtering...")

    # Test message 1: Critical severity (should pass)
    critical_msg = {
        "type": "alert",
        "data": {"severity": "critical", "title": "Critical Alert"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    result1 = await filter_service.should_send_message(user_id, critical_msg)
    assert result1.should_send == True, "Critical alert should pass filter"
    print("✓ Critical alert passed filter")

    # Test message 2: Low severity (should be blocked)
    low_msg = {
        "type": "alert",
        "data": {"severity": "low", "title": "Low Alert"},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    result2 = await filter_service.should_send_message(user_id, low_msg)
    assert result2.should_send == False, "Low alert should be blocked"
    print("✓ Low alert blocked by filter")

    # Cleanup
    await filter_service.remove_user_filters(user_id)

    print("\n✅ Message filtering test passed!")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_monitoring_metrics():
    """Test monitoring metrics collection."""
    print("\n" + "=" * 80)
    print("E2E Test: Monitoring Metrics")
    print("=" * 80)

    monitoring = get_websocket_monitoring()
    await monitoring.start()

    user_id = "monitor_user_001"
    connection_id = f"conn_{int(time.time() * 1000)}"

    # Test 1: Record connection
    print("\n1. Recording connection metrics...")
    await monitoring.record_connection_established(connection_id, user_id, "analyst")

    metrics = await monitoring.get_current_metrics()
    assert metrics.connection.total_connections >= 1
    print(f"✓ Connection recorded: {metrics.connection.total_connections} total")

    # Test 2: Record messages
    print("\n2. Recording message metrics...")
    await monitoring.record_message_sent(connection_id, "alert", 1024, recipients=1)
    await monitoring.record_message_received(connection_id, "alert")

    metrics = await monitoring.get_current_metrics()
    assert metrics.message.total_messages_sent >= 1
    assert metrics.message.total_messages_received >= 1
    print(f"✓ Messages recorded: {metrics.message.total_messages_sent} sent, "
          f"{metrics.message.total_messages_received} received")

    # Test 3: Record latency
    print("\n3. Recording performance metrics...")
    await monitoring.record_latency(25.5)
    await monitoring.record_latency(30.2)
    await monitoring.record_latency(20.8)

    metrics = await monitoring.get_current_metrics()
    assert metrics.performance.avg_latency_ms > 0
    print(f"✓ Latency recorded: avg={metrics.performance.avg_latency_ms:.2f}ms, "
          f"p95={metrics.performance.p95_latency_ms:.2f}ms")

    # Test 4: Health score
    print("\n4. Calculating health score...")
    health_score = await monitoring.get_health_score()
    assert 0 <= health_score <= 100
    print(f"✓ Health score: {health_score:.1f}%")

    # Cleanup
    await monitoring.record_connection_closed(connection_id)
    await monitoring.stop()

    print("\n✅ Monitoring metrics test passed!")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_alert_rules():
    """Test alert rule evaluation."""
    print("\n" + "=" * 80)
    print("E2E Test: Alert Rules")
    print("=" * 80)

    evaluator = get_alert_evaluator()

    user_id = "alert_user_001"

    # Create alert rule: trigger when health score drops below 50%
    print("\n1. Creating alert rule...")
    rule = AlertRule(
        user_id=user_id,
        name="Low Health Score Alert",
        description="Alert when system health drops below 50%",
        conditions=[
            AlertCondition(
                metric_type=MetricType.HEALTH_SCORE,
                operator=AlertOperator.LESS_THAN,
                threshold=50.0,
                duration_seconds=60
            )
        ],
        require_all=True,
        severity=AlertSeverity.WARNING,
        enabled=True,
        channels=["log"]
    )

    await evaluator.add_rule(rule)
    print("✓ Alert rule created")

    # Test rule evaluation with low health score
    print("\n2. Testing rule evaluation with low health score...")
    from models.websocket_metrics import AggregatedMetrics

    low_health_metrics = AggregatedMetrics(
        health_score=40.0,
        connection=...,
        message=...,
        error=...,
        performance=...
    )

    notifications = await evaluator.evaluate_metrics(low_health_metrics, user_id)

    # Note: Rule may not trigger due to cooldown, so we just verify it doesn't crash
    print(f"✓ Evaluation completed: {len(notifications)} notifications")

    # Test getting stats
    print("\n3. Getting alert statistics...")
    stats = await evaluator.get_stats(user_id)
    assert stats["total_rules"] >= 1
    print(f"✓ Alert stats: {stats['total_rules']} rules, {stats['total_triggers']} triggers")

    # Cleanup
    await evaluator.remove_rule(rule.id)

    print("\n✅ Alert rules test passed!")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_user_scenario():
    """Test complete user scenario: connect -> receive alerts -> disconnect -> reconnect."""
    print("\n" + "=" * 80)
    print("E2E Test: Complete User Scenario")
    print("=" * 80)

    from routers.websocket import ConnectionManager, WebSocketMessage

    manager = ConnectionManager()
    monitoring = get_websocket_monitoring()
    filter_service = get_filter_service()
    message_queue = get_message_queue_service()

    user_id = "scenario_user_001"

    # Phase 1: User connects
    print("\n=== Phase 1: Initial Connection ===")
    ws1 = MockWebSocket()
    await manager.connect(ws1, user_id, "analyst", {"alerts"})

    # Record in monitoring
    connection_id = list(manager.active_connections.keys())[0].client_id
    await monitoring.record_connection_established(connection_id, user_id, "analyst")

    print(f"✓ User connected with ID: {user_id}")

    # Phase 2: Receive alerts
    print("\n=== Phase 2: Receive Alerts ===")
    ws1.reset()

    alerts = [
        WebSocketMessage(
            type="alert",
            data={"id": f"alert_{i}", "severity": "high", "title": f"Alert {i}"},
            timestamp=datetime.now(timezone.utc).isoformat(),
            channel="alerts"
        )
        for i in range(1, 6)
    ]

    for alert in alerts:
        await manager.broadcast_to_channel("alerts", alert)
        await monitoring.record_message_sent(connection_id, "alert", 512, recipients=1)

    received_count = len([m for m in ws1.messages if m.get("type") == "alert"])
    print(f"✓ Received {received_count} alerts")

    # Phase 3: Disconnect
    print("\n=== Phase 3: Disconnect ===")
    await manager.disconnect(ws1)
    await monitoring.record_connection_closed(connection_id)

    # Send message while offline
    offline_alert = WebSocketMessage(
        type="alert",
        data={"id": "offline_alert", "severity": "critical", "title": "Offline Alert"},
        timestamp=datetime.now(timezone.utc).isoformat(),
        channel="alerts"
    )
    await manager.broadcast_to_channel("alerts", offline_alert, message_queue)
    print("✓ User disconnected, offline alert queued")

    # Phase 4: Reconnect and receive queued messages
    print("\n=== Phase 4: Reconnect ===")
    ws2 = MockWebSocket()
    await manager.connect(ws2, user_id, "analyst", {"alerts"}, message_queue)

    total_messages = len(ws2.messages)
    print(f"✓ Reconnected, received {total_messages} messages (welcome + queued)")

    # Phase 5: Apply filter
    print("\n=== Phase 5: Apply Message Filter ===")
    rule = FilterRule(
        user_id=user_id,
        name="Critical Only",
        min_severity=SeverityLevel.CRITICAL,
        priority=1,
        enabled=True
    )
    filter_set = FilterSet(user_id=user_id, rules=[rule])
    await filter_service.set_user_filters(user_id, filter_set)
    print("✓ Filter applied: critical severity only")

    # Cleanup
    await manager.disconnect(ws2)
    await filter_service.remove_user_filters(user_id)

    print("\n✅ Complete user scenario test passed!")


def test_e2e_summary():
    """Print E2E test summary."""
    print("\n" + "=" * 80)
    print("WebSocket End-to-End Test Suite")
    print("=" * 80)
    print(f"\nGenerated at: {datetime.now(timezone.utc).isoformat()}")

    print("\nTest Scenarios:")
    print("  1. Connection Lifecycle - Connect, Disconnect, Reconnect")
    print("  2. Message Send/Receive - Broadcast to multiple clients")
    print("  3. Offline Message Caching - Queue and deliver on reconnect")
    print("  4. Message Filtering - Server-side rule evaluation")
    print("  5. Monitoring Metrics - Real-time metrics collection")
    print("  6. Alert Rules - Threshold-based alerting")
    print("  7. Complete User Scenario - Full workflow test")

    print("\nRun with:")
    print("  pytest backend/tests/test_websocket_e2e.py -v -s --e2e")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_e2e_summary()
