"""NotifierPort — outbound port for pushing updates to frontend.

★ Abstracts WebSocket broadcast behind a Protocol.
★ Interface layer implements this for real-time UI updates.

Ref: Doc 02 §2.3
"""

from __future__ import annotations

from typing import Protocol

from core.entities.signal import TradingSignal
from core.entities.tick import Tick


class NotifierPort(Protocol):
    """Outbound port: push real-time updates to connected clients."""

    async def broadcast_tick(self, tick: Tick) -> None:
        """Broadcast a tick update to all subscribed clients."""
        ...

    async def broadcast_signal(self, signal: TradingSignal) -> None:
        """Broadcast a trading signal to all connected clients."""
        ...

    async def broadcast_message(self, channel: str, payload: dict[str, object]) -> None:
        """Broadcast a generic message to a specific channel."""
        ...
