from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from agents.state import AgentPhase, AgentState, ExecutionPlan, SignalAction

logger = logging.getLogger("agents.executor")


class ExecutorAgent:
    """Executes approved trades via broker or dry-run mode.

    Phase 5 upgrade: live broker integration via BrokerPort.
    When dry_run=False, orders are placed through the broker adapter
    with idempotency keys to prevent duplicate placement.
    """

    def __init__(self, broker_port: Any = None) -> None:
        self._broker = broker_port

    async def run(self, state: AgentState) -> dict[str, Any]:
        """LangGraph node: create execution plans for approved trades."""
        approved = state.get("approved_trades", [])
        scores = {s.symbol: s for s in state.get("technical_scores", [])}
        assessments = {a.symbol: a for a in state.get("risk_assessments", [])}
        dry_run = state.get("dry_run", True)
        nav = state.get("current_nav", Decimal("0"))

        plans: list[ExecutionPlan] = []

        for symbol in approved:
            tech = scores.get(symbol)
            risk = assessments.get(symbol)
            if tech is None or risk is None:
                continue

            action = tech.recommended_action
            if action in (SignalAction.HOLD, SignalAction.SKIP):
                continue

            # ★ FIX: Use latest_price (actual market price) as entry price
            entry_price = risk.latest_price
            if entry_price <= 0:
                continue
            quantity = self._calculate_quantity(
                nav=nav,
                position_pct=risk.position_size_pct,
                price=entry_price,
            )
            if quantity <= 0:
                continue

            # Generate idempotency key per order intent
            run_id = state.get("run_id", "")
            idempotency_key = f"{run_id}:{symbol}:{action.value}"

            if dry_run:
                logger.info(
                    "DRY RUN: %s %s x%d @ %s",
                    action.value,
                    symbol,
                    quantity,
                    entry_price,
                )
                plan = ExecutionPlan(
                    symbol=symbol,
                    action=action,
                    quantity=quantity,
                    price=entry_price,
                    order_type="LO",
                    broker="SSI",
                    executed=False,
                    order_id=None,
                    executed_at=None,
                )
            else:
                # Live execution via broker
                order_id, executed = await self._place_live_order(
                    symbol=str(symbol),
                    side=action.value,
                    quantity=quantity,
                    price=entry_price,
                    idempotency_key=idempotency_key,
                )
                plan = ExecutionPlan(
                    symbol=symbol,
                    action=action,
                    quantity=quantity,
                    price=entry_price,
                    order_type="LO",
                    broker="SSI",
                    executed=executed,
                    order_id=order_id,
                    executed_at=datetime.now(UTC) if executed else None,
                )
                logger.info(
                    "EXECUTE: %s %s x%d @ %s -> order_id=%s",
                    action.value,
                    symbol,
                    quantity,
                    entry_price,
                    order_id,
                )

            plans.append(plan)

        return {
            "phase": AgentPhase.COMPLETED,
            "execution_plans": plans,
        }

    async def _place_live_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: Decimal,
        idempotency_key: str,
    ) -> tuple[str | None, bool]:
        """Place order via broker adapter. Returns (order_id, executed)."""
        if self._broker is None:
            logger.error("No broker configured — cannot place live order")
            return None, False

        try:
            if hasattr(self._broker, "place_order"):
                order_id: str = await self._broker.place_order(
                    symbol=symbol,
                    side=side,
                    order_type="LO",
                    quantity=quantity,
                    price=str(price),  # ★ FIX: keep Decimal precision, consistent with SSI broker "★ String, not float"
                    idempotency_key=idempotency_key,
                )
                return order_id, True
        except Exception:
            logger.exception(
                "Broker order failed: %s %s x%d",
                side,
                symbol,
                quantity,
            )

        return None, False

    @staticmethod
    def _calculate_quantity(
        nav: Decimal,
        position_pct: Decimal,
        price: Decimal,
    ) -> int:
        if price <= 0:
            return 0
        raw_qty = (nav * position_pct) / price
        # Round down to nearest lot (100 shares)
        lots = int(raw_qty) // 100
        return max(lots * 100, 0)
