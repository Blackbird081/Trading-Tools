"""Portfolio rebalance — compute target allocation adjustments.

★ Stub for Phase 1 — full implementation with PyPortfolioOpt in Phase 3.
★ Pure function: current state + target in, adjustments out. No I/O.

Ref: Doc 02 §2.4
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.entities.order import OrderSide
from core.value_objects import Price, Quantity, Symbol


@dataclass(frozen=True, slots=True)
class RebalanceAction:
    """A single rebalance action — buy or sell to reach target allocation."""

    symbol: Symbol
    side: OrderSide
    quantity: Quantity
    target_price: Price
    reason: str


@dataclass(frozen=True, slots=True)
class RebalancePlan:
    """Complete rebalance plan — set of actions to reach target allocation."""

    actions: tuple[RebalanceAction, ...]
    total_buy_value: Decimal
    total_sell_value: Decimal


def compute_rebalance(
    current_positions: dict[Symbol, int],
    target_weights: dict[Symbol, Decimal],
    total_nav: Decimal,
    current_prices: dict[Symbol, Price],
) -> RebalancePlan:
    """Compute rebalance actions to align portfolio with target weights.

    ★ Phase 1 stub — basic equal-weight rebalance.
    ★ Phase 3 will implement Efficient Frontier optimization.

    Args:
        current_positions: symbol → current quantity held.
        target_weights: symbol → target % of NAV (0.0 to 1.0).
        total_nav: Total portfolio value.
        current_prices: symbol → current market price.

    Returns:
        RebalancePlan with buy/sell actions.
    """
    actions: list[RebalanceAction] = []
    total_buy = Decimal("0")
    total_sell = Decimal("0")

    for symbol, target_weight in target_weights.items():
        price = current_prices.get(symbol)
        if price is None:
            continue

        price_dec = Decimal(str(price))
        if price_dec <= 0:
            continue

        target_value = total_nav * target_weight
        current_qty = current_positions.get(symbol, 0)
        current_value = price_dec * Decimal(current_qty)

        diff_value = target_value - current_value
        diff_qty = int(diff_value / price_dec)

        # Round to lot size 100
        diff_qty = (diff_qty // 100) * 100

        if diff_qty > 0:
            action = RebalanceAction(
                symbol=symbol,
                side=OrderSide.BUY,
                quantity=Quantity(diff_qty),
                target_price=price,
                reason=f"Increase allocation to {target_weight:.0%}",
            )
            actions.append(action)
            total_buy += price_dec * Decimal(diff_qty)
        elif diff_qty < 0:
            action = RebalanceAction(
                symbol=symbol,
                side=OrderSide.SELL,
                quantity=Quantity(abs(diff_qty)),
                target_price=price,
                reason=f"Decrease allocation to {target_weight:.0%}",
            )
            actions.append(action)
            total_sell += price_dec * Decimal(abs(diff_qty))

    return RebalancePlan(
        actions=tuple(actions),
        total_buy_value=total_buy,
        total_sell_value=total_sell,
    )
