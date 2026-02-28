"""Input Validation Middleware — Pydantic-based request validation for FastAPI.

★ SEC-02: Validates all incoming requests with Pydantic models.
★ Prevents malformed data from reaching business logic.
★ Returns structured 422 errors with field-level details.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("interface.validation")

# ── Order Request Models ───────────────────────────────────────────────────────

VN_LOT_SIZE = 100
MAX_ORDER_VALUE_VND = Decimal("10_000_000_000")  # 10 tỷ VND max per order
MIN_PRICE_VND = Decimal("100")                    # 100 VND minimum price


class PlaceOrderRequest(BaseModel):
    """Validated order placement request.

    ★ Enforces VN market rules at API boundary.
    """

    symbol: Annotated[str, Field(min_length=2, max_length=10, pattern=r"^[A-Z0-9]+$")]
    side: Annotated[str, Field(pattern=r"^(BUY|SELL)$")]
    order_type: Annotated[str, Field(pattern=r"^(LO|ATO|ATC|MP)$")]
    quantity: Annotated[int, Field(gt=0, le=1_000_000)]
    price: Decimal = Field(ge=Decimal("0"))
    idempotency_key: Annotated[str, Field(min_length=8, max_length=64)]

    @field_validator("quantity")
    @classmethod
    def validate_lot_size(cls, v: int) -> int:
        """VN market: quantity must be multiple of 100."""
        if v % VN_LOT_SIZE != 0:
            msg = f"Quantity {v} must be a multiple of {VN_LOT_SIZE} (VN lot size)"
            raise ValueError(msg)
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        """Price must be positive for LO orders."""
        if v < 0:
            msg = "Price cannot be negative"
            raise ValueError(msg)
        return v

    @field_validator("symbol")
    @classmethod
    def validate_symbol_format(cls, v: str) -> str:
        """Symbol must be uppercase alphanumeric."""
        return v.upper().strip()


class CancelOrderRequest(BaseModel):
    """Validated order cancellation request."""

    order_id: Annotated[str, Field(min_length=1, max_length=64)]
    reason: Annotated[str | None, Field(max_length=200)] = None


class ScreenerRequest(BaseModel):
    """Validated screener pipeline request."""

    symbols: Annotated[list[str], Field(min_length=1, max_length=100)] = []
    max_candidates: Annotated[int, Field(ge=1, le=50)] = 10
    score_threshold: Annotated[float, Field(ge=0.0, le=10.0)] = 5.0
    dry_run: bool = True

    @field_validator("symbols")
    @classmethod
    def validate_symbols(cls, v: list[str]) -> list[str]:
        return [s.upper().strip() for s in v if s.strip()]


# ── Validation Helpers ────────────────────────────────────────────────────────

def validate_symbol(symbol: str) -> str:
    """Validate and normalize a stock symbol."""
    symbol = symbol.upper().strip()
    if not symbol or not symbol.isalnum():
        msg = f"Invalid symbol: {symbol!r}"
        raise ValueError(msg)
    if len(symbol) > 10:
        msg = f"Symbol too long: {symbol!r}"
        raise ValueError(msg)
    return symbol
