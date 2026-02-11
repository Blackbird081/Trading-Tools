"""Portfolio entities — Position, CashBalance, PortfolioState.

★ T+2.5 settlement awareness: sellable_qty reflects what's actually sellable NOW.
★ Source of truth: broker API (SSI/DNSE), NEVER computed locally.

Ref: Doc 05 §3.3
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from core.value_objects import Price, Quantity, Symbol


@dataclass(frozen=True, slots=True)
class Position:
    """A single stock position with T+2.5 settlement awareness.

    ★ INVARIANT: sellable_qty <= quantity (always)
    ★ INVARIANT: sellable_qty reflects T+2.5 settlement
    ★ Source of truth: broker API (SSI stockPosition)
    """

    symbol: Symbol
    quantity: Quantity  # Total on-hand (all settlement states)
    sellable_qty: Quantity  # Settled — available to sell NOW
    receiving_t1: Quantity  # Will settle tomorrow
    receiving_t2: Quantity  # Will settle day after tomorrow
    avg_price: Price  # Cost basis (weighted average)
    market_price: Price  # Current market price

    @property
    def unrealized_pnl(self) -> Decimal:
        """PnL if all shares were sold at market price."""
        return (Decimal(str(self.market_price)) - Decimal(str(self.avg_price))) * Decimal(
            self.quantity
        )

    @property
    def unrealized_pnl_pct(self) -> Decimal:
        """PnL as percentage of cost basis."""
        if self.avg_price == 0:
            return Decimal("0")
        return (Decimal(str(self.market_price)) - Decimal(str(self.avg_price))) / Decimal(
            str(self.avg_price)
        )

    @property
    def market_value(self) -> Decimal:
        """Current market value of this position."""
        return Decimal(str(self.market_price)) * Decimal(self.quantity)


@dataclass(frozen=True, slots=True)
class CashBalance:
    """Cash position with T+2.5 settlement awareness.

    ★ cashBal: Tiền mặt THỰC CÓ (settled cash).
    ★ purchasing_power: Sức mua (bao gồm margin nếu có).
    ★ CRITICAL: Dùng purchasing_power cho BUY validation,
      dùng cash_bal cho withdrawal/transfer validation.
    """

    cash_bal: Decimal  # Settled cash balance
    purchasing_power: Decimal  # Available buying power (incl. margin)
    pending_settlement: Decimal  # Cash from sells waiting to settle

    @property
    def total_available(self) -> Decimal:
        """Conservative: only confirmed cash."""
        return self.cash_bal


@dataclass(frozen=True, slots=True)
class PortfolioState:
    """Complete portfolio snapshot at a point in time.

    ★ ALWAYS sourced from broker API (SSI/DNSE), NEVER computed locally.
    ★ Local computation may drift from broker state due to T+2.5 timing.
    """

    positions: tuple[Position, ...]  # Tuple for immutability
    cash: CashBalance
    synced_at: datetime

    @property
    def net_asset_value(self) -> Decimal:
        """NAV = sum(position market values) + cash balance."""
        position_value = sum(p.market_value for p in self.positions)
        return position_value + self.cash.cash_bal

    @property
    def purchasing_power(self) -> Decimal:
        """Sức mua hiện tại."""
        return self.cash.purchasing_power

    def get_position(self, symbol: Symbol) -> Position | None:
        """Find position by symbol."""
        for p in self.positions:
            if p.symbol == symbol:
                return p
        return None

    def get_sellable_qty(self, symbol: Symbol) -> int:
        """Get the quantity available to sell RIGHT NOW.

        Returns 0 if no position exists for the symbol.
        """
        position = self.get_position(symbol)
        if position is None:
            return 0
        return position.sellable_qty
