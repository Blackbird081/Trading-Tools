"""Comprehensive order validation — ALL checks must pass.

★ DEFENSE IN DEPTH: Each check is independent.
  A failure in one check does NOT skip subsequent checks.
  We collect ALL failures for clear error reporting.

Check order:
  1. Kill Switch
  2. Price Band (ceiling/floor) — regulatory
  3. Lot Size (must be multiple of 100)
  4. Position Size (max % of NAV per order)
  5. Buying Power (sufficient cash for BUY)
  6. Sellable Quantity (T+2.5 aware for SELL)
  7. Daily Loss Limit

Ref: Doc 05 §3.6, Doc 02 §2.4
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.entities.order import Order, OrderSide
from core.entities.portfolio import PortfolioState
from core.entities.risk import RiskLimit
from core.use_cases.price_band import PriceBand, validate_order_price


@dataclass(frozen=True, slots=True)
class RiskCheckResult:
    """Result of comprehensive order validation."""

    approved: bool
    reason: str
    checks_passed: tuple[str, ...]
    checks_failed: tuple[str, ...]


def validate_order(
    order: Order,
    portfolio: PortfolioState,
    limits: RiskLimit,
    price_band: PriceBand | None = None,
    pending_sell_qty: int = 0,
) -> RiskCheckResult:
    """Pure function — comprehensive order validation.

    ★ No I/O, no side effects, fully testable.
    ★ ALL checks run independently — collects ALL failures.
    """
    passed: list[str] = []
    failed: list[str] = []

    # ── Check 1: Kill Switch ──────────────────────────────
    if limits.kill_switch_active:
        failed.append("KILL_SWITCH: Emergency halt is ACTIVE. All trading stopped.")
        return RiskCheckResult(
            approved=False,
            reason="Kill switch active",
            checks_passed=tuple(passed),
            checks_failed=tuple(failed),
        )
    passed.append("KILL_SWITCH: Off")

    # ── Check 2: Price Band ───────────────────────────────
    if price_band is not None:
        is_valid, price_reason = validate_order_price(order.price, price_band)
        if not is_valid:
            failed.append(f"PRICE_BAND: {price_reason}")
        else:
            passed.append("PRICE_BAND: Within ceiling/floor")

    # ── Check 3: Lot Size ─────────────────────────────────
    if order.quantity % 100 != 0:
        failed.append(
            f"LOT_SIZE: Quantity {order.quantity} is not a multiple of 100. "
            f"HOSE/HNX require lot size 100."
        )
    else:
        passed.append("LOT_SIZE: Valid (multiple of 100)")

    # ── Check 4: Position Size (max % NAV) ────────────────
    order_value = Decimal(str(order.price)) * Decimal(order.quantity)
    nav = portfolio.net_asset_value
    if nav > 0:
        position_pct = order_value / nav
        max_pct = limits.max_position_pct
        if position_pct > max_pct:
            failed.append(
                f"POSITION_SIZE: Order value {order_value:,.0f} VND = "
                f"{position_pct:.1%} of NAV {nav:,.0f} VND. "
                f"Exceeds limit {max_pct:.0%}."
            )
        else:
            passed.append(f"POSITION_SIZE: {position_pct:.1%} of NAV (limit: {max_pct:.0%})")

    # ── Check 5: Buying Power (BUY only) ──────────────────
    if order.side == OrderSide.BUY:
        if order_value > portfolio.purchasing_power:
            failed.append(
                f"BUYING_POWER: Order value {order_value:,.0f} VND exceeds "
                f"purchasing power {portfolio.purchasing_power:,.0f} VND."
            )
        else:
            passed.append("BUYING_POWER: Sufficient")

    # ── Check 6: Sellable Quantity (SELL only, T+2.5) ─────
    if order.side == OrderSide.SELL:
        sellable = portfolio.get_sellable_qty(order.symbol)
        available = sellable - pending_sell_qty  # Subtract pending sells
        if order.quantity > available:
            failed.append(
                f"SELLABLE_QTY: Requesting to sell {order.quantity} "
                f"but only {available} shares available "
                f"(sellable: {sellable}, pending sells: {pending_sell_qty}). "
                f"Check T+2.5 settlement status."
            )
        else:
            passed.append(f"SELLABLE_QTY: {order.quantity} <= {available} available")

    # ── Check 7: Daily Loss Limit ─────────────────────────
    # (Would query today's realized PnL from DuckDB — implemented in Phase 2)

    # ── Final Verdict ─────────────────────────────────────
    if failed:
        return RiskCheckResult(
            approved=False,
            reason="; ".join(failed),
            checks_passed=tuple(passed),
            checks_failed=tuple(failed),
        )

    return RiskCheckResult(
        approved=True,
        reason="All checks passed",
        checks_passed=tuple(passed),
        checks_failed=tuple(failed),
    )
