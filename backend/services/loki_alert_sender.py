"""
Loki 告警发送服务
将 SOC Copilot 告警发送到 Grafana Loki
"""

import json
from datetime import datetime
from typing import Any

import httpx

from core.logger import get_logger

logger = get_logger(__name__)


class LokiAlertSender:
    """Loki 告警发送器"""

    def __init__(self, loki_url: str = "http://localhost:3100/loki/api/v1/push"):
        self.loki_url = loki_url
        self.client = httpx.AsyncClient(timeout=10.0)

    async def send_alert(self, alert: dict[str, Any]) -> bool:
        """
        发送告警到 Loki

        Args:
            alert: 告警数据字典

        Returns:
            bool: 发送成功返回 True
        """
        try:
            # 构建 Loki payload
            payload = {
                "streams": [
                    {
                        "stream": {
                            "job": "soc-copilot",
                            "level": alert.get("severity", "info"),
                            "event_type": alert.get("event_type", "unknown"),
                            "agent_id": alert.get("agent_id", "system"),
                            "source": alert.get("source", "soc-copilot"),
                        },
                        "values": [
                            [self._get_timestamp_ns(), self._format_log_entry(alert)]
                        ],
                    }
                ]
            }

            # 发送到 Loki
            response = await self.client.post(
                self.loki_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 204:
                logger.info(f"Alert sent to Loki: {alert.get('event_type')}")
                return True
            else:
                logger.error(
                    f"Failed to send to Loki: {response.status_code} - {response.text}"
                )
                return False

        except Exception as e:
            logger.error(f"Error sending alert to Loki: {e}")
            return False

    def _get_timestamp_ns(self) -> str:
        """获取纳秒时间戳"""
        return str(int(datetime.utcnow().timestamp() * 1_000_000_000))

    def _format_log_entry(self, alert: dict[str, Any]) -> str:
        """格式化日志条目"""
        return json.dumps(
            {
                "timestamp": alert.get("timestamp", datetime.utcnow().isoformat()),
                "event_type": alert.get("event_type"),
                "severity": alert.get("severity"),
                "agent_id": alert.get("agent_id"),
                "source_ip": alert.get("source_ip"),
                "description": alert.get("description"),
                "details": alert.get("details", {}),
            }
        )

    async def send_test_alert(self) -> bool:
        """发送测试告警"""
        test_alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "system_test",
            "severity": "info",
            "agent_id": "test-001",
            "source_ip": "127.0.0.1",
            "description": "Test alert from SOC Copilot",
            "details": {"test": True},
        }

        return await self.send_alert(test_alert)

    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 全局实例
_loki_sender: LokiAlertSender | None = None


def get_loki_sender() -> LokiAlertSender:
    """获取 Loki 发送器实例"""
    global _loki_sender
    if _loki_sender is None:
        _loki_sender = LokiAlertSender()
    return _loki_sender
