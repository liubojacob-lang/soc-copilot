from unittest.mock import AsyncMock, MagicMock

import pytest

from services.webhook_deduplication import WebhookDeduplicationService


@pytest.mark.asyncio
async def test_webhook_fingerprint_and_memory_deduplication():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result
    mock_session.commit = AsyncMock()

    service = WebhookDeduplicationService(session=mock_session, redis_client=None)

    payload = b'{"event": "alert", "id": "12345"}'
    headers = {"content-type": "application/json", "x-event-type": "security_alert"}
    trigger_id = "trig-001"

    # 1. Initial check: should not be duplicate
    is_dup, cached = await service.check_duplicate(payload, headers, trigger_id)
    assert is_dup is False
    assert cached is None

    # 2. Record the request in memory cache
    response_data = {"status": "accepted", "action": "dispatched"}
    idem_key = await service.record_request(
        payload=payload,
        headers=headers,
        trigger_id=trigger_id,
        response=response_data,
        ttl_seconds=60
    )
    assert idem_key.startswith("webhook:fingerprint:")

    # 3. Check again with same payload: should detect memory duplicate
    is_dup2, cached2 = await service.check_duplicate(payload, headers, trigger_id)
    assert is_dup2 is True
    assert cached2 == response_data

    # 4. Different payload: should not be duplicate
    diff_payload = b'{"event": "alert", "id": "99999"}'
    is_dup3, cached3 = await service.check_duplicate(diff_payload, headers, trigger_id)
    assert is_dup3 is False
    assert cached3 is None
