"""Order entity — immutable order with enforced state machine.

★ CRITICAL: Orders are NEVER mutated in place.
  Every state change produces a NEW Order instance.
  This guarantees audit trail integrity and thread safety.

Ref: Doc 05 §2.2
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Self

from core.value_objects import Price, Quantity, Symbol


class OrderStatus(StrEnum):
    """Order lifecycle states — whitelist approach."""

    CREATED = "CREATED"  # Local — not yet sent to broker
    PENDING = "PENDING"  # Sent to broker, awaiting match
    PARTIAL_FILL = "PARTIAL_FILL"  # Some quantity matched
    MATCHED = "MATCHED"  # Fully filled
    REJECTED = "REJECTED"  # Rejected by local risk check
    BROKER_REJECTED = "BROKER_REJECTED"  # Rejected by broker/exchange
    CANCELLED = "CANCELLED"  # Cancelled by user or system


class OrderSide(StrEnum):
    """Buy or sell."""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(StrEnum):
    """Order types supported by Vietnamese exchanges."""

    LO = "LO"  # Limit Order
    ATO = "ATO"  # At the Open
    ATC = "ATC"  # At the Close
    MP = "MP"  # Market Price


# Valid state transitions — WHITELIST approach
_VALID_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.CREATED: frozenset(
        {
            OrderStatus.PENDING,
            OrderStatus.REJECTED,
            OrderStatus.CANCELLED,
        }
    ),
    OrderStatus.PENDING: frozenset(
        {
            OrderStatus.PARTIAL_FILL,
            OrderStatus.MATCHED,
            OrderStatus.BROKER_REJECTED,
            OrderStatus.CANCELLED,
        }
    ),
    OrderStatus.PARTIAL_FILL: frozenset(
        {
            OrderStatus.PARTIAL_FILL,  # More partial fills
            OrderStatus.MATCHED,  # Final fill
            OrderStatus.CANCELLED,  # Cancel remainder
        }
    ),
    # Terminal states — NO transitions allowed
    OrderStatus.MATCHED: frozenset(),
    OrderStatus.REJECTED: frozenset(),
    OrderStatus.BROKER_REJECTED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}


class InvalidOrderTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""


@dataclass(frozen=True, slots=True)
class Order:
    """Immutable order entity with enforced state machine.

    ★ CRITICAL: Orders are NEVER mutated in place.
      Every state change produces a NEW Order instance.
    """

    order_id: str
    symbol: Symbol
    side: OrderSide
    order_type: OrderType
    quantity: Quantity  # Total requested quantity
    price: Price  # Limit price
    ceiling_price: Price  # Max allowed price (giá trần)
    floor_price: Price  # Min allowed price (giá sàn)

    status: OrderStatus
    filled_quantity: Quantity  # Quantity already matched
    avg_fill_price: Price  # Weighted average fill price

    broker_order_id: str | None  # Assigned by broker after submission
    rejection_reason: str | None
    idempotency_key: str  # Client-generated unique key

    created_at: datetime
    updated_at: datetime

    def transition_to(self, new_status: OrderStatus, **kwargs: object) -> Self:
        """Create a new Order with updated status.

        ★ Enforces FSM: only valid transitions are allowed.
        ★ Returns a NEW instance — original is untouched.

        Raises:
            InvalidOrderTransitionError: If the transition is not allowed.
        """
        valid_next = _VALID_TRANSITIONS.get(self.status, frozenset())
        if new_status not in valid_next:
            msg = (
                f"Invalid transition: {self.status.value} → {new_status.value}. "
                f"Valid transitions from {self.status.value}: "
                f"{[s.value for s in valid_next]}"
            )
            raise InvalidOrderTransitionError(msg)

        return replace(self, status=new_status, **kwargs)  # type: ignore[arg-type]

    @property
    def is_terminal(self) -> bool:
        """Check if order is in a terminal (final) state."""
        return len(_VALID_TRANSITIONS.get(self.status, frozenset())) == 0

    @property
    def remaining_quantity(self) -> int:
        """Quantity still awaiting fill."""
        return self.quantity - self.filled_quantity

    @property
    def order_value(self) -> Decimal:
        """Total order value = price * quantity."""
        return Decimal(str(self.price)) * Decimal(self.quantity)
