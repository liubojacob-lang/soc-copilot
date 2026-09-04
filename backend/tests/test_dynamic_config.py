"""Unit tests for DynamicConfigService distributed runtime configuration hot-reloading."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.dynamic_config import (
    CONFIG_REDIS_HASH,
    CONFIG_RELOAD_CHANNEL,
    DynamicConfigService,
    get_dynamic_config,
)


@pytest.fixture
def service():
    """Create a fresh DynamicConfigService instance for testing."""
    srv = DynamicConfigService()
    srv._local_cache.clear()
    return srv


@pytest.mark.asyncio
async def test_get_default_without_redis(service):
    """Test getting default value when Redis is unavailable."""
    with patch.object(service, "_get_redis", new=AsyncMock(return_value=None)):
        val = await service.get("slow_request_threshold_ms")
        assert val == 1000

        # Custom key with provided fallback default
        custom_val = await service.get("custom_unknown_key", default=42)
        assert custom_val == 42


def test_get_sync(service):
    """Test synchronous get method using cache and fallback."""
    service._local_cache["cached_key"] = 999
    assert service.get_sync("cached_key") == 999
    assert service.get_sync("slow_request_threshold_ms") == 1000
    assert service.get_sync("non_existent_key", default="fallback") == "fallback"


@pytest.mark.asyncio
async def test_set_and_get_with_redis(service):
    """Test setting an override, persisting to Redis, and publishing reload event."""
    mock_redis = AsyncMock()
    mock_redis.hset = AsyncMock()
    mock_redis.publish = AsyncMock()

    with patch.object(service, "_get_redis", new=AsyncMock(return_value=mock_redis)):
        success = await service.set("slow_request_threshold_ms", "2500")
        assert success is True
        assert service._local_cache["slow_request_threshold_ms"] == 2500

        mock_redis.hset.assert_awaited_once_with(
            CONFIG_REDIS_HASH, "slow_request_threshold_ms", "2500"
        )
        mock_redis.publish.assert_awaited_once()
        call_args = mock_redis.publish.call_args[0]
        assert call_args[0] == CONFIG_RELOAD_CHANNEL
        payload = json.loads(call_args[1])
        assert payload["action"] == "set"
        assert payload["key"] == "slow_request_threshold_ms"
        assert payload["value"] == 2500
        assert payload["source"] == service._instance_id

        # Subsequent get returns cached value immediately
        val = await service.get("slow_request_threshold_ms")
        assert val == 2500


@pytest.mark.asyncio
async def test_delete_override(service):
    """Test deleting an override resets local cache and notifies peers."""
    service._local_cache["slow_request_threshold_ms"] = 3000
    mock_redis = AsyncMock()
    mock_redis.hdel = AsyncMock()
    mock_redis.publish = AsyncMock()

    with patch.object(service, "_get_redis", new=AsyncMock(return_value=mock_redis)):
        success = await service.delete("slow_request_threshold_ms")
        assert success is True
        assert "slow_request_threshold_ms" not in service._local_cache

        mock_redis.hdel.assert_awaited_once_with(
            CONFIG_REDIS_HASH, "slow_request_threshold_ms"
        )
        mock_redis.publish.assert_awaited_once()
        call_args = mock_redis.publish.call_args[0]
        payload = json.loads(call_args[1])
        assert payload["action"] == "delete"
        assert payload["key"] == "slow_request_threshold_ms"


@pytest.mark.asyncio
async def test_get_all_configurations(service):
    """Test get_all returns list of supported keys with override flags."""
    mock_redis = AsyncMock()
    mock_redis.hgetall = AsyncMock(
        return_value={"slow_request_threshold_ms": "1500", "custom_dynamic_param": '"test_val"'}
    )

    with patch.object(service, "_get_redis", new=AsyncMock(return_value=mock_redis)):
        all_configs = await service.get_all()
        assert len(all_configs) >= 10

        keys_map = {item["key"]: item for item in all_configs}
        assert "slow_request_threshold_ms" in keys_map
        assert keys_map["slow_request_threshold_ms"]["current_value"] == 1500
        assert keys_map["slow_request_threshold_ms"]["is_overridden"] is True

        assert "custom_dynamic_param" in keys_map
        assert keys_map["custom_dynamic_param"]["current_value"] == "test_val"


@pytest.mark.asyncio
async def test_pubsub_peer_message_processing(service):
    """Test pubsub listener processes set/delete/reload from peers and ignores self messages."""
    peer_set_msg = json.dumps(
        {
            "action": "set",
            "key": "api_timeout_default_ms",
            "value": 45000,
            "source": "other-pod-1234",
        }
    )
    peer_del_msg = json.dumps(
        {
            "action": "delete",
            "key": "api_timeout_default_ms",
            "source": "other-pod-1234",
        }
    )
    self_msg = json.dumps(
        {
            "action": "set",
            "key": "api_timeout_default_ms",
            "value": 99999,
            "source": service._instance_id,
        }
    )

    pubsub_messages = [
        {"data": peer_set_msg},
        {"data": self_msg},
        {"data": peer_del_msg},
    ]

    mock_pubsub = AsyncMock()

    async def mock_get_message(*args, **kwargs):
        if pubsub_messages:
            return pubsub_messages.pop(0)
        await asyncio.sleep(0.01)
        service._running = False
        return None

    mock_pubsub.get_message = mock_get_message
    mock_redis = AsyncMock()
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

    await service.start_pubsub(redis_client=mock_redis)
    # Wait for listener loop to process messages
    for _ in range(20):
        if not pubsub_messages and not service._running:
            break
        await asyncio.sleep(0.02)

    await service.stop_pubsub()
    assert "api_timeout_default_ms" not in service._local_cache


def test_singleton_accessor():
    """Test get_dynamic_config returns a singleton instance."""
    inst1 = get_dynamic_config()
    inst2 = get_dynamic_config()
    assert inst1 is inst2


@pytest.mark.asyncio
async def test_dynamic_config_api_endpoints(auth_client):
    """Test dynamic config REST API endpoints."""
    # 1. GET /api/v1/admin/settings/dynamic
    resp = await auth_client.get("/api/v1/admin/settings/dynamic")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["key"] == "slow_request_threshold_ms" for item in data)

    # 2. GET /api/v1/admin/settings/dynamic/{key}
    resp = await auth_client.get(
        "/api/v1/admin/settings/dynamic/slow_request_threshold_ms"
    )
    assert resp.status_code == 200
    item = resp.json()
    assert item["key"] == "slow_request_threshold_ms"

    # 3. PUT /api/v1/admin/settings/dynamic/{key}
    resp = await auth_client.put(
        "/api/v1/admin/settings/dynamic/slow_request_threshold_ms",
        json={"value": 1800},
    )
    assert resp.status_code == 200
    assert resp.json()["value"] == 1800

    # 4. DELETE /api/v1/admin/settings/dynamic/{key}
    resp = await auth_client.delete(
        "/api/v1/admin/settings/dynamic/slow_request_threshold_ms"
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

