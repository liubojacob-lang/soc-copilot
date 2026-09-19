"""Dynamic Configuration Service for distributed runtime settings hot-reloading.

Supports multi-layer fallback:
1. In-memory local cache (microsecond lookup)
2. Redis hash storage (`sys:dynamic_config`)
3. Static Pydantic BaseSettings (`core.config.settings`)

Broadcasts updates across multi-instance Pods via Redis Pub/Sub (`sys:config:reload`).
"""

import asyncio
import json
import uuid
from typing import Any

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

CONFIG_RELOAD_CHANNEL = "sys:config:reload"
CONFIG_REDIS_HASH = "sys:dynamic_config"


class DynamicConfigService:
    """Manages runtime-tunable configuration parameters across distributed instances."""

    def __init__(self) -> None:
        self._instance_id = str(uuid.uuid4())
        self._local_cache: dict[str, Any] = {}
        self._redis_client = None
        self._pubsub_task: asyncio.Task | None = None
        self._running = False

        # Metadata for standard tunable system parameters
        self._supported_keys: dict[str, dict[str, Any]] = {
            "slow_request_threshold_ms": {
                "type": "int",
                "description": "慢请求耗时告警阈值 (毫秒)",
                "default": 1000,
            },
            "alert_pipeline_interval_seconds": {
                "type": "int",
                "description": "告警处理管道轮询周期 (秒)",
                "default": getattr(settings, "alert_pipeline_interval_seconds", 15),
            },
            "alert_pipeline_batch_size": {
                "type": "int",
                "description": "告警管道单批次处理上限",
                "default": getattr(settings, "alert_pipeline_batch_size", 50),
            },
            "security_alert_retention_days": {
                "type": "int",
                "description": "安全告警数据保留天数",
                "default": getattr(settings, "security_alert_retention_days", 90),
            },
            "siem_log_retention_days": {
                "type": "int",
                "description": "SIEM 日志数据保留天数",
                "default": getattr(settings, "siem_log_retention_days", 30),
            },
            "api_timeout_default_ms": {
                "type": "int",
                "description": "默认 API 超时时间 (毫秒)",
                "default": getattr(settings, "api_timeout_default_ms", 30000),
            },
            "api_timeout_analysis_ms": {
                "type": "int",
                "description": "AI 研判分析 API 超时时间 (毫秒)",
                "default": getattr(settings, "api_timeout_analysis_ms", 60000),
            },
            "max_retries": {
                "type": "int",
                "description": "外部服务调用最大重试次数",
                "default": getattr(settings, "max_retries", 2),
            },
            "log_level": {
                "type": "str",
                "description": "系统日志输出级别 (DEBUG/INFO/WARNING/ERROR)",
                "default": getattr(settings, "log_level", "INFO"),
            },
            "ws_offline_cache_max_size": {
                "type": "int",
                "description": "单用户离线 WebSocket 消息最大缓冲条数",
                "default": 50,
            },
        }

    async def _get_redis(self):
        if self._redis_client is not None:
            return self._redis_client
        try:
            from core.redis_client import get_redis_client

            self._redis_client = await get_redis_client()
            return self._redis_client
        except Exception as e:
            logger.debug(f"Redis client not available for dynamic config: {e}")
            return None

    def get_sync(self, key: str, default: Any = None) -> Any:
        """Synchronously get a configuration value (from local cache or settings)."""
        key_clean = key.strip().lower()
        if key_clean in self._local_cache:
            return self._local_cache[key_clean]

        meta = self._supported_keys.get(key_clean)
        if meta and "default" in meta:
            fallback = meta["default"]
        else:
            fallback = getattr(settings, key_clean, default)

        return fallback

    async def get(self, key: str, default: Any = None) -> Any:
        """Asynchronously get a configuration value with multi-layer fallback."""
        key_clean = key.strip().lower()
        if key_clean in self._local_cache:
            return self._local_cache[key_clean]

        # Try fetching from Redis override hash
        redis = await self._get_redis()
        if redis:
            try:
                val = await redis.hget(CONFIG_REDIS_HASH, key_clean)
                if val is not None:
                    parsed = json.loads(val)
                    self._local_cache[key_clean] = parsed
                    return parsed
            except Exception as e:
                logger.warning(f"Failed to read dynamic config from Redis: {e}")

        # Fallback to supported_keys default or settings attribute
        meta = self._supported_keys.get(key_clean)
        if meta and "default" in meta:
            fallback = meta["default"]
        else:
            fallback = getattr(settings, key_clean, default)

        return fallback

    async def set(self, key: str, value: Any) -> bool:
        """Set a dynamic configuration override and broadcast reload to all pods."""
        key_clean = key.strip().lower()

        # Type conversion/validation if known
        meta = self._supported_keys.get(key_clean)
        if meta:
            expected_type = meta["type"]
            if expected_type == "int":
                value = int(value)
            elif expected_type == "float":
                value = float(value)
            elif expected_type == "bool":
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
                else:
                    value = bool(value)
            elif expected_type == "str":
                value = str(value)

        # Update local cache
        self._local_cache[key_clean] = value

        # Persist in Redis and broadcast
        redis = await self._get_redis()
        if redis:
            try:
                json_val = json.dumps(value)
                await redis.hset(CONFIG_REDIS_HASH, key_clean, json_val)
                reload_msg = json.dumps(
                    {
                        "action": "set",
                        "key": key_clean,
                        "value": value,
                        "source": self._instance_id,
                    }
                )
                await redis.publish(CONFIG_RELOAD_CHANNEL, reload_msg)
                logger.info(
                    f"Dynamic config override persisted and published: {key_clean}={value}"
                )
            except Exception as e:
                logger.error(f"Failed to persist dynamic config to Redis: {e}")
                return False

        return True

    async def delete(self, key: str) -> bool:
        """Remove a dynamic configuration override (reset to default) and broadcast."""
        key_clean = key.strip().lower()
        self._local_cache.pop(key_clean, None)

        redis = await self._get_redis()
        if redis:
            try:
                await redis.hdel(CONFIG_REDIS_HASH, key_clean)
                reload_msg = json.dumps(
                    {
                        "action": "delete",
                        "key": key_clean,
                        "source": self._instance_id,
                    }
                )
                await redis.publish(CONFIG_RELOAD_CHANNEL, reload_msg)
                logger.info(
                    f"Dynamic config override deleted and broadcasted: {key_clean}"
                )
            except Exception as e:
                logger.error(f"Failed to delete dynamic config from Redis: {e}")
                return False

        return True

    async def get_all(self) -> list[dict[str, Any]]:
        """List all supported configurations with current effective values and override status."""
        # Pre-load all Redis overrides
        overrides: dict[str, Any] = {}
        redis = await self._get_redis()
        if redis:
            try:
                raw_hash = await redis.hgetall(CONFIG_REDIS_HASH)
                for k, v in raw_hash.items():
                    try:
                        overrides[k] = json.loads(v)
                    except Exception:
                        overrides[k] = v
            except Exception as e:
                logger.warning(f"Failed to read all dynamic configs from Redis: {e}")

        result = []
        # Process known keys
        processed_keys = set()
        for key, meta in self._supported_keys.items():
            processed_keys.add(key)
            is_overridden = key in overrides or key in self._local_cache
            current_val = (
                overrides.get(key)
                if key in overrides
                else self._local_cache.get(key, meta.get("default"))
            )
            result.append(
                {
                    "key": key,
                    "current_value": current_val,
                    "default_value": meta.get("default"),
                    "is_overridden": is_overridden,
                    "type": meta.get("type", "str"),
                    "description": meta.get("description", ""),
                }
            )

        # Process custom keys that are not in _supported_keys
        for k, v in overrides.items():
            if k not in processed_keys:
                result.append(
                    {
                        "key": k,
                        "current_value": v,
                        "default_value": None,
                        "is_overridden": True,
                        "type": type(v).__name__,
                        "description": "自定义动态配置参数",
                    }
                )

        return result

    async def start_pubsub(self, redis_client=None) -> None:
        """Start listening to Redis Pub/Sub reload channel for distributed hot-reloads."""
        if self._running:
            return

        if redis_client is not None:
            self._redis_client = redis_client
        else:
            self._redis_client = await self._get_redis()

        if self._redis_client is None:
            logger.info(
                "Redis not available; dynamic config running in local-only mode."
            )
            return

        self._running = True
        self._pubsub_task = asyncio.create_task(
            self._pubsub_listener(), name="dynamic_config_pubsub_listener"
        )
        logger.info(
            f"DynamicConfig Pub/Sub bridge started on channel '{CONFIG_RELOAD_CHANNEL}' (instance_id={self._instance_id})"
        )

    async def stop_pubsub(self) -> None:
        """Stop listening to Pub/Sub reload channel."""
        self._running = False
        if self._pubsub_task and not self._pubsub_task.done():
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass
            self._pubsub_task = None
            logger.info("DynamicConfig Pub/Sub bridge stopped.")

    async def _pubsub_listener(self) -> None:
        """Background coroutine listening for configuration reload broadcasts."""
        pubsub = None
        try:
            pubsub = self._redis_client.pubsub()
            await pubsub.subscribe(CONFIG_RELOAD_CHANNEL)
            logger.info(f"Subscribed to {CONFIG_RELOAD_CHANNEL}")

            while self._running:
                try:
                    message = await pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    )
                    if not message:
                        await asyncio.sleep(0.05)
                        continue

                    data_raw = message.get("data")
                    if not data_raw or not isinstance(data_raw, str):
                        continue

                    payload = json.loads(data_raw)
                    # Discard updates initiated by this instance
                    if payload.get("source") == self._instance_id:
                        continue

                    action = payload.get("action")
                    key = payload.get("key")

                    if action == "set" and key:
                        val = payload.get("value")
                        self._local_cache[key] = val
                        logger.info(
                            f"Dynamic config hot-reloaded from peer: {key}={val}"
                        )
                    elif action == "delete" and key:
                        self._local_cache.pop(key, None)
                        logger.info(f"Dynamic config override reset by peer: {key}")
                    elif action == "reload_all":
                        self._local_cache.clear()
                        logger.info(
                            "Dynamic config local cache cleared by peer request"
                        )

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.warning(f"Error in dynamic config pubsub listener: {e}")
                    await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Dynamic config pubsub loop encountered fatal error: {e}")
        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe(CONFIG_RELOAD_CHANNEL)
                    await pubsub.close()
                except Exception:
                    pass


# Singleton instance
_dynamic_config_instance: DynamicConfigService | None = None


def get_dynamic_config() -> DynamicConfigService:
    """Get the singleton DynamicConfigService instance."""
    global _dynamic_config_instance
    if _dynamic_config_instance is None:
        _dynamic_config_instance = DynamicConfigService()
    return _dynamic_config_instance
