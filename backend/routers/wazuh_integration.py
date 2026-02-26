#!/usr/bin/env python3
"""
Wazuh Integration API Routes
API endpoints for Wazuh integration management and testing
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from services.wazuh_client import get_wazuh_client, WazuhClient
from services.wazuh_alert_mapper import get_alert_mapper
from services.wazuh_log_receiver import get_wazuh_receiver, init_wazuh_receiver
from services.message_queue_manager import get_message_queue_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/wazuh", tags=["Wazuh Integration"])


# ========== Request/Response Models ==========


class WazuhHealthCheck(BaseModel):
    """Health check response"""
    healthy: bool
    api_url: str
    message: str


class AgentInfo(BaseModel):
    """Agent information"""
    id: str
    name: str
    ip: str
    status: str
    os: Optional[Dict[str, str]] = None
    version: Optional[str] = None


class AlertsRequest(BaseModel):
    """Alerts query request"""
    limit: int = 100
    offset: int = 0
    agent_id: Optional[str] = None
    level: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class TestAlertRequest(BaseModel):
    """Test alert creation request"""
    agent_id: str = "001"
    rule_id: int = 5710  # SSH brute force
    severity: str = "high"


class ReceiverConfig(BaseModel):
    """Receiver configuration"""
    enabled: bool
    poll_interval: int
    batch_size: int
    lookback_minutes: int


class ReceiverStats(BaseModel):
    """Receiver statistics"""
    is_running: bool
    enabled: bool
    poll_interval: int
    batch_size: int
    last_poll_time: Optional[str]
    total_events_received: int
    total_alerts_published: int
    total_errors: int
    success_rate: float


# ========== API Endpoints ==========


@router.get("/health", response_model=WazuhHealthCheck)
async def health_check():
    """
    Check Wazuh API connectivity

    Returns health status of Wazuh API connection
    """
    client = get_wazuh_client()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wazuh client not initialized"
        )

    try:
        is_healthy = await client.health_check()
        return WazuhHealthCheck(
            healthy=is_healthy,
            api_url=client.api_url,
            message="Connected" if is_healthy else "Cannot connect to Wazuh API"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Wazuh API health check failed: {str(e)}"
        )


@router.get("/agents", response_model=List[AgentInfo])
async def get_agents(
    limit: int = 500,
    status_filter: Optional[str] = None
):
    """
    Get list of Wazuh agents

    Args:
        limit: Maximum number of agents to return
        status_filter: Filter by status (active, disconnected, never_connected)

    Returns:
        List of agent information
    """
    client = get_wazuh_client()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wazuh client not initialized"
        )

    try:
        agents_data = await client.get_agents(limit=limit, status=status_filter)

        agents = []
        for agent in agents_data:
            agents.append(AgentInfo(
                id=str(agent.get('id', 'N/A')),
                name=agent.get('name', 'Unknown'),
                ip=agent.get('ip', 'N/A'),
                status=agent.get('status', 'unknown'),
                os=agent.get('os'),
                version=agent.get('version')
            ))

        return agents

    except Exception as e:
        logger.error(f"Error fetching agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch agents: {str(e)}"
        )


@router.get("/agents/{agent_id}")
async def get_agent_info(agent_id: str):
    """
    Get detailed information about a specific agent

    Args:
        agent_id: Agent ID or name

    Returns:
        Agent detailed information
    """
    client = get_wazuh_client()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wazuh client not initialized"
        )

    try:
        agent_info = await client.get_agent_info(agent_id)
        return agent_info
    except Exception as e:
        logger.error(f"Error fetching agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch agent info: {str(e)}"
        )


@router.post("/alerts")
async def fetch_alerts(request: AlertsRequest):
    """
    Fetch alerts from Wazuh

    Args:
        request: Alerts query parameters

    Returns:
        List of alerts
    """
    client = get_wazuh_client()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wazuh client not initialized"
        )

    try:
        # Parse timestamps if provided
        start_time = None
        end_time = None

        if request.start_time:
            start_time = datetime.fromisoformat(request.start_time)
        if request.end_time:
            end_time = datetime.fromisoformat(request.end_time)

        alerts = await client.get_alerts(
            limit=request.limit,
            offset=request.offset,
            agent_id=request.agent_id,
            level=request.level,
            start_time=start_time,
            end_time=end_time
        )

        return {
            "count": len(alerts),
            "alerts": alerts
        }

    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch alerts: {str(e)}"
        )


@router.get("/alerts/summary")
async def get_alerts_summary(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """
    Get alerts summary statistics

    Args:
        start_time: Start time filter (ISO format)
        end_time: End time filter (ISO format)

    Returns:
        Alerts summary
    """
    client = get_wazuh_client()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wazuh client not initialized"
        )

    try:
        # Parse timestamps
        st = datetime.fromisoformat(start_time) if start_time else None
        et = datetime.fromisoformat(end_time) if end_time else None

        summary = await client.get_alerts_summary(start_time=st, end_time=et)
        return summary

    except Exception as e:
        logger.error(f"Error fetching alerts summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch alerts summary: {str(e)}"
        )


@router.post("/test-alert")
async def create_test_alert(request: TestAlertRequest):
    """
    Create a test alert from Wazuh data and publish to message queue

    Useful for testing the integration end-to-end

    Args:
        request: Test alert configuration

    Returns:
        Published alert details
    """
    client = get_wazuh_client()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wazuh client not initialized"
        )

    try:
        # Fetch alerts from Wazuh to get real data
        # If Wazuh daemons aren't ready, fall back to mock alert
        try:
            alerts = await client.get_alerts(limit=10, agent_id=request.agent_id)
        except Exception as wazuh_error:
            logger.warning(f"Wazuh not ready, using mock alert: {wazuh_error}")
            alerts = None

        if not alerts or len(alerts) == 0:
            # Create mock alert if no real alerts available
            test_alert = {
                'rule': {
                    'id': request.rule_id,
                    'level': 12 if request.severity == 'high' else 5,
                    'description': 'Test Alert - SSH Brute Force Attempt',
                    'groups': ['authentication_failed', 'bruteforce'],
                    'mitre': {
                        'id': ['T1110'],
                        'technique': ['Brute Force']
                    }
                },
                'agent': {
                    'id': request.agent_id,
                    'name': 'test-agent',
                    'ip': '10.0.0.100'
                },
                'timestamp': datetime.utcnow().isoformat(),
                'full_log': 'Feb 24 12:00:00 test-server sshd[12345]: Failed password for root from 192.168.1.100 port 12345 ssh2',
                'location': '/var/log/auth.log',
                'data': {
                    'srcip': '192.168.1.100',
                    'srcport': '12345',
                    'dstport': '22'
                }
            }
        else:
            # Use first real alert
            test_alert = alerts[0]

        # Map alert to SOC format
        mapper = get_alert_mapper()
        mapped_alert = mapper.map_alert(test_alert)

        # Publish to message queue
        mq_manager = get_message_queue_manager()
        await mq_manager.publish_alert_async(
            alert=mapped_alert,
            severity=mapped_alert.get('severity', 'medium')
        )

        return {
            "message": "Test alert created and published successfully",
            "alert_id": mapped_alert.get('id'),
            "severity": mapped_alert.get('severity'),
            "title": mapped_alert.get('title'),
            "queue_priority": mapped_alert.get('severity')
        }

    except Exception as e:
        logger.error(f"Error creating test alert: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create test alert: {str(e)}"
        )


@router.get("/receiver/stats", response_model=ReceiverStats)
async def get_receiver_stats():
    """
    Get Wazuh log receiver statistics

    Returns current statistics and status
    """
    receiver = get_wazuh_receiver()

    if not receiver:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wazuh receiver not initialized"
        )

    try:
        stats = receiver.get_statistics()
        return ReceiverStats(**stats)
    except Exception as e:
        logger.error(f"Error getting receiver stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get receiver stats: {str(e)}"
        )


@router.post("/receiver/start")
async def start_receiver():
    """
    Start the Wazuh log receiver service

    Returns status of the operation
    """
    receiver = get_wazuh_receiver()

    if not receiver:
        # Initialize receiver if not exists
        init_wazuh_receiver()
        receiver = get_wazuh_receiver()

    if receiver.is_running:
        return {
            "message": "Receiver is already running",
            "stats": receiver.get_statistics()
        }

    try:
        # Start receiver in background
        import asyncio
        asyncio.create_task(receiver.start())

        return {
            "message": "Wazuh log receiver started successfully",
            "stats": receiver.get_statistics()
        }

    except Exception as e:
        logger.error(f"Error starting receiver: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start receiver: {str(e)}"
        )


@router.post("/receiver/stop")
async def stop_receiver():
    """
    Stop the Wazuh log receiver service

    Returns status of the operation
    """
    receiver = get_wazuh_receiver()

    if not receiver:
        return {
            "message": "Receiver not initialized"
        }

    if not receiver.is_running:
        return {
            "message": "Receiver is not running"
        }

    try:
        await receiver.stop()

        return {
            "message": "Wazuh log receiver stopped successfully",
            "stats": receiver.get_statistics()
        }

    except Exception as e:
        logger.error(f"Error stopping receiver: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop receiver: {str(e)}"
        )


@router.post("/receiver/configure")
async def configure_receiver(config: ReceiverConfig):
    """
    Configure Wazuh log receiver

    Args:
        config: Receiver configuration

    Returns updated configuration
    """
    try:
        # Initialize receiver with new config
        init_wazuh_receiver(
            poll_interval=config.poll_interval,
            batch_size=config.batch_size,
            lookback_minutes=config.lookback_minutes,
            enabled=config.enabled
        )

        receiver = get_wazuh_receiver()

        return {
            "message": "Receiver configured successfully",
            "config": config.dict(),
            "stats": receiver.get_statistics() if receiver else None
        }

    except Exception as e:
        logger.error(f"Error configuring receiver: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure receiver: {str(e)}"
        )


@router.post("/receiver/restart")
async def restart_receiver():
    """
    Restart the Wazuh log receiver service

    Returns status of the operation
    """
    receiver = get_wazuh_receiver()

    if not receiver:
        return {
            "message": "Receiver not initialized, use /configure first"
        }

    try:
        # Stop if running
        if receiver.is_running:
            await receiver.stop()

        # Start again
        import asyncio
        asyncio.create_task(receiver.start())

        return {
            "message": "Wazuh log receiver restarted successfully",
            "stats": receiver.get_statistics()
        }

    except Exception as e:
        logger.error(f"Error restarting receiver: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart receiver: {str(e)}"
        )


@router.get("/integration/status")
async def get_integration_status():
    """
    Get overall Wazuh integration status

    Returns comprehensive status information
    """
    client = get_wazuh_client()
    receiver = get_wazuh_receiver()

    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "wazuh_api": {
            "configured": client is not None,
            "api_url": client.api_url if client else None,
            "authenticated": client.jwt_token is not None if client else False
        },
        "log_receiver": {
            "initialized": receiver is not None,
            "running": receiver.is_running if receiver else False,
            "stats": receiver.get_statistics() if receiver else None
        },
        "message_queue": {
            "available": get_message_queue_manager() is not None
        }
    }

    return status
