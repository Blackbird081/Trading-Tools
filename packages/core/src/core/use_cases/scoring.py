"""Technical scoring — compute technical analysis score for a symbol.

★ Stub for Phase 1 — full implementation in Phase 3 with pandas-ta.
★ Pure function: input data in, score out. No I/O.

Ref: Doc 04 §1.6
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TechnicalScore:
    """Result of technical analysis scoring."""

    score: Decimal  # -10.0 to +10.0 (negative = bearish, positive = bullish)
    rsi_signal: str  # "oversold" | "neutral" | "overbought"
    macd_signal: str  # "bullish_cross" | "neutral" | "bearish_cross"
    bb_signal: str  # "below_lower" | "within" | "above_upper"
    details: str  # Human-readable explanation


def compute_technical_score(
    ohlcv_data: list[dict[str, object]],
) -> TechnicalScore:
    """Compute a composite technical score from OHLCV data.

    ★ Phase 1 stub — returns neutral score.
    ★ Phase 3 will implement full RSI + MACD + Bollinger Bands scoring.

    Args:
        ohlcv_data: List of OHLCV candle dicts with keys:
            open, high, low, close, volume, timestamp.

    Returns:
        TechnicalScore with composite rating.
    """
    if not ohlcv_data:
        return TechnicalScore(
            score=Decimal("0"),
            rsi_signal="neutral",
            macd_signal="neutral",
            bb_signal="within",
            details="No data available for analysis",
        )

    # Phase 1: Basic price change scoring
    if len(ohlcv_data) < 2:
        return TechnicalScore(
            score=Decimal("0"),
            rsi_signal="neutral",
            macd_signal="neutral",
            bb_signal="within",
            details="Insufficient data (need >= 2 candles)",
        )

    latest_close = Decimal(str(ohlcv_data[-1].get("close", 0)))
    prev_close = Decimal(str(ohlcv_data[-2].get("close", 0)))

    change_pct = Decimal("0") if prev_close == 0 else (latest_close - prev_close) / prev_close

    # Simple scoring: map % change to -10..+10 range
    score = (change_pct * Decimal("100")).quantize(Decimal("0.1"))
    score = max(Decimal("-10"), min(Decimal("10"), score))

    return TechnicalScore(
        score=score,
        rsi_signal="neutral",
        macd_signal="neutral",
        bb_signal="within",
        details=f"Price change: {change_pct:.2%}. Full TA pending Phase 3.",
    )
