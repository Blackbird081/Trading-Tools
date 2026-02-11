"""Tests for Circuit Breaker pattern.

★ State transitions: CLOSED → OPEN → HALF_OPEN → CLOSED
★ Fast-fail when OPEN
★ Recovery after timeout

Ref: Doc 05 §4.6
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import pytest
from adapters.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)


class TestCircuitBreaker:
    """Circuit breaker state transition tests."""

    @pytest.mark.asyncio
    async def test_closed_allows_calls(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        func = AsyncMock(return_value="ok")
        result = await cb.call(func)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        func = AsyncMock(side_effect=ConnectionError("fail"))

        for _ in range(3):
            with pytest.raises(ConnectionError):
                await cb.call(func)

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    @pytest.mark.asyncio
    async def test_open_rejects_immediately(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=60.0)
        func = AsyncMock(side_effect=ConnectionError("fail"))

        # Trip the breaker
        with pytest.raises(ConnectionError):
            await cb.call(func)

        assert cb.state == CircuitState.OPEN

        # Now should reject with CircuitOpenError
        with pytest.raises(CircuitOpenError, match="OPEN"):
            await cb.call(func)

    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.01)
        fail_func = AsyncMock(side_effect=ConnectionError("fail"))

        # Trip the breaker
        with pytest.raises(ConnectionError):
            await cb.call(fail_func)

        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout (must be real sleep — CB uses time.monotonic)
        time.sleep(0.02)  # noqa: ASYNC251

        # Next call should transition to HALF_OPEN and succeed
        success_func = AsyncMock(return_value="recovered")
        result = await cb.call(success_func)
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED  # type: ignore[comparison-overlap]

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.01)
        fail_func = AsyncMock(side_effect=ConnectionError("fail"))

        # Trip the breaker
        with pytest.raises(ConnectionError):
            await cb.call(fail_func)

        # Wait for recovery (must be real sleep — CB uses time.monotonic)
        time.sleep(0.02)  # noqa: ASYNC251

        # Half-open probe fails → back to OPEN
        with pytest.raises(ConnectionError):
            await cb.call(fail_func)

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self) -> None:
        cb = CircuitBreaker(name="test", failure_threshold=3)
        fail_func = AsyncMock(side_effect=ConnectionError("fail"))
        ok_func = AsyncMock(return_value="ok")

        # 2 failures (not yet tripped)
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(fail_func)

        assert cb.failure_count == 2

        # Success resets count
        await cb.call(ok_func)
        assert cb.failure_count == 0
        assert cb.success_count == 1
        assert cb.state == CircuitState.CLOSED

    def test_manual_reset(self) -> None:
        cb = CircuitBreaker(name="test")
        cb.state = CircuitState.OPEN
        cb.failure_count = 10
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
