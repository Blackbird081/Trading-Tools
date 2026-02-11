from __future__ import annotations

import logging

logger = logging.getLogger("vnstock.screener")


class VnstockScreenerAdapter:
    """Vnstock stock screening wrapper."""

    async def get_screener_data(
        self,
        exchange: str = "HOSE",
    ) -> list[dict[str, object]]:
        """Fetch stock screening data from vnstock."""
        try:
            import vnstock

            stock = vnstock.Vnstock().stock(symbol="VCI", source="VCI")
            df = stock.listing.symbols_by_exchange(exchange=exchange)
            return df.to_dict("records")  # type: ignore[no-any-return]
        except ImportError:
            logger.warning("vnstock not installed. Returning empty screening data.")
            return []
        except Exception:
            logger.exception("Failed to fetch screening data")
            return []
