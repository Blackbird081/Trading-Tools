"""Integration test: Data Agent ingestion pipeline.

★ FakeMarketData yields ticks → DataAgent buffers → flushes to FakeTickRepo.
★ Verifies: tick count matches, no data loss.

Ref: Doc 02 §5.5
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal

import pytest
from agents.data_agent import DataAgent
from core.entities.tick import Exchange, Tick
from core.value_objects import Price, Quantity, Symbol

# ── Fake Implementations (structural subtyping) ─────────────────


class FakeMarketData:
    """Fake MarketDataPort that yields N ticks then stops."""

    def __init__(self, ticks: list[Tick]) -> None:
        self._ticks = ticks
        self._connected = False

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def subscribe(self, symbols: list[Symbol]) -> None:
        pass

    def stream(self) -> AsyncIterator[Tick]:
        return self._stream_impl()

    async def _stream_impl(self) -> AsyncIterator[Tick]:
        for tick in self._ticks:
            yield tick
            await asyncio.sleep(0)  # Yield control


class FakeTickRepo:
    """Fake TickRepository that stores ticks in memory."""

    def __init__(self) -> None:
        self.stored: list[Tick] = []

    async def insert_batch(self, ticks: list[Tick]) -> int:
        self.stored.extend(ticks)
        return len(ticks)

    async def get_ohlcv(self, *args: object, **kwargs: object) -> list[dict[str, object]]:
        return []

    async def asof_join_orders(self, *args: object, **kwargs: object) -> list[dict[str, object]]:
        return []


# ── Helper ───────────────────────────────────────────────────────


def _make_ticks(count: int) -> list[Tick]:
    """Generate N deterministic ticks."""
    from datetime import timedelta

    base = datetime(2026, 2, 10, 9, 0, 0)
    return [
        Tick(
            symbol=Symbol("FPT"),
            price=Price(Decimal("98500") + Decimal(str(i * 10))),
            volume=Quantity(100 + i),
            exchange=Exchange.HOSE,
            timestamp=base + timedelta(seconds=i),
        )
        for i in range(count)
    ]


# ── Tests ────────────────────────────────────────────────────────


class TestDataAgent:
    """Data Agent ingestion pipeline tests."""

    @pytest.mark.asyncio
    async def test_ingest_and_flush_100_ticks(self) -> None:
        """100 ticks → buffer → flush → all stored in repo."""
        ticks = _make_ticks(100)
        market = FakeMarketData(ticks)
        repo = FakeTickRepo()

        agent = DataAgent(
            market_data=market,
            tick_repo=repo,
            flush_interval=0.05,  # Flush every 50ms for fast test
        )

        # Run with timeout — agent stops when stream ends
        try:
            await asyncio.wait_for(agent.start(), timeout=2.0)
        except (TimeoutError, ExceptionGroup):
            await agent.stop()

        assert agent.total_ingested == 100
        assert agent.total_flushed == len(repo.stored)
        # All ticks should eventually be flushed
        assert len(repo.stored) == 100

    @pytest.mark.asyncio
    async def test_ingest_1000_ticks_no_data_loss(self) -> None:
        """1000 ticks — verify zero data loss."""
        ticks = _make_ticks(1000)
        market = FakeMarketData(ticks)
        repo = FakeTickRepo()

        agent = DataAgent(
            market_data=market,
            tick_repo=repo,
            flush_interval=0.02,
        )

        try:
            await asyncio.wait_for(agent.start(), timeout=5.0)
        except (TimeoutError, ExceptionGroup):
            await agent.stop()

        assert agent.total_ingested == 1000
        assert len(repo.stored) == 1000

    @pytest.mark.asyncio
    async def test_empty_stream(self) -> None:
        """Empty stream — agent ingests nothing."""
        market = FakeMarketData([])
        repo = FakeTickRepo()

        agent = DataAgent(
            market_data=market,
            tick_repo=repo,
            flush_interval=0.05,
        )

        try:
            await asyncio.wait_for(agent.start(), timeout=1.0)
        except (TimeoutError, ExceptionGroup):
            await agent.stop()

        assert agent.total_ingested == 0
        assert len(repo.stored) == 0

    @pytest.mark.asyncio
    async def test_stop_flushes_remaining_buffer(self) -> None:
        """Stopping agent should flush any remaining buffered ticks."""
        ticks = _make_ticks(50)
        market = FakeMarketData(ticks)
        repo = FakeTickRepo()

        agent = DataAgent(
            market_data=market,
            tick_repo=repo,
            flush_interval=10.0,  # Very long — won't auto-flush
        )

        import contextlib

        with contextlib.suppress(TimeoutError, ExceptionGroup):
            await asyncio.wait_for(agent.start(), timeout=1.0)

        # Manual stop should flush remaining
        await agent.stop()

        assert agent.total_ingested == 50
        assert len(repo.stored) == 50
