"""WebSocket Connection Manager for real-time communication.

Extracted from routers/websocket.py for better code organization.

Features:
- Manage WebSocket connections
- Channel-based subscriptions
- Message broadcasting
- Offline message queuing
- Connection monitoring
"""

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket
from pydantic import BaseModel

from core.logger import get_logger
from models.message_queue import MessageType
from models.websocket_metrics import ErrorType
from services.message_queue import MessageQueueService
from services.observability.websocket_monitoring import get_websocket_monitoring
from services.websocket_compression import get_compression_service

logger = get_logger(__name__)


class WebSocketMessage(BaseModel):
    """WebSocket message format."""

    type: str  # alert, playbook_run, system, ping, pong
    data: dict[str, Any]
    timestamp: str
    channel: str | None = None


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting.

    Features:
    - Connection lifecycle management
    - Channel-based subscriptions
    - Message broadcasting with optional compression
    - Offline message queuing
    - Performance monitoring integration
    """

    def __init__(self):
        # Active connections: {websocket: user_info}
        self.active_connections: dict[WebSocket, dict[str, Any]] = {}
        # Channel subscriptions: {channel: set of websockets}
        self.channel_subscriptions: dict[str, set[WebSocket]] = {
            "alerts": set(),
            "playbook_runs": set(),
            "system": set(),
        }
        # Known users (including offline): {user_id: last_seen}
        self.known_users: dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._user_ttl_seconds = 86400  # 24 hours

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        user_role: str,
        channels: set[str] | None = None,
        message_queue: MessageQueueService | None = None,
    ):
        """Accept a new WebSocket connection and send queued messages."""
        connection_id = f"{user_id}_{int(time.time() * 1000)}"
        await websocket.accept()

        async with self._lock:
            self.active_connections[websocket] = {
                "user_id": user_id,
                "user_role": user_role,
                "connected_at": datetime.now(UTC).isoformat(),
                "channels": channels or {"alerts"},
                "connection_id": connection_id,
            }
            for channel in channels or {"alerts"}:
                if channel in self.channel_subscriptions:
                    self.channel_subscriptions[channel].add(websocket)

        self.known_users[user_id] = datetime.now(UTC).isoformat()
        logger.info(
            f"WebSocket connected: user={user_id}, channels={channels or ['alerts']}"
        )

        try:
            monitoring = get_websocket_monitoring()
            await monitoring.record_connection_established(
                connection_id, user_id, user_role
            )
        except Exception as e:
            logger.warning(f"Failed to record connection in monitoring: {e}")

        await self.send_personal_message(
            websocket,
            WebSocketMessage(
                type="system",
                data={"message": "Connected to SOC Copilot real-time feed"},
                timestamp=datetime.now(UTC).isoformat(),
                channel="system",
            ).model_dump(),
        )

        if message_queue and await message_queue.is_available():
            try:
                queued_messages = await message_queue.get_messages(user_id)
                if queued_messages:
                    logger.info(
                        f"Sending {len(queued_messages)} queued messages to user {user_id}"
                    )
                    for msg in queued_messages:
                        await self.send_personal_message(
                            websocket,
                            WebSocketMessage(
                                type=msg.type.value,
                                data=msg.data,
                                timestamp=msg.timestamp,
                                channel=msg.channel,
                            ).model_dump(),
                        )
                    await self.send_personal_message(
                        websocket,
                        WebSocketMessage(
                            type="system",
                            data={
                                "message": f"Delivered {len(queued_messages)} messages from while you were offline"
                            },
                            timestamp=datetime.now(UTC).isoformat(),
                            channel="system",
                        ).model_dump(),
                    )
            except Exception as e:
                logger.error(f"Error sending queued messages to user {user_id}: {e}")

    async def disconnect(self, websocket: WebSocket, reason: str | None = None):
        """Handle WebSocket disconnection."""
        async with self._lock:
            if websocket in self.active_connections:
                user_info = self.active_connections[websocket]
                connection_id = user_info.get("connection_id")
                user_id = user_info.get("user_id")
                for channel in self.channel_subscriptions.values():
                    channel.discard(websocket)
                del self.active_connections[websocket]
                logger.info(f"WebSocket disconnected: user={user_id}, reason={reason}")
                if connection_id:
                    try:
                        monitoring = get_websocket_monitoring()
                        await monitoring.record_connection_closed(connection_id, reason)
                    except Exception as e:
                        logger.warning(
                            f"Failed to record disconnection in monitoring: {e}"
                        )

    async def send_personal_message(
        self, websocket: WebSocket, message: dict, compress: bool = True
    ):
        """Send a message to a specific client with optional compression."""
        try:
            compression_service = get_compression_service()
            message_with_meta, compressed_data = compression_service.compress_message(
                message
            )
            if compressed_data:
                await websocket.send_text(
                    json.dumps({"_compressed": True, "_data": compressed_data.hex()})
                )
                message_size = message_with_meta.get(
                    "_compressed_size", len(json.dumps(message))
                )
            else:
                await websocket.send_json(message)
                message_size = len(json.dumps(message))
            if websocket in self.active_connections:
                user_info = self.active_connections[websocket]
                connection_id = user_info.get("connection_id")
                if connection_id:
                    try:
                        monitoring = get_websocket_monitoring()
                        await monitoring.record_message_sent(
                            connection_id,
                            message.get("type", "unknown"),
                            message_size,
                            recipients=1,
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record message in monitoring: {e}")
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
            try:
                monitoring = get_websocket_monitoring()
                await monitoring.record_error(
                    ErrorType.MESSAGE_PARSE_ERROR,
                    str(e),
                    is_critical=True,
                    context={"message_type": message.get("type")},
                )
            except Exception:
                pass
            await self.disconnect(websocket, reason="send_error")

    async def broadcast_to_channel(
        self,
        channel: str,
        message: WebSocketMessage,
        message_queue: MessageQueueService | None = None,
    ):
        """Broadcast a message to all clients subscribed to a channel."""
        if channel not in self.channel_subscriptions:
            return
        message_dict = message.model_dump()
        connections = list(self.channel_subscriptions[channel])
        delivered_users = set()
        for websocket in connections:
            try:
                await websocket.send_json(message_dict)
                user_id = self.active_connections.get(websocket, {}).get("user_id")
                if user_id:
                    delivered_users.add(user_id)
            except Exception as e:
                logger.error(f"Failed to broadcast to channel {channel}: {e}")
                await self.disconnect(websocket)
        if message_queue and await message_queue.is_available():
            for user_id in self.known_users:
                if user_id not in delivered_users:
                    try:
                        msg_type = (
                            MessageType(message.type)
                            if message.type in [mt.value for mt in MessageType]
                            else MessageType.ALERT
                        )
                        await message_queue.push_message(
                            user_id=user_id,
                            message_type=msg_type,
                            data=message.data,
                            channel=message.channel or channel,
                        )
                    except Exception as e:
                        logger.error(f"Error queuing message for user {user_id}: {e}")

    async def broadcast_alert(self, alert_data: dict[str, Any]):
        message = WebSocketMessage(
            type="alert",
            data=alert_data,
            timestamp=datetime.now(UTC).isoformat(),
            channel="alerts",
        )
        await self.broadcast_to_channel("alerts", message)

    async def broadcast_playbook_run(self, run_data: dict[str, Any]):
        message = WebSocketMessage(
            type="playbook_run",
            data=run_data,
            timestamp=datetime.now(UTC).isoformat(),
            channel="playbook_runs",
        )
        await self.broadcast_to_channel("playbook_runs", message)

    async def broadcast_system_message(self, message_data: dict[str, Any]):
        message = WebSocketMessage(
            type="system",
            data=message_data,
            timestamp=datetime.now(UTC).isoformat(),
            channel="system",
        )
        await self.broadcast_to_channel("system", message)

    def get_connection_count(self) -> int:
        return len(self.active_connections)

    def get_channel_stats(self) -> dict[str, int]:
        return {
            channel: len(connections)
            for channel, connections in self.channel_subscriptions.items()
        }

    async def send_batch(
        self,
        channel: str,
        messages: list[dict[str, Any]],
        message_queue: MessageQueueService | None = None,
    ):
        if channel not in self.channel_subscriptions:
            return
        connections = list(self.channel_subscriptions[channel])
        delivered_users = set()
        for websocket in connections:
            try:
                for message in messages:
                    await websocket.send_json(message)
                user_id = self.active_connections.get(websocket, {}).get("user_id")
                if user_id:
                    delivered_users.add(user_id)
            except Exception as e:
                logger.error(f"Failed to send batch to channel {channel}: {e}")
                await self.disconnect(websocket)
        if message_queue and await message_queue.is_available():
            for message in messages:
                for user_id in self.known_users:
                    if user_id not in delivered_users:
                        try:
                            msg_type = MessageType(message.get("type", "alert"))
                            if msg_type.value in [mt.value for mt in MessageType]:
                                await message_queue.push_message(
                                    user_id=user_id,
                                    message_type=msg_type,
                                    data=message.get("data", {}),
                                    channel=message.get("channel", channel),
                                )
                        except Exception as e:
                            logger.error(
                                f"Error queuing message for user {user_id}: {e}"
                            )

    async def cleanup_stale_users(self) -> int:
        now = datetime.now(UTC)
        stale_users = []
        for user_id, last_seen_str in self.known_users.items():
            try:
                last_seen = datetime.fromisoformat(last_seen_str.replace("Z", "+00:00"))
                if (now - last_seen).total_seconds() > self._user_ttl_seconds:
                    stale_users.append(user_id)
            except Exception:
                stale_users.append(user_id)
        async with self._lock:
            for user_id in stale_users:
                del self.known_users[user_id]
        if stale_users:
            logger.info(f"Cleaned up {len(stale_users)} stale users from known_users")
        return len(stale_users)


_manager: ConnectionManager | None = None


def get_manager() -> ConnectionManager:
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager
