from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from core.entities.tick import OHLCV, Exchange
from core.value_objects import Price, Quantity, Symbol

logger = logging.getLogger("vnstock.history")


class VnstockHistoryAdapter:
    """Vnstock wrapper for historical OHLCV data.

    Wraps vnstock library for consistent interface.
    Falls back to empty data if vnstock is unavailable.
    """

    async def get_ohlcv(
        self,
        symbol: Symbol,
        start: date,
        end: date,
        resolution: str = "1D",
    ) -> list[OHLCV]:
        """Fetch historical OHLCV from vnstock."""
        try:
            from datetime import datetime

            import vnstock

            stock = vnstock.Vnstock().stock(symbol=str(symbol), source="VCI")
            df = stock.quote.history(
                start=start.isoformat(),
                end=end.isoformat(),
            )
            results: list[OHLCV] = []
            for _, row in df.iterrows():
                results.append(
                    OHLCV(
                        symbol=symbol,
                        exchange=Exchange.HOSE,
                        open=Price(Decimal(str(row.get("open", 0)))),
                        high=Price(Decimal(str(row.get("high", 0)))),
                        low=Price(Decimal(str(row.get("low", 0)))),
                        close=Price(Decimal(str(row.get("close", 0)))),
                        volume=Quantity(int(row.get("volume", 0))),
                        timestamp=datetime.combine(row.get("time", start), datetime.min.time()),
                    )
                )
            return results
        except ImportError:
            logger.warning("vnstock not installed. Returning empty OHLCV data.")
            return []
        except Exception:
            logger.exception("Failed to fetch OHLCV for %s", symbol)
            return []
