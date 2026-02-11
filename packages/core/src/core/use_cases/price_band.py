"""Price band enforcement — ceiling/floor/tick size calculation.

★ REGULATORY CONSTRAINT — these limits are SET BY LAW, not configurable.
★ Any order with price outside [floor, ceiling] will be REJECTED by exchange.
★ Our system rejects BEFORE sending to broker.

Ref: Doc 05 §3.5
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_UP, Decimal

from core.entities.tick import Exchange
from core.value_objects import Price, Symbol

# ── Price Band Rules (Regulatory) ────────────────────────────
# These are SET BY LAW — not configurable. Hardcode defensively.

_PRICE_BAND_PCT: dict[Exchange, Decimal] = {
    Exchange.HOSE: Decimal("0.07"),  # ±7%
    Exchange.HNX: Decimal("0.10"),  # ±10%
    Exchange.UPCOM: Decimal("0.15"),  # ±15%
}

# Tick size rules (HOSE) — price step depends on price level
_HOSE_TICK_SIZES: list[tuple[Decimal, Decimal]] = [
    (Decimal("10000"), Decimal("10")),  # Price < 10,000: tick = 10 VND
    (Decimal("50000"), Decimal("50")),  # 10,000 ≤ Price < 50,000: tick = 50
    (Decimal("999999999"), Decimal("100")),  # Price ≥ 50,000: tick = 100
]


@dataclass(frozen=True, slots=True)
class PriceBand:
    """Ceiling and floor prices for a symbol on a given trading day."""

    symbol: Symbol
    exchange: Exchange
    reference_price: Price  # Giá tham chiếu (opening reference)
    ceiling_price: Price  # Giá trần (max allowed)
    floor_price: Price  # Giá sàn (min allowed)
    tick_size: Decimal  # Bước giá (min price increment)


def calculate_price_band(
    symbol: Symbol,
    exchange: Exchange,
    reference_price: Price,
) -> PriceBand:
    """Calculate ceiling/floor prices from reference price.

    ★ REGULATORY CONSTRAINT — these limits are absolute.
    ★ Price must snap to tick size grid.
    """
    band_pct = _PRICE_BAND_PCT[exchange]
    ref = Decimal(str(reference_price))

    # Calculate raw ceiling/floor
    raw_ceiling = ref * (1 + band_pct)
    raw_floor = ref * (1 - band_pct)

    # Snap to tick size
    tick = _get_tick_size(exchange, ref)
    ceiling = Price(_snap_down(raw_ceiling, tick))  # Round DOWN for ceiling
    floor = Price(_snap_up(raw_floor, tick))  # Round UP for floor

    return PriceBand(
        symbol=symbol,
        exchange=exchange,
        reference_price=reference_price,
        ceiling_price=ceiling,
        floor_price=floor,
        tick_size=tick,
    )


def validate_order_price(
    price: Price,
    band: PriceBand,
) -> tuple[bool, str]:
    """Validate that order price is within regulatory price band.

    Returns: (is_valid, reason)

    ★ This check is MANDATORY. Bypass = regulatory violation.
    ★ Applied in Risk Agent BEFORE any order reaches the broker.
    """
    price_dec = Decimal(str(price))
    ceiling_dec = Decimal(str(band.ceiling_price))
    floor_dec = Decimal(str(band.floor_price))

    if price_dec > ceiling_dec:
        return False, (
            f"Price {price} exceeds ceiling {band.ceiling_price} "
            f"(ref: {band.reference_price}, band: ±"
            f"{_PRICE_BAND_PCT[band.exchange]:.0%})"
        )

    if price_dec < floor_dec:
        return False, (
            f"Price {price} below floor {band.floor_price} "
            f"(ref: {band.reference_price}, band: ±"
            f"{_PRICE_BAND_PCT[band.exchange]:.0%})"
        )

    # Validate tick size alignment
    remainder = price_dec % band.tick_size
    if remainder != 0:
        return False, (
            f"Price {price} not aligned to tick size {band.tick_size}. "
            f"Nearest valid: {_snap_down(price_dec, band.tick_size)}"
        )

    return True, "Price within valid range"


def _get_tick_size(exchange: Exchange, price: Decimal) -> Decimal:
    """Get tick size based on exchange and price level."""
    if exchange != Exchange.HOSE:
        return Decimal("100")  # HNX and UPCOM: fixed 100 VND

    for threshold, tick in _HOSE_TICK_SIZES:
        if price < threshold:
            return tick
    return Decimal("100")


def _snap_down(value: Decimal, tick: Decimal) -> Decimal:
    """Round down to nearest tick."""
    return (value / tick).quantize(Decimal("1"), rounding=ROUND_DOWN) * tick


def _snap_up(value: Decimal, tick: Decimal) -> Decimal:
    """Round up to nearest tick."""
    return (value / tick).quantize(Decimal("1"), rounding=ROUND_UP) * tick
