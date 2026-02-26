"""
WebSocket 连接管理器
用于管理告警实时推送的 WebSocket 连接
"""

from typing import Dict, Set, Optional, Any
from fastapi import WebSocket
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 活跃连接: {user_id: {connection_id: WebSocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        # 连接订阅: {connection_id: {filters}}
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        # 最后心跳时间: {connection_id: datetime}
        self.last_heartbeat: Dict[str, datetime] = {}

    async def connect(self, websocket: WebSocket, user_id: str, connection_id: str):
        """接受新连接"""
        await websocket.accept()

        if user_id not in self.active_connections:
            self.active_connections[user_id] = {}

        self.active_connections[user_id][connection_id] = websocket
        self.subscriptions[connection_id] = {
            "severity": None,  # None = all
            "event_type": None,
            "min_severity": None,
        }
        self.last_heartbeat[connection_id] = datetime.now()

        logger.info(f"WebSocket connected: user={user_id}, conn={connection_id}")

    def disconnect(self, user_id: str, connection_id: str):
        """断开连接"""
        if user_id in self.active_connections:
            if connection_id in self.active_connections[user_id]:
                del self.active_connections[user_id][connection_id]

        if connection_id in self.subscriptions:
            del self.subscriptions[connection_id]

        if connection_id in self.last_heartbeat:
            del self.last_heartbeat[connection_id]

        logger.info(f"WebSocket disconnected: user={user_id}, conn={connection_id}")

    async def send_personal_message(self, message: dict, user_id: str, connection_id: str):
        """发送个人消息"""
        if user_id in self.active_connections:
            if connection_id in self.active_connections[user_id]:
                try:
                    websocket = self.active_connections[user_id][connection_id]
                    await websocket.send_json(message)
                    return True
                except Exception as e:
                    logger.error(f"Failed to send message: {e}")
                    self.disconnect(user_id, connection_id)
        return False

    async def broadcast_to_user(self, message: dict, user_id: str):
        """向用户的所有连接广播"""
        if user_id not in self.active_connections:
            return

        disconnected = []
        for conn_id, websocket in self.active_connections[user_id].items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {conn_id}: {e}")
                disconnected.append(conn_id)

        # 清理断开的连接
        for conn_id in disconnected:
            self.disconnect(user_id, conn_id)

    async def broadcast_alert(self, alert: dict, severity_order: dict = None):
        """广播告警到所有订阅用户"""
        if severity_order is None:
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

        alert_severity = alert.get("severity", "info").lower()

        for user_id, connections in self.active_connections.items():
            for conn_id, websocket in connections.items():
                try:
                    # 检查订阅过滤
                    subscription = self.subscriptions.get(conn_id, {})

                    # 严重程度过滤
                    min_severity = subscription.get("min_severity")
                    if min_severity:
                        min_order = severity_order.get(min_severity, 999)
                        alert_order = severity_order.get(alert_severity, 999)
                        if alert_order > min_order:
                            continue

                    # 事件类型过滤
                    event_type_filter = subscription.get("event_type")
                    if event_type_filter and alert.get("event_type") != event_type_filter:
                        continue

                    # 发送告警
                    await websocket.send_json({
                        "type": "alert",
                        "data": alert,
                        "timestamp": datetime.now().isoformat()
                    })

                except Exception as e:
                    logger.error(f"Failed to broadcast alert: {e}")

    def update_subscription(self, connection_id: str, filters: dict):
        """更新连接的订阅过滤"""
        if connection_id in self.subscriptions:
            self.subscriptions[connection_id].update(filters)
            logger.info(f"Subscription updated for {connection_id}: {filters}")

    def heartbeat(self, connection_id: str):
        """更新心跳时间"""
        self.last_heartbeat[connection_id] = datetime.now()

    async def check_timeouts(self, timeout_seconds: int = 60):
        """检查超时连接"""
        now = datetime.now()
        timeout_connections = []

        for conn_id, last_beat in self.last_heartbeat.items():
            if (now - last_beat).total_seconds() > timeout_seconds:
                timeout_connections.append(conn_id)

        for conn_id in timeout_connections:
            # 找到对应的用户并断开
            for user_id, connections in self.active_connections.items():
                if conn_id in connections:
                    logger.warning(f"Connection timeout: {conn_id}")
                    self.disconnect(user_id, conn_id)
                    break

    def get_connection_stats(self) -> dict:
        """获取连接统计信息"""
        total_connections = sum(
            len(conns) for conns in self.active_connections.values()
        )

        return {
            "total_users": len(self.active_connections),
            "total_connections": total_connections,
            "connections_per_user": {
                user_id: len(conns)
                for user_id, conns in self.active_connections.items()
            }
        }


# 全局连接管理器实例
manager = ConnectionManager()
