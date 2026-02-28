"""Tick entity — single market tick data point.

★ Immutable (frozen=True) — thread-safe by default.
★ slots=True — ~30-40% less memory than __dict__.

Ref: Doc 02 §2.2
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from core.value_objects import Price, Quantity, Symbol


class Exchange(StrEnum):
    """Vietnamese stock exchanges."""

    HOSE = "HOSE"  # Ho Chi Minh Stock Exchange
    HNX = "HNX"  # Hanoi Stock Exchange
    UPCOM = "UPCOM"  # Unlisted Public Company Market


# ★ VN Exchange-specific price bands (percentage from reference price)
# HOSE: ±7%, HNX: ±10%, UPCOM: ±15%
_PRICE_BAND: dict[str, Decimal] = {
    Exchange.HOSE: Decimal("0.07"),
    Exchange.HNX: Decimal("0.10"),
    Exchange.UPCOM: Decimal("0.15"),
}


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

    @property
    def price_band_pct(self) -> Decimal:
        """Get the price band percentage for this tick's exchange."""
        return _PRICE_BAND.get(self.exchange, Decimal("0.07"))

    def is_ceiling(self, ref_price: Price) -> bool:
        """Check if this tick's price hits the ceiling (giá trần).

        ★ Fix: uses exchange-specific band (HOSE=7%, HNX=10%, UPCOM=15%).
        """
        band = self.price_band_pct
        return self.price >= Price(Decimal(str(ref_price)) * (1 + band))

    def is_floor(self, ref_price: Price) -> bool:
        """Check if this tick's price hits the floor (giá sàn).

        ★ Fix: uses exchange-specific band (HOSE=7%, HNX=10%, UPCOM=15%).
        """
        band = self.price_band_pct
        return self.price <= Price(Decimal(str(ref_price)) * (1 - band))


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
