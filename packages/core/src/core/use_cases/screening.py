"""Screening — filter symbols based on criteria.

★ Stub for Phase 1 — full implementation in Phase 3.
★ Pure function: filters in, watchlist out. No I/O.

Ref: Doc 02 §2.4
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.value_objects import Symbol


@dataclass(frozen=True, slots=True)
class ScreeningCriteria:
    """Criteria for stock screening."""

    min_volume: int = 100_000  # Minimum daily volume
    min_price: Decimal = Decimal("5000")  # Minimum price (VND)
    max_price: Decimal = Decimal("500000")  # Maximum price (VND)
    exchanges: tuple[str, ...] = ("HOSE",)  # Target exchanges


@dataclass(frozen=True, slots=True)
class ScreeningResult:
    """Result of stock screening."""

    symbols: tuple[Symbol, ...]
    criteria_used: ScreeningCriteria
    total_scanned: int
    total_matched: int


def run_screening(
    candidates: list[dict[str, object]],
    criteria: ScreeningCriteria,
) -> ScreeningResult:
    """Filter symbols based on screening criteria.

    ★ Pure function — no I/O, no side effects.
    ★ Candidates come from Vnstock adapter (fetched externally).

    Args:
        candidates: List of dicts with keys: symbol, exchange, price, volume.
        criteria: Screening criteria to apply.

    Returns:
        ScreeningResult with matched symbols.
    """
    matched: list[Symbol] = []

    for candidate in candidates:
        symbol = str(candidate.get("symbol", ""))
        exchange = str(candidate.get("exchange", ""))
        price = Decimal(str(candidate.get("price", 0)))
        volume_raw = candidate.get("volume", 0)
        volume = int(volume_raw) if isinstance(volume_raw, (int, float, str)) else 0

        # Apply filters
        if exchange not in criteria.exchanges:
            continue
        if volume < criteria.min_volume:
            continue
        if price < criteria.min_price or price > criteria.max_price:
            continue

        matched.append(Symbol(symbol))

    return ScreeningResult(
        symbols=tuple(matched),
        criteria_used=criteria,
        total_scanned=len(candidates),
        total_matched=len(matched),
    )
