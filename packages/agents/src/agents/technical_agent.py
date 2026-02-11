from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from agents.state import AgentPhase, AgentState, SignalAction, TechnicalScore

logger = logging.getLogger("agents.technical")


def compute_indicators(ohlcv_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute technical indicators from OHLCV data.

    Pure function — no side effects. Can run in ProcessPoolExecutor.
    Falls back to simple scoring if pandas-ta unavailable.
    """
    if len(ohlcv_data) < 2:
        return {
            "rsi_14": 50.0,
            "macd_signal": "neutral",
            "bb_position": "inside",
            "trend_ma": "neutral",
            "composite_score": 0.0,
            "recommended_action": "HOLD",
        }

    try:
        import pandas as pd

        df = pd.DataFrame(ohlcv_data)

        # Try pandas-ta for full indicators
        try:
            import pandas_ta as ta  # noqa: F401  # type: ignore[import-untyped]

            df.ta.rsi(length=14, append=True)
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            df.ta.bbands(length=20, std=2, append=True)
            df.ta.sma(length=50, append=True)
            df.ta.sma(length=200, append=True)
        except ImportError:
            # Fallback: compute basic indicators manually
            df["RSI_14"] = _simple_rsi(df["close"], 14)
            df["SMA_50"] = df["close"].rolling(50).mean()
            df["SMA_200"] = df["close"].rolling(200).mean()

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 2 else latest
        return _score_from_indicators(latest, prev)

    except ImportError:
        # No pandas at all — use pure Python fallback
        return _simple_score(ohlcv_data)


def _score_from_indicators(latest: Any, prev: Any) -> dict[str, Any]:
    """Score from pandas Series with indicator columns."""
    score = 0.0

    # RSI Scoring (+-3 points)
    rsi = float(latest.get("RSI_14", 50) or 50)
    if rsi < 30:
        score += 3.0
    elif rsi < 40:
        score += 1.5
    elif rsi > 70:
        score -= 3.0
    elif rsi > 60:
        score -= 1.5

    # MACD Scoring (+-3 points)
    macd_val = float(latest.get("MACD_12_26_9", 0) or 0)
    macd_sig = float(latest.get("MACDs_12_26_9", 0) or 0)
    prev_macd = float(prev.get("MACD_12_26_9", 0) or 0)
    prev_sig = float(prev.get("MACDs_12_26_9", 0) or 0)
    macd_signal = "neutral"
    if macd_val > macd_sig and prev_macd <= prev_sig:
        score += 3.0
        macd_signal = "bullish_cross"
    elif macd_val < macd_sig and prev_macd >= prev_sig:
        score -= 3.0
        macd_signal = "bearish_cross"

    # Bollinger Bands Scoring (+-2 points)
    close = float(latest.get("close", 0) or 0)
    bb_lower = float(latest.get("BBL_20_2.0", close) or close)
    bb_upper = float(latest.get("BBU_20_2.0", close) or close)
    bb_position = "inside"
    if close <= bb_lower:
        score += 2.0
        bb_position = "below_lower"
    elif close >= bb_upper:
        score -= 2.0
        bb_position = "above_upper"

    # Trend MA50/MA200 (+-2 points)
    ma50 = float(latest.get("SMA_50", 0) or 0)
    ma200 = float(latest.get("SMA_200", 0) or 0)
    trend_ma = "neutral"
    if ma50 > 0 and ma200 > 0:
        if ma50 > ma200:
            score += 2.0
            trend_ma = "golden_cross"
        elif ma50 < ma200:
            score -= 2.0
            trend_ma = "death_cross"

    # Determine action
    if score >= 5.0:
        action = "BUY"
    elif score <= -5.0:
        action = "SELL"
    else:
        action = "HOLD"

    return {
        "rsi_14": rsi,
        "macd_signal": macd_signal,
        "bb_position": bb_position,
        "trend_ma": trend_ma,
        "composite_score": score,
        "recommended_action": action,
    }


def _simple_rsi(series: Any, period: int = 14) -> Any:
    """Simple RSI calculation without pandas-ta."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, float("inf"))
    return 100 - (100 / (1 + rs))


def _simple_score(ohlcv_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Fallback pure-Python scoring without pandas."""
    if len(ohlcv_data) < 2:
        return {
            "rsi_14": 50.0,
            "macd_signal": "neutral",
            "bb_position": "inside",
            "trend_ma": "neutral",
            "composite_score": 0.0,
            "recommended_action": "HOLD",
        }

    prev_close = float(ohlcv_data[-2].get("close", 0) or 0)
    curr_close = float(ohlcv_data[-1].get("close", 0) or 0)

    if prev_close <= 0:
        return {
            "rsi_14": 50.0,
            "macd_signal": "neutral",
            "bb_position": "inside",
            "trend_ma": "neutral",
            "composite_score": 0.0,
            "recommended_action": "HOLD",
        }

    change_pct = (curr_close - prev_close) / prev_close
    score = max(-10.0, min(10.0, change_pct * 100))
    action = "BUY" if score >= 5.0 else ("SELL" if score <= -5.0 else "HOLD")

    return {
        "rsi_14": 50.0,
        "macd_signal": "neutral",
        "bb_position": "inside",
        "trend_ma": "neutral",
        "composite_score": score,
        "recommended_action": action,
    }


class TechnicalAgent:
    """Performs technical analysis on screened candidates."""

    def __init__(self, tick_repo: Any) -> None:
        self._tick_repo = tick_repo

    async def run(self, state: AgentState) -> dict[str, Any]:
        """LangGraph node: analyze all watchlist symbols."""
        watchlist = state.get("watchlist", [])
        threshold = state.get("score_threshold", 5.0)

        scores: list[TechnicalScore] = []
        top_candidates: list[Any] = []
        now = datetime.now(UTC)

        for item in watchlist:
            ohlcv = await self._get_ohlcv(item.symbol)
            result = compute_indicators(ohlcv)

            tech_score = TechnicalScore(
                symbol=item.symbol,
                rsi_14=result["rsi_14"],
                macd_signal=result["macd_signal"],
                bb_position=result["bb_position"],
                trend_ma=result["trend_ma"],
                composite_score=result["composite_score"],
                recommended_action=SignalAction(result["recommended_action"]),
                analysis_timestamp=now,
            )
            scores.append(tech_score)

            if abs(result["composite_score"]) >= threshold:
                top_candidates.append(item.symbol)

        logger.info(
            "Technical analysis: %d scored, %d above threshold",
            len(scores),
            len(top_candidates),
        )
        return {
            "phase": AgentPhase.RISK_CHECKING,
            "technical_scores": scores,
            "top_candidates": top_candidates,
        }

    async def _get_ohlcv(self, symbol: Any) -> list[dict[str, Any]]:
        """Fetch OHLCV data from tick repo."""
        try:
            # Prefer async method first
            get_ohlcv = getattr(self._tick_repo, "get_ohlcv", None)
            if callable(get_ohlcv):
                result: list[dict[str, Any]] = await get_ohlcv(symbol)
                return result
            # Fallback to sync method in thread
            get_ohlcv_sync = getattr(self._tick_repo, "get_ohlcv_sync", None)
            if callable(get_ohlcv_sync):
                import asyncio

                result2: list[dict[str, Any]] = await asyncio.to_thread(
                    get_ohlcv_sync,
                    symbol,
                    days=200,
                )
                return result2
            return []
        except Exception:
            logger.exception("Failed to get OHLCV for %s", symbol)
            return []
