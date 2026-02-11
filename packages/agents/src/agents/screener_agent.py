from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from agents.state import AgentPhase, AgentState, ScreenerResult

logger = logging.getLogger("agents.screener")


class ScreenerAgent:
    """Scans market for opportunities using screening + volume spike detection."""

    def __init__(
        self,
        screener_port: Any,
        tick_repo: Any,
    ) -> None:
        self._screener = screener_port
        self._tick_repo = tick_repo

    async def run(self, state: AgentState) -> dict[str, Any]:
        """LangGraph node function. Reads state, returns partial update."""
        max_candidates = state.get("max_candidates", 10)

        # Step 1: Fundamental screening
        raw_candidates = await self._screen_candidates()

        # Step 2: Volume spike detection
        spike_symbols = await self._detect_volume_spikes()

        # Step 3: Build watchlist
        watchlist: list[ScreenerResult] = []
        now = datetime.now(UTC)

        for candidate in raw_candidates[:max_candidates]:
            symbol = candidate.get("symbol", "")
            watchlist.append(
                ScreenerResult(
                    symbol=symbol,
                    eps_growth=float(candidate.get("eps_growth", 0.0)),
                    pe_ratio=float(candidate.get("pe_ratio", 0.0)),
                    volume_spike=symbol in spike_symbols,
                    passed_at=now,
                )
            )

        logger.info("Screener found %d candidates", len(watchlist))
        return {
            "phase": AgentPhase.ANALYZING,
            "watchlist": watchlist,
        }

    async def _screen_candidates(self) -> list[dict[str, Any]]:
        """Fetch candidates from screener port."""
        try:
            if hasattr(self._screener, "screen"):
                result: list[dict[str, Any]] = await self._screener.screen(
                    min_eps_growth=0.10,
                    max_pe_ratio=15.0,
                )
                return result
            if hasattr(self._screener, "get_screener_data"):
                result2: list[dict[str, Any]] = await self._screener.get_screener_data()
                return result2
            return []
        except Exception:
            logger.exception("Screening failed")
            return []

    async def _detect_volume_spikes(self) -> set[str]:
        """Detect volume spikes via tick repo."""
        try:
            if hasattr(self._tick_repo, "query_volume_spikes"):
                results = await self._tick_repo.query_volume_spikes(
                    threshold_multiplier=2.0,
                )
                return {r["symbol"] for r in results}
            return set()
        except Exception:
            logger.exception("Volume spike detection failed")
            return set()
