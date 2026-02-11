from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("retry")

_DEFAULT_RETRYABLE = (ConnectionError, TimeoutError, OSError)


@dataclass(frozen=True, slots=True)
class RetryConfig:
    """Configuration for exponential backoff retry strategy."""

    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = _DEFAULT_RETRYABLE


_DEFAULT_RETRY_CONFIG = RetryConfig()


def calculate_backoff_delay(attempt: int, config: RetryConfig) -> float:
    delay = config.base_delay * (config.exponential_base**attempt)
    delay = min(delay, config.max_delay)
    if config.jitter:
        delay = random.uniform(0, delay)
    return delay


async def retry_async[T](
    func: Callable[..., Awaitable[T]],
    *args: Any,
    config: RetryConfig = _DEFAULT_RETRY_CONFIG,
    operation_name: str = "operation",
    **kwargs: Any,
) -> T:
    """Execute async function with exponential backoff retry."""
    last_exception: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as exc:
            last_exception = exc
            if attempt >= config.max_retries:
                logger.error(
                    "%s: Failed after %d attempts. Last error: %s",
                    operation_name,
                    attempt + 1,
                    exc,
                )
                raise
            delay = calculate_backoff_delay(attempt, config)
            logger.warning(
                "%s: Attempt %d/%d failed (%s: %s). Retrying in %.1fs...",
                operation_name,
                attempt + 1,
                config.max_retries,
                type(exc).__name__,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
    assert last_exception is not None
    raise last_exception
