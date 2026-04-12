"""
离线消息缓存服务
用于存储用户离线期间的消息，上线后推送
"""

import json
from datetime import datetime, timedelta
from typing import Any

from core.config import get_settings
from core.logger import get_logger

logger = get_logger(__name__)


class OfflineMessageCache:
    """离线消息缓存管理器"""

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self._cache: dict[str, list[dict[str, Any]]] = {}  # 内存缓存
        self._redis_client = None
        self._use_redis = False
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis client if configured"""
        settings = get_settings()
        if settings.redis_enabled and settings.redis_url:
            try:
                import redis.asyncio as redis

                self._redis_client = redis.from_url(
                    settings.redis_url, encoding="utf-8", decode_responses=True
                )
                self._use_redis = True
                logger.info("Redis client initialized for offline cache")
            except ImportError:
                logger.warning(
                    "Redis package not installed, falling back to memory cache"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to initialize Redis client: {e}, falling back to memory cache"
                )

    async def store_message(
        self,
        user_id: str,
        message_type: str,
        message_data: dict[str, Any],
        ttl_seconds: int = 86400,  # 24小时
    ):
        """存储离线消息"""
        try:
            message = {
                "type": message_type,
                "data": message_data,
                "timestamp": datetime.utcnow().isoformat(),
                "expires_at": (
                    datetime.utcnow() + timedelta(seconds=ttl_seconds)
                ).isoformat(),
            }

            if self._use_redis and self._redis_client:
                await self._store_to_redis(user_id, message, ttl_seconds)
            else:
                await self._store_to_memory(user_id, message)

            logger.debug(f"Stored offline message for user {user_id}: {message_type}")

        except Exception as e:
            logger.error(f"Failed to store offline message: {e}")

    async def _store_to_redis(
        self, user_id: str, message: dict[str, Any], ttl_seconds: int
    ):
        """Store message to Redis"""
        try:
            key = f"offline_messages:{user_id}"
            await self._redis_client.lpush(key, json.dumps(message))
            await self._redis_client.ltrim(key, 0, 99)  # Keep max 100 messages
            await self._redis_client.expire(key, ttl_seconds)
        except Exception as e:
            logger.warning(f"Failed to store to Redis: {e}, falling back to memory")
            await self._store_to_memory(user_id, message)

    async def _store_to_memory(self, user_id: str, message: dict[str, Any]):
        """Store message to memory cache"""
        if user_id not in self._cache:
            self._cache[user_id] = []

        self._cache[user_id].append(message)

        # 限制缓存数量（每个用户最多100条）
        if len(self._cache[user_id]) > 100:
            self._cache[user_id] = self._cache[user_id][-100:]

    async def get_messages(self, user_id: str) -> list[dict[str, Any]]:
        """获取用户的离线消息"""
        try:
            if self._use_redis and self._redis_client:
                messages = await self._get_from_redis(user_id)
            else:
                messages = await self._get_from_memory(user_id)

            logger.info(
                f"Retrieved {len(messages)} offline messages for user {user_id}"
            )
            return messages

        except Exception as e:
            logger.error(f"Failed to get offline messages: {e}")
            return []

    async def _get_from_redis(self, user_id: str) -> list[dict[str, Any]]:
        """Get messages from Redis"""
        try:
            key = f"offline_messages:{user_id}"
            messages_json = await self._redis_client.lrange(key, 0, -1)

            messages = []
            now = datetime.utcnow()

            for msg_json in messages_json:
                try:
                    msg = json.loads(msg_json)
                    expires_at = datetime.fromisoformat(msg["expires_at"])
                    if expires_at > now:
                        messages.append(msg)
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue

            await self._redis_client.delete(key)
            return messages
        except Exception as e:
            logger.warning(f"Failed to get from Redis: {e}, falling back to memory")
            return await self._get_from_memory(user_id)

    async def _get_from_memory(self, user_id: str) -> list[dict[str, Any]]:
        """Get messages from memory cache"""
        messages = self._cache.get(user_id, [])
        now = datetime.utcnow()

        # 过滤过期消息
        valid_messages = []
        for msg in messages:
            expires_at = datetime.fromisoformat(msg["expires_at"])
            if expires_at > now:
                valid_messages.append(msg)

        # 清空已读取的消息
        self._cache[user_id] = []
        return valid_messages

    async def clear_old_messages(self, older_than_hours: int = 24):
        """清理过期消息"""
        try:
            if self._use_redis and self._redis_client:
                await self._clear_redis_old_messages(older_than_hours)
            else:
                await self._clear_memory_old_messages(older_than_hours)

            logger.info("Cleared old offline messages")

        except Exception as e:
            logger.error(f"Failed to clear old messages: {e}")

    async def _clear_redis_old_messages(self, older_than_hours: int):
        """Clear old messages from Redis"""
        try:
            cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
            pattern = "offline_messages:*"

            async for key in self._redis_client.scan_iter(match=pattern):
                messages_json = await self._redis_client.lrange(key, 0, -1)
                valid_messages = []

                for msg_json in messages_json:
                    try:
                        msg = json.loads(msg_json)
                        expires_at = datetime.fromisoformat(msg["expires_at"])
                        if expires_at > cutoff:
                            valid_messages.append(msg)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue

                if valid_messages:
                    await self._redis_client.delete(key)
                    for msg in valid_messages:
                        await self._redis_client.lpush(key, json.dumps(msg))
                else:
                    await self._redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Failed to clear Redis old messages: {e}")

    async def _clear_memory_old_messages(self, older_than_hours: int):
        """Clear old messages from memory cache"""
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

    def get_cache_stats(self) -> dict[str, Any]:
        """获取缓存统计信息"""
        stats = {
            "storage_type": "redis" if self._use_redis else "memory",
            "total_users": 0,
            "total_messages": 0,
            "messages_per_user": {},
        }

        if self._use_redis:
            stats["redis_enabled"] = True
        else:
            stats["total_users"] = len(self._cache)
            stats["total_messages"] = sum(len(msgs) for msgs in self._cache.values())
            stats["messages_per_user"] = {
                user_id: len(msgs) for user_id, msgs in self._cache.items()
            }

        return stats

    async def close(self):
        """Close Redis connection"""
        if self._redis_client:
            await self._redis_client.close()
            logger.info("Redis connection closed")


# 全局离线缓存实例
_cache: OfflineMessageCache | None = None


def get_offline_cache() -> OfflineMessageCache:
    """获取全局离线缓存实例"""
    global _cache
    return _cache


def init_offline_cache(db_session_factory):
    """初始化离线缓存"""
    global _cache
    _cache = OfflineMessageCache(db_session_factory)
    return _cache
