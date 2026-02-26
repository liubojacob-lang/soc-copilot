"""
WebSocket Router for Real-time Alerts.

v0.8.5: Real-time alert push via WebSocket.
- Push new alerts to connected clients
- Support for multiple clients
- Authentication via JWT token
- Channel-based subscriptions (alerts, playbook_runs, system)

v0.9.0: Offline message caching.
- Queue messages for offline clients
- Automatic message delivery on reconnect
- Redis-based message queue

v0.9.1: Monitoring and metrics.
- Real-time metrics collection
- Performance tracking
- Error monitoring

v0.9.2: Performance optimization.
- Message compression
- Batch sending
- Connection pooling
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Optional, Set, Dict, Any, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from pydantic import BaseModel

from core.logger import get_logger, set_request_context, clear_request_context
from core.security import decode_token
from services.message_queue import get_message_queue_service, MessageQueueService
from models.message_queue import QueuedMessage
from services.websocket_monitoring import get_websocket_monitoring
from models.websocket_metrics import ErrorType
from services.websocket_compression import get_compression_service

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


class WebSocketMessage(BaseModel):
    """WebSocket message format."""
    type: str  # alert, playbook_run, system, ping, pong
    data: Dict[str, Any]
    timestamp: str
    channel: Optional[str] = None


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        # Active connections: {websocket: user_info}
        self.active_connections: Dict[WebSocket, Dict[str, Any]] = {}
        # Channel subscriptions: {channel: set of websockets}
        self.channel_subscriptions: Dict[str, Set[WebSocket]] = {
            "alerts": set(),
            "playbook_runs": set(),
            "system": set(),
        }
        # Known users (including offline): {user_id: last_seen}
        self.known_users: Dict[str, str] = {}
        self._lock = asyncio.Lock()
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        user_role: str,
        channels: Optional[Set[str]] = None,
        message_queue: Optional[MessageQueueService] = None,
    ):
        """Accept a new WebSocket connection and send queued messages."""
        connection_id = f"{user_id}_{int(time.time() * 1000)}"

        await websocket.accept()

        async with self._lock:
            self.active_connections[websocket] = {
                "user_id": user_id,
                "user_role": user_role,
                "connected_at": datetime.now(timezone.utc).isoformat(),
                "channels": channels or {"alerts"},
                "connection_id": connection_id,
            }

            # Subscribe to channels
            for channel in (channels or {"alerts"}):
                if channel in self.channel_subscriptions:
                    self.channel_subscriptions[channel].add(websocket)

        # Track known user
        self.known_users[user_id] = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"WebSocket connected: user={user_id}, channels={channels or ['alerts']}"
        )

        # Record connection in monitoring
        try:
            monitoring = get_websocket_monitoring()
            await monitoring.record_connection_established(connection_id, user_id, user_role)
        except Exception as e:
            logger.warning(f"Failed to record connection in monitoring: {e}")

        # Send welcome message
        await self.send_personal_message(
            websocket,
            WebSocketMessage(
                type="system",
                data={"message": "Connected to SOC Copilot real-time feed"},
                timestamp=datetime.now(timezone.utc).isoformat(),
                channel="system",
            ).model_dump()
        )

        # Send queued offline messages
        if message_queue and await message_queue.is_available():
            try:
                queued_messages = await message_queue.get_messages(user_id)
                if queued_messages:
                    logger.info(f"Sending {len(queued_messages)} queued messages to user {user_id}")
                    for msg in queued_messages:
                        await self.send_personal_message(
                            websocket,
                            WebSocketMessage(
                                type=msg.type.value,
                                data=msg.data,
                                timestamp=msg.timestamp,
                                channel=msg.channel,
                            ).model_dump()
                        )

                    # Send notification about queued messages
                    await self.send_personal_message(
                        websocket,
                        WebSocketMessage(
                            type="system",
                            data={
                                "message": f"Delivered {len(queued_messages)} messages from while you were offline"
                            },
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            channel="system",
                        ).model_dump()
                    )
            except Exception as e:
                logger.error(f"Error sending queued messages to user {user_id}: {e}")
    
    async def disconnect(self, websocket: WebSocket, reason: Optional[str] = None):
        """Handle WebSocket disconnection."""
        async with self._lock:
            if websocket in self.active_connections:
                user_info = self.active_connections[websocket]
                connection_id = user_info.get("connection_id")
                user_id = user_info.get("user_id")

                # Unsubscribe from all channels
                for channel in self.channel_subscriptions.values():
                    channel.discard(websocket)

                del self.active_connections[websocket]

                logger.info(
                    f"WebSocket disconnected: user={user_id}, reason={reason}"
                )

                # Record disconnection in monitoring
                if connection_id:
                    try:
                        monitoring = get_websocket_monitoring()
                        await monitoring.record_connection_closed(connection_id, reason)
                    except Exception as e:
                        logger.warning(f"Failed to record disconnection in monitoring: {e}")
    
    async def send_personal_message(
        self,
        websocket: WebSocket,
        message: dict,
        compress: bool = True
    ):
        """Send a message to a specific client with optional compression."""
        try:
            # Try to compress the message
            compression_service = get_compression_service()
            message_with_meta, compressed_data = compression_service.compress_message(message)

            # Send compressed or regular message
            if compressed_data:
                # Send compressed binary message
                await websocket.send_text(
                    json.dumps({
                        "_compressed": True,
                        "_data": compressed_data.hex()  # Send as hex string
                    })
                )
                message_size = message_with_meta.get("_compressed_size", len(json.dumps(message)))
            else:
                # Send regular JSON message
                await websocket.send_json(message)
                message_size = len(json.dumps(message))

            # Record message sent in monitoring
            if websocket in self.active_connections:
                user_info = self.active_connections[websocket]
                connection_id = user_info.get("connection_id")
                if connection_id:
                    try:
                        monitoring = get_websocket_monitoring()
                        message_type = message.get("type", "unknown")
                        await monitoring.record_message_sent(
                            connection_id,
                            message_type,
                            message_size,
                            recipients=1
                        )
                    except Exception as e:
                        logger.warning(f"Failed to record message in monitoring: {e}")

        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")

            # Record error in monitoring
            try:
                monitoring = get_websocket_monitoring()
                await monitoring.record_error(
                    ErrorType.MESSAGE_PARSE_ERROR,
                    str(e),
                    is_critical=True,
                    context={"message_type": message.get("type")}
                )
            except Exception:
                pass

            await self.disconnect(websocket, reason="send_error")
    
    async def broadcast_to_channel(
        self,
        channel: str,
        message: WebSocketMessage,
        message_queue: Optional[MessageQueueService] = None
    ):
        """Broadcast a message to all clients subscribed to a channel.

        For offline clients, queue the message for delivery on reconnect.
        """
        if channel not in self.channel_subscriptions:
            return

        message_dict = message.model_dump()

        # Get connections to send to (copy to avoid modification during iteration)
        connections = list(self.channel_subscriptions[channel])

        # Track which users received the message
        delivered_users = set()

        for websocket in connections:
            try:
                await websocket.send_json(message_dict)
                # Track delivered user
                user_id = self.active_connections.get(websocket, {}).get('user_id')
                if user_id:
                    delivered_users.add(user_id)
            except Exception as e:
                logger.error(f"Failed to broadcast to channel {channel}: {e}")
                await self.disconnect(websocket)

        # Queue message for known users who are offline
        if message_queue and await message_queue.is_available():
            for user_id in self.known_users.keys():
                if user_id not in delivered_users:
                    # User is offline, queue the message
                    try:
                        from models.message_queue import MessageType
                        msg_type = MessageType(message.type) if message.type in [mt.value for mt in MessageType] else MessageType.ALERT

                        await message_queue.push_message(
                            user_id=user_id,
                            message_type=msg_type,
                            data=message.data,
                            channel=message.channel or channel
                        )
                        logger.debug(f"Queued message for offline user {user_id}")
                    except Exception as e:
                        logger.error(f"Error queuing message for user {user_id}: {e}")
    
    async def broadcast_alert(self, alert_data: Dict[str, Any]):
        """Broadcast an alert to all subscribed clients."""
        message = WebSocketMessage(
            type="alert",
            data=alert_data,
            timestamp=datetime.now(timezone.utc).isoformat(),
            channel="alerts",
        )
        await self.broadcast_to_channel("alerts", message)
    
    async def broadcast_playbook_run(self, run_data: Dict[str, Any]):
        """Broadcast a playbook run update to all subscribed clients."""
        message = WebSocketMessage(
            type="playbook_run",
            data=run_data,
            timestamp=datetime.now(timezone.utc).isoformat(),
            channel="playbook_runs",
        )
        await self.broadcast_to_channel("playbook_runs", message)
    
    async def broadcast_system_message(self, message_data: Dict[str, Any]):
        """Broadcast a system message to all subscribed clients."""
        message = WebSocketMessage(
            type="system",
            data=message_data,
            timestamp=datetime.now(timezone.utc).isoformat(),
            channel="system",
        )
        await self.broadcast_to_channel("system", message)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
    
    def get_channel_stats(self) -> Dict[str, int]:
        """Get statistics for each channel."""
        return {
            channel: len(connections)
            for channel, connections in self.channel_subscriptions.items()
        }

    async def send_batch(
        self,
        channel: str,
        messages: List[Dict[str, Any]],
        message_queue: Optional[MessageQueueService] = None
    ):
        """Send a batch of messages to a channel."""
        if channel not in self.channel_subscriptions:
            return

        connections = list(self.channel_subscriptions[channel])
        delivered_users = set()

        for websocket in connections:
            try:
                for message in messages:
                    await websocket.send_json(message)

                user_id = self.active_connections.get(websocket, {}).get('user_id')
                if user_id:
                    delivered_users.add(user_id)

            except Exception as e:
                logger.error(f"Failed to send batch to channel {channel}: {e}")
                await self.disconnect(websocket)

        # Queue for offline users
        if message_queue and await message_queue.is_available():
            for message in messages:
                for user_id in self.known_users.keys():
                    if user_id not in delivered_users:
                        try:
                            from models.message_queue import MessageType
                            msg_type = MessageType(message.get("type", "alert"))
                            if msg_type.value in [mt.value for mt in MessageType]:
                                await message_queue.push_message(
                                    user_id=user_id,
                                    message_type=msg_type,
                                    data=message.get("data", {}),
                                    channel=message.get("channel", channel)
                                )
                        except Exception as e:
                            logger.error(f"Error queuing message for user {user_id}: {e}")


# Global connection manager
_manager: Optional[ConnectionManager] = None


def get_manager() -> ConnectionManager:
    """Get the global connection manager."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


async def push_alert(alert_data: Dict[str, Any]):
    """Push an alert to all connected clients.

    This function can be called from anywhere in the application
    to push alerts to WebSocket clients. Offline clients will have
    the message queued for delivery on reconnect.
    """
    manager = get_manager()
    message_queue = get_message_queue_service()
    await manager.broadcast_alert(alert_data)

    # Also queue for offline users
    if message_queue and await message_queue.is_available():
        from models.message_queue import MessageType
        for user_id in manager.known_users.keys():
            # Check if user is currently connected
            is_connected = any(
                conn.get('user_id') == user_id
                for conn in manager.active_connections.values()
            )
            if not is_connected:
                try:
                    await message_queue.push_message(
                        user_id=user_id,
                        message_type=MessageType.ALERT,
                        data=alert_data,
                        channel="alerts"
                    )
                except Exception as e:
                    logger.error(f"Error queuing alert for user {user_id}: {e}")


async def push_playbook_run_update(run_data: Dict[str, Any]):
    """Push a playbook run update to connected clients."""
    manager = get_manager()
    message_queue = get_message_queue_service()
    await manager.broadcast_playbook_run(run_data)

    # Queue for offline users if queue available
    if message_queue and await message_queue.is_available():
        from models.message_queue import MessageType
        for user_id in manager.known_users.keys():
            is_connected = any(
                conn.get('user_id') == user_id
                for conn in manager.active_connections.values()
            )
            if not is_connected:
                try:
                    await message_queue.push_message(
                        user_id=user_id,
                        message_type=MessageType.PLAYBOOK_RUN,
                        data=run_data,
                        channel="playbook_runs"
                    )
                except Exception as e:
                    logger.error(f"Error queuing playbook run for user {user_id}: {e}")


async def push_system_notification(message: str, level: str = "info"):
    """Push a system notification to connected clients."""
    manager = get_manager()
    await manager.broadcast_system_message({
        "message": message,
        "level": level,
    })


@router.websocket("/ws/alerts")
async def alerts_websocket(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    channels: Optional[str] = Query(None),
):
    """WebSocket endpoint for real-time alerts.
    
    Query Parameters:
        token: JWT authentication token
        channels: Comma-separated list of channels to subscribe to
                  (alerts, playbook_runs, system)
    
    Message Types:
        - alert: New security alert
        - playbook_run: Playbook execution update
        - system: System notification
        - ping/pong: Connection keepalive
    """
    manager = get_manager()
    
    # Authenticate
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return
    
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    user_id = payload.get("sub")
    user_role = payload.get("role")
    
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        return
    
    # Parse channels
    subscribed_channels = set()
    if channels:
        for ch in channels.split(","):
            ch = ch.strip()
            if ch in manager.channel_subscriptions:
                subscribed_channels.add(ch)
    if not subscribed_channels:
        subscribed_channels = {"alerts"}

    # Get message queue service
    message_queue = get_message_queue_service()

    # Connect with message queue for offline messages
    await manager.connect(websocket, user_id, user_role, subscribed_channels, message_queue)
    
    try:
        # Main message loop
        while True:
            # Wait for messages from client
            data = await asyncio.wait_for(
                websocket.receive_text(),
                timeout=60.0  # 60 second timeout
            )
            
            try:
                message = json.loads(data)
                msg_type = message.get("type", "unknown")
                
                # Handle ping/pong for keepalive
                if msg_type == "ping":
                    await manager.send_personal_message(
                        websocket,
                        WebSocketMessage(
                            type="pong",
                            data={"timestamp": datetime.now(timezone.utc).isoformat()},
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        ).model_dump()
                    )
                
                # Handle channel subscription changes
                elif msg_type == "subscribe":
                    new_channels = message.get("channels", [])
                    async with manager._lock:
                        # Unsubscribe from old channels
                        for ch in manager.channel_subscriptions.values():
                            ch.discard(websocket)
                        
                        # Subscribe to new channels
                        for ch in new_channels:
                            if ch in manager.channel_subscriptions:
                                manager.channel_subscriptions[ch].add(websocket)
                        
                        manager.active_connections[websocket]["channels"] = set(new_channels)
                    
                    await manager.send_personal_message(
                        websocket,
                        WebSocketMessage(
                            type="system",
                            data={"message": f"Subscribed to: {', '.join(new_channels)}"},
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            channel="system",
                        ).model_dump()
                    )
                
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    websocket,
                    WebSocketMessage(
                        type="error",
                        data={"message": "Invalid JSON format"},
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ).model_dump()
                )
    
    except asyncio.TimeoutError:
        # Send ping to check connection
        try:
            await manager.send_personal_message(
                websocket,
                WebSocketMessage(
                    type="ping",
                    data={},
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ).model_dump()
            )
        except Exception:
            pass
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    manager = get_manager()
    return {
        "active_connections": manager.get_connection_count(),
        "channels": manager.get_channel_stats(),
    }


@router.get("/ws/monitoring/metrics")
async def get_monitoring_metrics():
    """Get current WebSocket monitoring metrics."""
    try:
        monitoring = get_websocket_monitoring()
        metrics = await monitoring.get_current_metrics()
        return metrics.model_dump()
    except Exception as e:
        logger.error(f"Failed to get monitoring metrics: {e}")
        return {
            "error": str(e),
            "health_score": 100.0,
            "connection": {},
            "message": {},
            "error": {},
            "performance": {}
        }


@router.get("/ws/monitoring/health")
async def get_monitoring_health():
    """Get WebSocket system health score."""
    try:
        monitoring = get_websocket_monitoring()
        health_score = await monitoring.get_health_score()
        return {
            "health_score": health_score,
            "status": "healthy" if health_score >= 70 else "degraded" if health_score >= 50 else "critical"
        }
    except Exception as e:
        logger.error(f"Failed to get health score: {e}")
        return {
            "health_score": 0.0,
            "status": "error",
            "error": str(e)
        }


@router.get("/ws/monitoring/summary")
async def get_monitoring_summary():
    """Get WebSocket monitoring summary."""
    try:
        monitoring = get_websocket_monitoring()
        summary = await monitoring.get_metrics_summary()
        return summary
    except Exception as e:
        logger.error(f"Failed to get monitoring summary: {e}")
        return {
            "error": str(e),
            "health_score": 100.0,
            "active_connections": 0,
            "total_messages": 0,
            "total_errors": 0,
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0
        }


@router.get("/ws/compression/stats")
async def get_compression_stats():
    """Get message compression statistics."""
    try:
        compression_service = get_compression_service()
        stats = compression_service.get_stats()
        return stats.model_dump()
    except Exception as e:
        logger.error(f"Failed to get compression stats: {e}")
        return {
            "total_messages": 0,
            "compressed_messages": 0,
            "compression_ratio": 0.0,
            "bytes_saved": 0
        }


@router.post("/ws/compression/reset-stats")
async def reset_compression_stats():
    """Reset compression statistics."""
    try:
        compression_service = get_compression_service()
        compression_service.reset_stats()
        return {"message": "Compression statistics reset successfully"}
    except Exception as e:
        logger.error(f"Failed to reset compression stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset stats: {str(e)}")


@router.get("/ws/batch/stats")
async def get_batch_stats():
    """Get message batching statistics."""
    try:
        from services.message_batch_service import get_batch_service
        batch_service = get_batch_service()
        stats = batch_service.get_stats()
        return stats.model_dump()
    except Exception as e:
        logger.error(f"Failed to get batch stats: {e}")
        return {
            "total_batches": 0,
            "total_messages_batched": 0,
            "avg_batch_size": 0.0
        }


@router.post("/ws/batch/flush")
async def flush_batches():
    """Manually flush all pending message batches."""
    try:
        from services.message_batch_service import get_batch_service
        batch_service = get_batch_service()
        await batch_service.flush_all()
        return {"message": "All batches flushed successfully"}
    except Exception as e:
        logger.error(f"Failed to flush batches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to flush batches: {str(e)}")


@router.get("/ws/pool/stats")
async def get_pool_stats():
    """Get connection pool statistics."""
    try:
        from services.websocket_connection_pool import get_connection_pool
        pool_service = get_connection_pool()
        stats = pool_service.get_stats()
        return stats.model_dump()
    except Exception as e:
        logger.error(f"Failed to get pool stats: {e}")
        return {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "unhealthy_connections": 0
        }
