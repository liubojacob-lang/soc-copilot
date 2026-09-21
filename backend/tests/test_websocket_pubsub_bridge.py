"""
Unit tests for WebSocket ConnectionManager Redis Pub/Sub multi-instance broadcast bridge.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.websocket_manager import ConnectionManager, WebSocketMessage


@pytest.fixture
def connection_manager():
    return ConnectionManager()


@pytest.mark.asyncio
class TestWebSocketPubSubBridge:
    """Test multi-instance WebSocket Redis Pub/Sub broadcast bridge."""

    async def test_start_pubsub_no_redis(self, connection_manager):
        """Should fall back to single-instance mode when Redis is None."""
        await connection_manager.start_pubsub(redis_client=None)
        assert connection_manager._pubsub_task is None
        assert connection_manager._redis_client is None

    async def test_start_and_stop_pubsub(self, connection_manager):
        """Should start background task and clean up on stop."""
        mock_redis = MagicMock()
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub

        # Create a mock listen generator that stays open until cancelled
        async def fake_listen():
            while True:
                await asyncio.sleep(0.1)
                yield {"type": "ping"}

        mock_pubsub.listen = fake_listen

        await connection_manager.start_pubsub(redis_client=mock_redis)
        assert connection_manager._pubsub_task is not None
        assert not connection_manager._pubsub_task.done()

        await connection_manager.stop_pubsub()
        assert connection_manager._pubsub_task is None

    async def test_broadcast_publishes_to_redis(self, connection_manager):
        """broadcast_to_channel should deliver locally and publish to Redis Pub/Sub."""
        mock_redis = AsyncMock()
        connection_manager._redis_client = mock_redis

        # Mock local websocket
        mock_ws = AsyncMock()
        connection_manager.channel_subscriptions["alerts"].add(mock_ws)
        connection_manager.active_connections[mock_ws] = {
            "user_id": "user-001",
            "channels": {"alerts"},
        }

        msg = WebSocketMessage(
            type="alert",
            data={"alert_id": "alt-999", "severity": "high"},
            timestamp="2026-09-04T12:00:00Z",
            channel="alerts",
        )

        await connection_manager.broadcast_to_channel(
            channel="alerts",
            message=msg,
            publish_to_redis=True,
        )

        # 1. Local delivery verified
        mock_ws.send_json.assert_awaited_once()

        # 2. Redis publish verified
        mock_redis.publish.assert_awaited_once()
        call_args = mock_redis.publish.call_args[0]
        assert call_args[0] == "ws:broadcast"
        published_payload = json.loads(call_args[1])
        assert published_payload["sender_id"] == connection_manager._instance_id
        assert published_payload["channel"] == "alerts"
        assert published_payload["message"]["data"]["alert_id"] == "alt-999"

    async def test_broadcast_publish_disabled(self, connection_manager):
        """When publish_to_redis is False, Redis publish should be skipped."""
        mock_redis = AsyncMock()
        connection_manager._redis_client = mock_redis

        mock_ws = AsyncMock()
        connection_manager.channel_subscriptions["alerts"].add(mock_ws)

        msg = WebSocketMessage(
            type="alert",
            data={"alert_id": "alt-888"},
            timestamp="2026-09-04T12:00:00Z",
            channel="alerts",
        )

        await connection_manager.broadcast_to_channel(
            channel="alerts",
            message=msg,
            publish_to_redis=False,
        )

        mock_ws.send_json.assert_awaited_once()
        mock_redis.publish.assert_not_awaited()

    async def test_pubsub_listener_processes_peer_message(self, connection_manager):
        """Peer instance messages should be delivered locally; self messages ignored."""
        mock_ws = AsyncMock()
        connection_manager.channel_subscriptions["alerts"].add(mock_ws)

        mock_redis = MagicMock()
        mock_pubsub = AsyncMock()
        mock_redis.pubsub.return_value = mock_pubsub

        peer_payload = json.dumps(
            {
                "sender_id": "other-peer-instance-999",
                "channel": "alerts",
                "message": {
                    "type": "alert",
                    "data": {"title": "Peer Pod Alert"},
                    "timestamp": "2026-09-04T12:00:00Z",
                },
            }
        )

        self_payload = json.dumps(
            {
                "sender_id": connection_manager._instance_id,  # Echo from self
                "channel": "alerts",
                "message": {
                    "type": "alert",
                    "data": {"title": "Self Echo Alert"},
                    "timestamp": "2026-09-04T12:00:00Z",
                },
            }
        )

        async def mock_listen():
            # 1. Message from peer
            yield {"type": "message", "data": peer_payload}
            # 2. Echo message from self (must be ignored)
            yield {"type": "message", "data": self_payload}
            # 3. Non-message event (e.g. subscribe confirmation)
            yield {"type": "subscribe", "data": 1}

        mock_pubsub.listen = mock_listen

        connection_manager._redis_client = mock_redis
        listener_task = asyncio.create_task(connection_manager._pubsub_listener())
        await asyncio.sleep(0.05)
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass

        # Only peer message should have been delivered to local client
        assert mock_ws.send_json.await_count == 1
        delivered = mock_ws.send_json.call_args[0][0]
        assert delivered["data"]["title"] == "Peer Pod Alert"
