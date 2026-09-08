import pytest

from utils.retry import with_retry, with_sync_retry


@pytest.mark.asyncio
async def test_async_retry_success():
    calls = 0
    @with_retry(max_retries=3, base_delay=0.01, jitter=False)
    async def sample_async_func():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ValueError("temporary error")
        return "done"

    result = await sample_async_func()
    assert result == "done"
    assert calls == 3

@pytest.mark.asyncio
async def test_async_retry_exhausted():
    @with_retry(max_retries=2, base_delay=0.01, jitter=False)
    async def sample_fail():
        raise RuntimeError("permanent failure")

    with pytest.raises(RuntimeError, match="permanent failure"):
        await sample_fail()

def test_sync_retry_success():
    calls = 0
    @with_sync_retry(max_retries=3, base_delay=0.01, jitter=False)
    def sample_sync_func():
        nonlocal calls
        calls += 1
        if calls < 2:
            raise ConnectionError("sync failure")
        return 42

    assert sample_sync_func() == 42
    assert calls == 2
