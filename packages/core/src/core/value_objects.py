"""Value objects — domain primitives with type safety via NewType.

★ Decimal for Price — NEVER use float for financial data (IEEE 754 rounding errors).
★ NewType enforces type safety at mypy level: can't pass Symbol where Price is expected.

Ref: Doc 02 §2.2
"""

from __future__ import annotations

from decimal import Decimal
from typing import NewType

Symbol = NewType("Symbol", str)  # "FPT", "VNM", "VIC", ...
Price = NewType("Price", Decimal)  # Decimal for financial precision
Quantity = NewType("Quantity", int)  # Always integer (lot size = 100)
