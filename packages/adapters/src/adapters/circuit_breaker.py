from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, TypeVar

logger = logging.getLogger("circuit_breaker")

T = TypeVar("T")


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised when circuit breaker is OPEN."""


@dataclass
class CircuitBreaker:
    """Circuit breaker pattern for broker API calls."""

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = field(default=0, init=False)
    last_failure_time: float = field(default=0.0, init=False)
    success_count: int = field(default=0, init=False)

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit '%s': OPEN -> HALF_OPEN", self.name)
            else:
                remaining = self.recovery_timeout - (time.monotonic() - self.last_failure_time)
                msg = f"Circuit '{self.name}' is OPEN. Retry after {remaining:.0f}s."
                raise CircuitOpenError(msg)
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit '%s': HALF_OPEN -> CLOSED", self.name)
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count += 1

    def _on_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                "Circuit '%s': -> OPEN after %d failures. Blocking for %ds.",
                self.name,
                self.failure_count,
                self.recovery_timeout,
            )

    def reset(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        logger.info("Circuit '%s': manually reset to CLOSED", self.name)
