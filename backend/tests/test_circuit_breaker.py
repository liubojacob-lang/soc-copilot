import asyncio

import pytest

from utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException, CircuitState


@pytest.mark.asyncio
async def test_circuit_breaker_normal_flow():
    cb = CircuitBreaker(name="test-cb", failure_threshold=2, recovery_timeout=0.2)
    
    async def successful_call():
        return "ok"
        
    res = await cb.call(successful_call)
    assert res == "ok"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0

@pytest.mark.asyncio
async def test_circuit_breaker_trips_to_open():
    cb = CircuitBreaker(name="test-cb", failure_threshold=2, recovery_timeout=0.1)
    
    async def failing_call():
        raise ValueError("downstream failure")
        
    # First failure
    with pytest.raises(ValueError):
        await cb.call(failing_call)
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1
    
    # Second failure -> trips to OPEN
    with pytest.raises(ValueError):
        await cb.call(failing_call)
    assert cb.state == CircuitState.OPEN
    assert cb.failure_count == 2
    
    # Immediate call fast-fails with CircuitBreakerOpenException
    with pytest.raises(CircuitBreakerOpenException):
        await cb.call(failing_call)

@pytest.mark.asyncio
async def test_circuit_breaker_recovery_to_closed():
    cb = CircuitBreaker(name="test-cb", failure_threshold=1, recovery_timeout=0.05)
    
    async def failing_call():
        raise RuntimeError("error")
        
    with pytest.raises(RuntimeError):
        await cb.call(failing_call)
    assert cb.state == CircuitState.OPEN
    
    # Wait for recovery timeout
    await asyncio.sleep(0.15)
    
    async def healthy_call():
        return "recovered"
        
    # In HALF_OPEN state, successful call recovers circuit to CLOSED
    res = await cb.call(healthy_call)
    assert res == "recovered"
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
