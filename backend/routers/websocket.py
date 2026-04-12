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
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from core.logger import get_logger
from core.security import decode_token
from dependencies.auth import get_current_user
from services.message_queue import get_message_queue_service
from services.observability.websocket_monitoring import get_websocket_monitoring
from services.websocket_compression import get_compression_service

# Import ConnectionManager from extracted service
from services.websocket_manager import WebSocketMessage, get_manager

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


async def push_alert(alert_data: dict[str, Any]):
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
                conn.get("user_id") == user_id
                for conn in manager.active_connections.values()
            )
            if not is_connected:
                try:
                    await message_queue.push_message(
                        user_id=user_id,
                        message_type=MessageType.ALERT,
                        data=alert_data,
                        channel="alerts",
                    )
                except Exception as e:
                    logger.error(f"Error queuing alert for user {user_id}: {e}")


async def push_playbook_run_update(run_data: dict[str, Any]):
    """Push a playbook run update to connected clients."""
    manager = get_manager()
    message_queue = get_message_queue_service()
    await manager.broadcast_playbook_run(run_data)

    # Queue for offline users if queue available
    if message_queue and await message_queue.is_available():
        from models.message_queue import MessageType

        for user_id in manager.known_users.keys():
            is_connected = any(
                conn.get("user_id") == user_id
                for conn in manager.active_connections.values()
            )
            if not is_connected:
                try:
                    await message_queue.push_message(
                        user_id=user_id,
                        message_type=MessageType.PLAYBOOK_RUN,
                        data=run_data,
                        channel="playbook_runs",
                    )
                except Exception as e:
                    logger.error(f"Error queuing playbook run for user {user_id}: {e}")


async def push_system_notification(message: str, level: str = "info"):
    """Push a system notification to connected clients."""
    manager = get_manager()
    await manager.broadcast_system_message(
        {
            "message": message,
            "level": level,
        }
    )


@router.websocket("/ws/alerts")
async def alerts_websocket(
    websocket: WebSocket,
    channels: str | None = Query(None),
):
    """WebSocket endpoint for real-time alerts.

    Query Parameters:
        channels: Comma-separated list of channels to subscribe to
                  (alerts, playbook_runs, system)

    Authentication:
        Token is passed via Sec-WebSocket-Protocol header as "access_token.<jwt>"
        This avoids exposing the token in URL query parameters (server logs, browser history).

    Message Types:
        - alert: New security alert
        - playbook_run: Playbook execution update
        - system: System notification
        - ping/pong: Connection keepalive
    """
    manager = get_manager()

    # Extract token from Sec-WebSocket-Protocol header
    # Client sends: new WebSocket(url, "access_token.<jwt>")
    token = None
    protocol_header = websocket.headers.get("sec-websocket-protocol", "")
    for proto in protocol_header.split(","):
        proto = proto.strip()
        if proto.startswith("access_token."):
            token = proto[len("access_token.") :]
            break

    # Fallback: also accept token via query parameter for backward compatibility
    if not token:
        token = websocket.query_params.get("token")

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
    await manager.connect(
        websocket, user_id, user_role, subscribed_channels, message_queue
    )

    try:
        # Main message loop
        while True:
            # Wait for messages from client
            data = await asyncio.wait_for(
                websocket.receive_text(), timeout=60.0  # 60 second timeout
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
                            data={"timestamp": datetime.now(UTC).isoformat()},
                            timestamp=datetime.now(UTC).isoformat(),
                        ).model_dump(),
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

                        manager.active_connections[websocket]["channels"] = set(
                            new_channels
                        )

                    await manager.send_personal_message(
                        websocket,
                        WebSocketMessage(
                            type="system",
                            data={
                                "message": f"Subscribed to: {', '.join(new_channels)}"
                            },
                            timestamp=datetime.now(UTC).isoformat(),
                            channel="system",
                        ).model_dump(),
                    )

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    websocket,
                    WebSocketMessage(
                        type="error",
                        data={"message": "Invalid JSON format"},
                        timestamp=datetime.now(UTC).isoformat(),
                    ).model_dump(),
                )

    except TimeoutError:
        # Send ping to check connection
        try:
            await manager.send_personal_message(
                websocket,
                WebSocketMessage(
                    type="ping",
                    data={},
                    timestamp=datetime.now(UTC).isoformat(),
                ).model_dump(),
            )
        except Exception:
            pass

    except WebSocketDisconnect:
        await manager.disconnect(websocket)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


@router.get("/ws/stats")
async def get_websocket_stats(user=Depends(get_current_user)):
    """Get WebSocket connection statistics."""
    manager = get_manager()
    return {
        "active_connections": manager.get_connection_count(),
        "channels": manager.get_channel_stats(),
    }


@router.get("/ws/monitoring/metrics")
async def get_monitoring_metrics(user=Depends(get_current_user)):
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
            "performance": {},
        }


@router.get("/ws/monitoring/health")
async def get_monitoring_health(user=Depends(get_current_user)):
    """Get WebSocket system health score."""
    try:
        monitoring = get_websocket_monitoring()
        health_score = await monitoring.get_health_score()
        return {
            "health_score": health_score,
            "status": (
                "healthy"
                if health_score >= 70
                else "degraded" if health_score >= 50 else "critical"
            ),
        }
    except Exception as e:
        logger.error(f"Failed to get health score: {e}")
        return {"health_score": 0.0, "status": "error", "error": str(e)}


@router.get("/ws/monitoring/summary")
async def get_monitoring_summary(user=Depends(get_current_user)):
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
            "p95_latency_ms": 0.0,
        }


@router.get("/ws/compression/stats")
async def get_compression_stats(user=Depends(get_current_user)):
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
            "bytes_saved": 0,
        }


@router.post("/ws/compression/reset-stats")
async def reset_compression_stats(user=Depends(get_current_user)):
    """Reset compression statistics."""
    try:
        compression_service = get_compression_service()
        compression_service.reset_stats()
        return {"message": "Compression statistics reset successfully"}
    except Exception as e:
        logger.error(f"Failed to reset compression stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset stats: {e!s}")


@router.get("/ws/batch/stats")
async def get_batch_stats(user=Depends(get_current_user)):
    """Get message batching statistics."""
    try:
        from services.message_batch_service import get_batch_service

        batch_service = get_batch_service()
        stats = batch_service.get_stats()
        return stats.model_dump()
    except Exception as e:
        logger.error(f"Failed to get batch stats: {e}")
        return {"total_batches": 0, "total_messages_batched": 0, "avg_batch_size": 0.0}


@router.post("/ws/batch/flush")
async def flush_batches(user=Depends(get_current_user)):
    """Manually flush all pending message batches."""
    try:
        from services.message_batch_service import get_batch_service

        batch_service = get_batch_service()
        await batch_service.flush_all()
        return {"message": "All batches flushed successfully"}
    except Exception as e:
        logger.error(f"Failed to flush batches: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to flush batches: {e!s}"
        )


@router.get("/ws/pool/stats")
async def get_pool_stats(user=Depends(get_current_user)):
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
            "unhealthy_connections": 0,
        }
