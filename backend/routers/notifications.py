"""
Notifications Router
通知管理 API

提供通知相关的接口:
- 发送测试通知
- 查看通知渠道状态
- 查看队列统计
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List
from pydantic import BaseModel
from datetime import datetime

from services.notification_service import get_notification_service
from services.message_queue_manager import get_message_queue_manager
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


class TestNotificationRequest(BaseModel):
    """测试通知请求"""
    channels: List[str] = []  # 指定测试渠道 (空表示所有)


class QueueStatsResponse(BaseModel):
    """队列统计响应"""
    critical: int
    high: int
    medium: int
    low: int


@router.post("/test", response_model=Dict[str, bool])
async def send_test_notification(
    request: TestNotificationRequest | None = None
) -> Dict[str, bool]:
    """
    发送测试通知

    用于验证通知渠道配置是否正确。

    支持的渠道:
    - feishu: 飞书通知
    - slack: Slack 通知
    - email: 邮件通知

    如果不指定 channels，将发送到所有已配置的渠道。
    """
    try:
        notification_service = get_notification_service()

        # 如果指定了渠道，只测试指定渠道
        channels = request.channels if request else None

        logger.info(f"Sending test notification to channels: {channels or 'all'}")

        # 构建测试告警
        test_alert = {
            'id': 'TEST-001',
            'title': 'SOC Copilot Test Notification',
            'source': 'test',
            'event_type': 'test',
            'severity': 'info',
            'description': 'This is a test notification to verify channel configuration.',
            'created_at': datetime.now().isoformat()
        }

        # 发送测试通知
        results = await notification_service.send_alert(test_alert, channels=channels)

        return results

    except Exception as e:
        logger.error(f"Error sending test notification: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send test notification: {str(e)}")


@router.get("/channels", response_model=Dict[str, bool])
async def get_notification_channels() -> Dict[str, bool]:
    """
    获取通知渠道状态

    返回各通知渠道是否已配置:
    - feishu: 飞书
    - slack: Slack
    - email: 邮件
    """
    try:
        notification_service = get_notification_service()

        return {
            "feishu": bool(notification_service.feishu_webhook),
            "slack": bool(notification_service.slack_webhook),
            "email": bool(notification_service.email_config['to'])
        }

    except Exception as e:
        logger.error(f"Error getting notification channels: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get channels: {str(e)}")


@router.get("/queue/stats", response_model=Dict[str, Dict[str, int | str]])
async def get_queue_stats() -> Dict[str, Dict[str, int | str]]:
    """
    获取消息队列统计信息

    返回各优先级队列的:
    - length: 队列中消息总数
    - pending: 待处理消息数
    - stream: 流名称
    """
    try:
        mq_manager = get_message_queue_manager()
        health = mq_manager.health_check()
        stats = mq_manager.get_queue_stats()
        if not health.get('redis'):
            # 无 Redis 时降级返回空统计，避免前端页面整体失败
            return {
                "critical": {"stream": "events:critical", "length": 0, "pending": 0},
                "high": {"stream": "events:high", "length": 0, "pending": 0},
                "medium": {"stream": "events:medium", "length": 0, "pending": 0},
                "low": {"stream": "events:low", "length": 0, "pending": 0},
            }

        return stats

    except Exception as e:
        logger.error(f"Error getting queue stats: {str(e)}")
        # 与 /health 一致，异常时也返回可渲染的默认结构
        return {
            "critical": {"stream": "events:critical", "length": 0, "pending": 0},
            "high": {"stream": "events:high", "length": 0, "pending": 0},
            "medium": {"stream": "events:medium", "length": 0, "pending": 0},
            "low": {"stream": "events:low", "length": 0, "pending": 0},
        }


@router.get("/health")
async def get_notification_health() -> Dict:
    """
    获取通知系统健康状态

    返回:
    - redis: Redis 连接状态
    - streams: Streams 是否已创建
    - channels: 已配置的通知渠道
    """
    try:
        mq_manager = get_message_queue_manager()
        notification_service = get_notification_service()

        health = mq_manager.health_check()

        return {
            "redis": health.get('redis', False),
            "streams": health.get('streams', False),
            "channels": {
                "feishu": bool(notification_service.feishu_webhook),
                "slack": bool(notification_service.slack_webhook),
                "email": bool(notification_service.email_config['to'])
            }
        }

    except Exception as e:
        logger.error(f"Error checking notification health: {str(e)}")
        return {
            "redis": False,
            "streams": False,
            "channels": {},
            "error": str(e)
        }
