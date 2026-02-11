"""MarketDataPort — inbound port for streaming market ticks.

★ Protocol-based (structural subtyping, NOT ABC).
★ Adapter doesn't need to inherit — just match method signatures.

Ref: Doc 02 §2.3
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from core.entities.tick import Tick
from core.value_objects import Symbol


class MarketDataPort(Protocol):
    """Inbound port: stream market ticks from any broker."""

    async def connect(self) -> None:
        """Establish connection to market data source."""
        ...

    async def disconnect(self) -> None:
        """Gracefully disconnect from market data source."""
        ...

    async def subscribe(self, symbols: list[Symbol]) -> None:
        """Subscribe to market data for given symbols."""
        ...

    def stream(self) -> AsyncIterator[Tick]:
        """Stream ticks as an async iterator."""
        ...
