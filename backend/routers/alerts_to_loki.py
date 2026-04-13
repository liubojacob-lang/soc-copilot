"""
告警路由 - 发送告警到 Loki
"""

from fastapi import APIRouter, Depends, HTTPException

from core.logger import get_logger
from dependencies import get_current_user
from models.user import UserModel
from services.loki_alert_sender import get_loki_sender

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


@router.post("/send")
async def send_alert(
    alert: dict,
    current_user: UserModel = Depends(get_current_user),
):
    """发送告警到 Loki 和前端"""
    try:
        # 发送到 Loki
        loki_sender = get_loki_sender()
        await loki_sender.send_alert(alert)

        logger.info(f"Alert sent: {alert.get('event_type')}")
        return {"status": "success", "message": "Alert sent to Loki"}

    except Exception as e:
        logger.error(f"Failed to send alert: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/test")
async def test_alert(current_user: UserModel = Depends(get_current_user)):
    """发送测试告警"""
    loki_sender = get_loki_sender()
    success = await loki_sender.send_test_alert()

    if success:
        return {"status": "success", "message": "Test alert sent"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send test alert")
