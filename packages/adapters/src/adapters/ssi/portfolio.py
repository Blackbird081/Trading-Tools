from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from core.entities.portfolio import CashBalance, PortfolioState

logger = logging.getLogger("ssi.portfolio")


class SSIPortfolioClient:
    """SSI portfolio sync — stockPosition + cash balance."""

    def __init__(self, auth_client: object) -> None:
        self._auth = auth_client

    async def get_portfolio(self) -> PortfolioState:
        """Fetch current portfolio state from SSI API.

        Stub — returns empty portfolio for now.
        Full implementation in Phase 5.
        """
        logger.info("Fetching portfolio from SSI (stub)")
        return PortfolioState(
            positions=(),
            cash=CashBalance(
                cash_bal=Decimal("0"),
                purchasing_power=Decimal("0"),
                pending_settlement=Decimal("0"),
            ),
            synced_at=datetime.now(),
        )
