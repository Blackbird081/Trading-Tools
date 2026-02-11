from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.ports.market_data import MarketDataPort
    from core.ports.repository import TickRepository

from core.entities.tick import Tick

logger = logging.getLogger("agents.data")


class DataAgent:
    """Ingests market ticks and buffers for batch persistence.

    Two concurrent tasks: ingest (non-blocking) + flush (periodic).
    DuckDB writes offloaded to thread pool via asyncio.to_thread().
    """

    def __init__(
        self,
        market_data: MarketDataPort,
        tick_repo: TickRepository,
        flush_interval: float = 1.0,
        max_buffer_size: int = 100_000,
    ) -> None:
        self._market_data = market_data
        self._tick_repo = tick_repo
        self._flush_interval = flush_interval
        self._buffer: deque[Tick] = deque(maxlen=max_buffer_size)
        self._running = False
        self._total_ingested = 0
        self._total_flushed = 0

    @property
    def total_ingested(self) -> int:
        return self._total_ingested

    @property
    def total_flushed(self) -> int:
        return self._total_flushed

    @property
    def buffer_size(self) -> int:
        return len(self._buffer)

    async def start(self) -> None:
        """Start ingestion + flush loops concurrently."""
        self._running = True
        await self._market_data.connect()
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._ingest_loop())
            tg.create_task(self._flush_loop())

    async def stop(self) -> None:
        """Graceful shutdown — final flush before stopping."""
        self._running = False
        await self._market_data.disconnect()
        await self._flush_buffer()

    async def _ingest_loop(self) -> None:
        """Non-blocking: async for yields control between ticks."""
        async for tick in self._market_data.stream():
            self._buffer.append(tick)
            self._total_ingested += 1
            if not self._running:
                break

    async def _flush_loop(self) -> None:
        """Periodic flush — offloads DuckDB write to thread pool."""
        while self._running:
            await asyncio.sleep(self._flush_interval)
            await self._flush_buffer()

    async def _flush_buffer(self) -> None:
        """Flush buffered ticks to repository."""
        if not self._buffer:
            return
        batch = list(self._buffer)
        self._buffer.clear()
        count = await self._tick_repo.insert_batch(batch)
        self._total_flushed += count
        logger.info("Flushed %d ticks to repository (total: %d)", count, self._total_flushed)
