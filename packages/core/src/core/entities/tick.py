"""Tick entity — single market tick data point.

★ Immutable (frozen=True) — thread-safe by default.
★ slots=True — ~30-40% less memory than __dict__.

Ref: Doc 02 §2.2
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from core.value_objects import Price, Quantity, Symbol


class Exchange(StrEnum):
    """Vietnamese stock exchanges."""

    HOSE = "HOSE"  # Ho Chi Minh Stock Exchange
    HNX = "HNX"  # Hanoi Stock Exchange
    UPCOM = "UPCOM"  # Unlisted Public Company Market


@dataclass(frozen=True, slots=True)
class Tick:
    """Single market tick — immutable, hashable.

    Represents one price/volume update from the exchange.
    """

    symbol: Symbol
    price: Price
    volume: Quantity
    exchange: Exchange
    timestamp: datetime

    def is_ceiling(self, ref_price: Price) -> bool:
        """Check if this tick's price hits the ceiling (giá trần)."""
        from decimal import Decimal

        return self.price >= Price(Decimal(str(ref_price)) * Decimal("1.07"))

    def is_floor(self, ref_price: Price) -> bool:
        """Check if this tick's price hits the floor (giá sàn)."""
        from decimal import Decimal

        return self.price <= Price(Decimal(str(ref_price)) * Decimal("0.93"))


@dataclass(frozen=True, slots=True)
class OHLCV:
    """Open-High-Low-Close-Volume candle — aggregated tick data."""

    symbol: Symbol
    exchange: Exchange
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Quantity
    timestamp: datetime
