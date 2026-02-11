from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from core.entities.tick import Exchange, Tick
from core.value_objects import Price, Quantity, Symbol

from adapters.retry import RetryConfig, calculate_backoff_delay

logger = logging.getLogger("ws.ssi")


class ConnectionState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FATAL = "fatal"


class SSIMarketWebSocket:
    """Resilient WebSocket client for SSI market data.

    Implements MarketDataPort (structural subtyping via Protocol).
    """

    def __init__(
        self,
        url: str,
        auth_client: Any,
        reconnect_config: RetryConfig | None = None,
    ) -> None:
        self._url = url
        self._auth = auth_client
        self._ws: Any = None
        self._state = ConnectionState.DISCONNECTED
        self._reconnect_attempt = 0
        self._last_message_at: float = 0.0
        self._subscribed_symbols: list[Symbol] = []
        self._config = reconnect_config or RetryConfig(
            max_retries=0,
            base_delay=1.0,
            max_delay=60.0,
            jitter=True,
        )

    @property
    def state(self) -> ConnectionState:
        return self._state

    async def connect(self) -> None:
        """Establish WebSocket connection with authentication."""
        import websockets

        self._state = ConnectionState.CONNECTING
        try:
            token = await self._auth.get_access_token()
            self._ws = await websockets.connect(
                self._url,
                additional_headers={"Authorization": f"Bearer {token}"},
                ping_interval=30.0,
                ping_timeout=10.0,
                close_timeout=5.0,
                max_size=2**20,
            )
            self._state = ConnectionState.CONNECTED
            self._reconnect_attempt = 0
            self._last_message_at = asyncio.get_event_loop().time()
            logger.info("WebSocket connected to %s", self._url)
        except Exception:
            self._state = ConnectionState.DISCONNECTED
            raise

    async def disconnect(self) -> None:
        """Graceful shutdown."""
        self._state = ConnectionState.DISCONNECTED
        if self._ws is not None:
            await self._ws.close(code=1000, reason="Client shutdown")
            self._ws = None

    async def subscribe(self, symbols: list[Symbol]) -> None:
        """Subscribe to market data for given symbols."""
        self._subscribed_symbols = symbols
        if self._ws is not None and self._state == ConnectionState.CONNECTED:
            msg = json.dumps({"action": "subscribe", "symbols": [str(s) for s in symbols]})
            await self._ws.send(msg)

    def stream(self) -> AsyncIterator[Tick]:
        """Stream ticks as an async iterator."""
        return self._stream_impl()

    async def _stream_impl(self) -> AsyncIterator[Tick]:
        """Internal stream implementation with auto-reconnect."""
        while self._state != ConnectionState.FATAL:
            try:
                if self._ws is None or self._state != ConnectionState.CONNECTED:
                    await self._reconnect_with_backoff()
                assert self._ws is not None
                async for raw_message in self._ws:
                    self._last_message_at = asyncio.get_event_loop().time()
                    self._reconnect_attempt = 0
                    tick = self._parse_tick(str(raw_message))
                    if tick is not None:
                        yield tick
            except Exception as exc:
                logger.warning("WebSocket error: %s. Will reconnect.", exc)
                self._ws = None
                self._state = ConnectionState.RECONNECTING

    async def _reconnect_with_backoff(self) -> None:
        """Reconnect with exponential backoff."""
        while True:
            self._state = ConnectionState.RECONNECTING
            delay = calculate_backoff_delay(self._reconnect_attempt, self._config)
            logger.info(
                "WebSocket reconnect attempt %d — waiting %.1fs...",
                self._reconnect_attempt + 1,
                delay,
            )
            await asyncio.sleep(delay)
            self._reconnect_attempt += 1
            try:
                await self.connect()
                if self._subscribed_symbols:
                    await self.subscribe(self._subscribed_symbols)
                return
            except Exception:
                logger.debug("Reconnect attempt %d failed", self._reconnect_attempt)
                continue

    @staticmethod
    def _parse_tick(raw: str) -> Tick | None:
        """Parse raw JSON message to Tick entity."""
        try:
            data = json.loads(raw)
            exchange_map = {"HOSE": Exchange.HOSE, "HNX": Exchange.HNX, "UPCOM": Exchange.UPCOM}
            exchange_str = data.get("Exchange", data.get("exchange", "HOSE"))
            exchange = exchange_map.get(exchange_str, Exchange.HOSE)
            return Tick(
                symbol=Symbol(data.get("Symbol", data.get("symbol", ""))),
                price=Price(Decimal(str(data.get("LastPrice", data.get("price", 0))))),
                volume=Quantity(int(data.get("LastVol", data.get("volume", 0)))),
                exchange=exchange,
                timestamp=datetime.now(),
            )
        except (KeyError, ValueError, TypeError):
            logger.warning("Failed to parse tick message")
            return None
