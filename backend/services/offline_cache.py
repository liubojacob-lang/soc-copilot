"""
离线消息缓存服务
用于存储用户离线期间的消息，上线后推送
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from core.logger import get_logger
import json

logger = get_logger(__name__)


class OfflineMessageCache:
    """离线消息缓存管理器"""

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self._cache: Dict[str, List[Dict[str, Any]]] = {}  # 内存缓存

    async def store_message(
        self,
        user_id: str,
        message_type: str,
        message_data: Dict[str, Any],
        ttl_seconds: int = 86400  # 24小时
    ):
        """存储离线消息"""
        try:
            # 存储到内存缓存
            if user_id not in self._cache:
                self._cache[user_id] = []

            self._cache[user_id].append({
                "type": message_type,
                "data": message_data,
                "timestamp": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
            })

            # 限制缓存数量（每个用户最多100条）
            if len(self._cache[user_id]) > 100:
                self._cache[user_id] = self._cache[user_id][-100:]

            # TODO: 也可以存储到数据库或 Redis
            logger.debug(f"Stored offline message for user {user_id}: {message_type}")

        except Exception as e:
            logger.error(f"Failed to store offline message: {e}")

    async def get_messages(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的离线消息"""
        try:
            messages = self._cache.get(user_id, [])
            now = datetime.utcnow()

            # 过滤过期消息
            valid_messages = []
            for msg in messages:
                expires_at = datetime.fromisoformat(msg["expires_at"])
                if expires_at > now:
                    valid_messages.append(msg)

            # 更新缓存
            self._cache[user_id] = valid_messages

            # 清空已读取的消息
            self._cache[user_id] = []

            logger.info(f"Retrieved {len(valid_messages)} offline messages for user {user_id}")
            return valid_messages

        except Exception as e:
            logger.error(f"Failed to get offline messages: {e}")
            return []

    async def clear_old_messages(self, older_than_hours: int = 24):
        """清理过期消息"""
        try:
            now = datetime.utcnow()
            cutoff = now - timedelta(hours=older_than_hours)

            for user_id in list(self._cache.keys()):
                valid_messages = []
                for msg in self._cache[user_id]:
                    expires_at = datetime.fromisoformat(msg["expires_at"])
                    if expires_at > cutoff:
                        valid_messages.append(msg)

                if valid_messages:
                    self._cache[user_id] = valid_messages
                else:
                    del self._cache[user_id]

            logger.info("Cleared old offline messages")

        except Exception as e:
            logger.error(f"Failed to clear old messages: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_messages = sum(len(msgs) for msgs in self._cache.values())
        return {
            "total_users": len(self._cache),
            "total_messages": total_messages,
            "messages_per_user": {
                user_id: len(msgs)
                for user_id, msgs in self._cache.items()
            }
        }


# 全局离线缓存实例
_cache: Optional[OfflineMessageCache] = None


def get_offline_cache() -> OfflineMessageCache:
    """获取全局离线缓存实例"""
    global _cache
    return _cache


def init_offline_cache(db_session_factory):
    """初始化离线缓存"""
    global _cache
    _cache = OfflineMessageCache(db_session_factory)
    return _cache
