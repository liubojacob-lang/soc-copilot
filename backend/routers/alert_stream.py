#!/usr/bin/env python3
"""
Wazuh Alert Stream API Routes

API endpoints for real-time Wazuh alert streaming.
"""

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from services.alert_stream_service import (
    get_wazuh_stream_service,
    init_wazuh_stream_service
)
from schemas.wazuh_stream import (
    get_wazuh_stream_service,
    init_wazuh_stream_service
)
    get_wazuh_stream_service,
    init_wazuh_stream_service
)
from services.wazuh_client import get_wazuh_client
from schemas.wazuh_stream import (
    WazuhAlertStream,
    AlertStreamFilter,
    AlertStreamStats,
    WazuhStreamMessage,
    SeverityLevel
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/wazuh/stream", tags=["Wazuh Stream"])


# ========== Request/Response Models ==========


class StreamConfig(BaseModel):
    """Stream service configuration."""
    aggregation_window_seconds: int = 60
    max_buffer_size: int = 10000
    max_history_size: int = 1000


class StreamStartRequest(BaseModel):
    """Request to start the stream service."""
    config: Optional[StreamConfig] = None


class StreamStatusResponse(BaseModel):
    """Stream service status."""
    running: bool
    stats: Optional[AlertStreamStats] = None
    config: Optional[StreamConfig] = None


class TestStreamAlertRequest(BaseModel):
    """Request to send a test stream alert."""
    agent_id: str = "001"
    severity: SeverityLevel = SeverityLevel.HIGH
    event_type: str = "ssh_login"
    count: int = 1


# ========== API Endpoints ==========


@router.post("/start", response_model=StreamStatusResponse)
async def start_stream_service(request: StreamStartRequest = StreamStartRequest()):
    """
    Start the Wazuh alert stream service.

    Initializes the background service for real-time alert streaming.
    """
    try:
        service = get_wazuh_stream_service()

        if service._running:
            return StreamStatusResponse(
                running=True,
                stats=service.get_stats(),
                config=StreamConfig(
                    aggregation_window_seconds=service.aggregation_window.seconds,
                    max_buffer_size=service.max_buffer_size,
                    max_history_size=service.max_history_size
                )
            )

        # Initialize with custom config if provided
        if request.config:
            service = await init_wazuh_stream_service(
                aggregation_window_seconds=request.config.aggregation_window_seconds,
                max_buffer_size=request.config.max_buffer_size,
                max_history_size=request.config.max_history_size
            )
        else:
            service = await init_wazuh_stream_service()

        return StreamStatusResponse(
            running=True,
            stats=service.get_stats(),
            config=request.config or StreamConfig()
        )

    except Exception as e:
        logger.error(f"Error starting stream service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start stream service: {str(e)}"
        )


@router.post("/stop", response_model=StreamStatusResponse)
async def stop_stream_service():
    """
    Stop the Wazuh alert stream service.
    """
    try:
        service = get_wazuh_stream_service()

        if not service._running:
            return StreamStatusResponse(running=False)

        await service.stop()

        return StreamStatusResponse(
            running=False,
            stats=service.get_stats()
        )

    except Exception as e:
        logger.error(f"Error stopping stream service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop stream service: {str(e)}"
        )


@router.get("/status", response_model=StreamStatusResponse)
async def get_stream_status():
    """
    Get the current status of the Wazuh alert stream service.
    """
    try:
        service = get_wazuh_stream_service()

        if not service._running:
            return StreamStatusResponse(running=False)

        return StreamStatusResponse(
            running=True,
            stats=service.get_stats(),
            config=StreamConfig(
                aggregation_window_seconds=service.aggregation_window.seconds,
                max_buffer_size=service.max_buffer_size,
                max_history_size=service.max_history_size
            )
        )

    except Exception as e:
        logger.error(f"Error getting stream status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stream status: {str(e)}"
        )


@router.get("/stats", response_model=AlertStreamStats)
async def get_stream_stats():
    """
    Get detailed stream statistics.
    """
    try:
        service = get_wazuh_stream_service()

        if not service._running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stream service is not running"
            )

        return service.get_stats()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stream stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stream stats: {str(e)}"
        )


@router.get("/history", response_model=List[WazuhAlertStream])
async def get_recent_alerts(
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of alerts to return")
):
    """
    Get recent alerts from the stream history.

    Useful for new clients to catch up on recent alerts.
    """
    try:
        service = get_wazuh_stream_service()

        if not service._running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stream service is not running"
            )

        return service.get_recent_alerts(limit=limit)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recent alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent alerts: {str(e)}"
        )


@router.post("/test-alert", response_model=Dict[str, Any])
async def send_test_alert(request: TestStreamAlertRequest):
    """
    Send a test alert through the stream.

    Useful for testing the WebSocket connection and alert formatting.
    """
    try:
        service = get_wazuh_stream_service()

        if not service._running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stream service is not running"
            )

        # Create test alerts
        alerts_sent = 0
        for i in range(request.count):
            test_alert = WazuhAlertStream(
                id=f"test-{datetime.utcnow().isoformat()}-{i}",
                timestamp=datetime.utcnow(),
                source="wazuh-test",
                severity=request.severity,
                event_type=request.event_type,
                title=f"Test Alert: {request.event_type}",
                rule={
                    "id": 9999,
                    "level": 10 if request.severity == SeverityLevel.HIGH else 5,
                    "description": f"Test alert for {request.event_type}",
                    "groups": ["test"],
                    "mitre": {"id": ["T9999"], "technique": ["Test Technique"]}
                },
                agent={
                    "id": request.agent_id,
                    "name": f"test-agent-{request.agent_id}",
                    "ip": "10.0.0.100",
                    "status": "active"
                },
                full_log=f"This is a test alert for {request.event_type}",
                location="/var/log/test.log",
                mitre={
                    "id": "T9999",
                    "technique": "Test Technique",
                    "tactic": "Test Tactic"
                },
                source_ip="203.0.113.45" if i == 0 else f"203.0.113.{45 + i}",
                iocs=["203.0.113.45"],
                analyzed=True,
                risk_score=75.0
            )

            await service.stream_alert(test_alert)
            alerts_sent += 1

        return {
            "success": True,
            "message": f"Sent {alerts_sent} test alert(s)",
            "alerts_sent": alerts_sent,
            "alert_ids": [f"test-{datetime.utcnow().isoformat()}-{i}" for i in range(request.count)]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send test alert: {str(e)}"
        )


@router.post("/subscribe", response_model=Dict[str, str])
async def subscribe_to_stream(
    client_id: str = Query(..., description="Unique client identifier"),
    filters: AlertStreamFilter = None
):
    """
    Subscribe a client to the stream with optional filters.

    The client_id should be a unique identifier for the WebSocket connection.
    """
    try:
        service = get_wazuh_stream_service()

        if not service._running:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Stream service is not running"
            )

        if filters is None:
            filters = AlertStreamFilter()

        service.subscribe(client_id, filters)

        return {
            "message": "Subscribed to Wazuh alert stream",
            "client_id": client_id,
            "filters": filters.dict() if filters else {}
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing to stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to subscribe to stream: {str(e)}"
        )


@router.delete("/subscribe", response_model=Dict[str, str])
async def unsubscribe_from_stream(
    client_id: str = Query(..., description="Client identifier to unsubscribe")
):
    """
    Unsubscribe a client from the stream.
    """
    try:
        service = get_wazuh_stream_service()
        service.unsubscribe(client_id)

        return {
            "message": "Unsubscribed from Wazuh alert stream",
            "client_id": client_id
        }

    except Exception as e:
        logger.error(f"Error unsubscribing from stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unsubscribe from stream: {str(e)}"
        )


@router.get("/subscriptions", response_model=Dict[str, Dict[str, Any]])
async def get_stream_subscriptions():
    """
    Get all active stream subscriptions.

    Admin endpoint for monitoring active subscriptions.
    """
    try:
        service = get_wazuh_stream_service()

        subscriptions = {}
        for client_id, filters in service._subscriptions.items():
            subscriptions[client_id] = filters.dict() if filters else {}

        return {
            "total_subscriptions": len(subscriptions),
            "subscriptions": subscriptions
        }

    except Exception as e:
        logger.error(f"Error getting subscriptions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get subscriptions: {str(e)}"
        )
