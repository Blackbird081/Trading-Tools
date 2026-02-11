"""Tests for retry with exponential backoff.

★ Deterministic delays (jitter disabled) for predictable testing.
★ Verify backoff formula: delay = min(base * 2^attempt, max_delay)
★ Verify max retries enforcement.

Ref: Doc 05 §4.2
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from adapters.retry import RetryConfig, calculate_backoff_delay, retry_async

# ── calculate_backoff_delay ──────────────────────────────────────


class TestCalculateBackoffDelay:
    """Test backoff delay calculation."""

    def test_attempt_0_returns_base_delay(self) -> None:
        config = RetryConfig(base_delay=1.0, jitter=False)
        assert calculate_backoff_delay(0, config) == 1.0

    def test_attempt_1_returns_double(self) -> None:
        config = RetryConfig(base_delay=1.0, jitter=False)
        assert calculate_backoff_delay(1, config) == 2.0

    def test_attempt_2_returns_quadruple(self) -> None:
        config = RetryConfig(base_delay=1.0, jitter=False)
        assert calculate_backoff_delay(2, config) == 4.0

    def test_delay_capped_at_max(self) -> None:
        config = RetryConfig(base_delay=1.0, max_delay=10.0, jitter=False)
        # 2^10 = 1024, but capped at 10
        assert calculate_backoff_delay(10, config) == 10.0

    def test_jitter_within_bounds(self) -> None:
        config = RetryConfig(base_delay=1.0, jitter=True)
        for _ in range(100):
            delay = calculate_backoff_delay(0, config)
            assert 0 <= delay <= 1.0

    def test_custom_exponential_base(self) -> None:
        config = RetryConfig(base_delay=1.0, exponential_base=3.0, jitter=False)
        assert calculate_backoff_delay(2, config) == 9.0  # 1 * 3^2


# ── retry_async ──────────────────────────────────────────────────


class TestRetryAsync:
    """Test async retry logic."""

    @pytest.mark.asyncio
    async def test_success_on_first_try(self) -> None:
        func = AsyncMock(return_value="ok")
        result = await retry_async(func, config=RetryConfig(max_retries=3))
        assert result == "ok"
        func.assert_called_once()

    @pytest.mark.asyncio
    async def test_retries_on_connection_error(self) -> None:
        func = AsyncMock(side_effect=[ConnectionError("fail"), "ok"])
        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        result = await retry_async(func, config=config, operation_name="test_op")
        assert result == "ok"
        assert func.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self) -> None:
        func = AsyncMock(side_effect=ConnectionError("always fail"))
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        with pytest.raises(ConnectionError, match="always fail"):
            await retry_async(func, config=config, operation_name="test_op")
        assert func.call_count == 3  # initial + 2 retries

    @pytest.mark.asyncio
    async def test_non_retryable_exception_propagates(self) -> None:
        func = AsyncMock(side_effect=ValueError("bad input"))
        config = RetryConfig(max_retries=3, base_delay=0.01)
        with pytest.raises(ValueError, match="bad input"):
            await retry_async(func, config=config)
        func.assert_called_once()  # No retry for ValueError

    @pytest.mark.asyncio
    async def test_timeout_error_is_retryable(self) -> None:
        func = AsyncMock(side_effect=[TimeoutError("timeout"), "ok"])
        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        result = await retry_async(func, config=config)
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_os_error_is_retryable(self) -> None:
        func = AsyncMock(side_effect=[OSError("network"), "ok"])
        config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
        result = await retry_async(func, config=config)
        assert result == "ok"
