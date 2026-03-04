"""Shared metrics for local reliability evaluations.

This module powers:
- fixed-dataset benchmark metrics
- provider A/B consensus comparison
- weekly drift monitoring
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


ACTION_BUY = "BUY"
ACTION_SELL = "SELL"
ACTION_HOLD = "HOLD"


@dataclass(frozen=True)
class RecommendationOutcome:
    """Normalized recommendation with realized outcome."""

    dt: date
    symbol: str
    recommendation: str
    confidence: float
    realized_return: float


def normalize_action(value: str) -> str:
    """Normalize action labels across agents/providers."""
    raw = value.strip().upper().replace("-", "_")
    if raw in {"BUY", "STRONG_BUY", "ACCUMULATE"}:
        return ACTION_BUY
    if raw in {"SELL", "STRONG_SELL", "REDUCE", "AVOID"}:
        return ACTION_SELL
    if raw in {"HOLD", "NEUTRAL", "WAIT"}:
        return ACTION_HOLD
    return ACTION_HOLD


def load_outcomes_csv(path: Path) -> list[RecommendationOutcome]:
    """Load fixed outcome dataset from CSV."""
    rows: list[RecommendationOutcome] = []
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                RecommendationOutcome(
                    dt=datetime.strptime(row["date"], "%Y-%m-%d").date(),
                    symbol=row["symbol"].strip().upper(),
                    recommendation=normalize_action(row["recommendation"]),
                    confidence=float(row.get("confidence", 0.0)),
                    realized_return=float(row["realized_return"]),
                )
            )
    return rows


def is_correct_call(
    recommendation: str,
    realized_return: float,
    *,
    hold_band: float = 0.005,
) -> bool:
    """Evaluate call correctness against realized return."""
    action = normalize_action(recommendation)
    if action == ACTION_BUY:
        return realized_return > 0.0
    if action == ACTION_SELL:
        return realized_return < 0.0
    return abs(realized_return) <= hold_band


def strategy_return(row: RecommendationOutcome) -> float:
    """Convert recommendation + market return into strategy return."""
    if row.recommendation == ACTION_BUY:
        return row.realized_return
    if row.recommendation == ACTION_SELL:
        return -row.realized_return
    return 0.0


def precision_at_k(rows: Iterable[RecommendationOutcome], k: int) -> float:
    """Precision@K over high-confidence actionable calls."""
    actionable = [r for r in rows if r.recommendation in {ACTION_BUY, ACTION_SELL}]
    ranked = sorted(actionable, key=lambda r: r.confidence, reverse=True)
    top = ranked[: max(0, k)]
    if not top:
        return 0.0
    tp = sum(1 for row in top if is_correct_call(row.recommendation, row.realized_return, hold_band=0.0))
    return tp / len(top)


def hit_rate(rows: Iterable[RecommendationOutcome], *, hold_band: float = 0.005) -> float:
    """Overall signal hit-rate."""
    seq = list(rows)
    if not seq:
        return 0.0
    hits = sum(1 for row in seq if is_correct_call(row.recommendation, row.realized_return, hold_band=hold_band))
    return hits / len(seq)


def max_drawdown(rows: Iterable[RecommendationOutcome]) -> float:
    """Compute max drawdown from strategy equity curve."""
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for row in rows:
        equity *= 1.0 + strategy_return(row)
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def evaluate_quant_benchmark(rows: Iterable[RecommendationOutcome], *, k: int = 10) -> dict[str, float]:
    """Return benchmark metric set for roadmap acceptance."""
    seq = list(rows)
    return {
        "sample_size": float(len(seq)),
        "precision_at_k": precision_at_k(seq, k),
        "hit_rate": hit_rate(seq),
        "max_drawdown": max_drawdown(seq),
    }

