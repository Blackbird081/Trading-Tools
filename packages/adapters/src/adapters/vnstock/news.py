from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("vnstock.news")


class VnstockNewsAdapter:
    """Vnstock news feed wrapper for Fundamental Agent."""

    def _normalize_news(self, raw: Any, limit: int) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []

        if raw is None:
            return records
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    records.append(item)
        elif isinstance(raw, dict):
            nested = raw.get("data")
            if isinstance(nested, list):
                for item in nested:
                    if isinstance(item, dict):
                        records.append(item)
            else:
                records.append(raw)
        elif hasattr(raw, "to_dict"):
            try:
                as_records = raw.to_dict("records")
            except Exception:  # pragma: no cover - library dependent
                as_records = []
            if isinstance(as_records, list):
                for item in as_records:
                    if isinstance(item, dict):
                        records.append(item)

        normalized: list[dict[str, object]] = []
        for row in records:
            title = str(
                row.get("title")
                or row.get("headline")
                or row.get("news_title")
                or row.get("tieu_de")
                or ""
            ).strip()
            if not title:
                continue
            normalized.append(
                {
                    "title": title,
                    "source": str(row.get("source") or row.get("publisher") or "vnstock"),
                    "date": str(row.get("date") or row.get("time") or row.get("published_at") or ""),
                }
            )

        return normalized[: max(1, limit)]

    def get_headlines(self, symbol: str, limit: int = 5) -> list[dict[str, object]]:
        """Fetch headlines for symbol from vnstock (best-effort, graceful fallback)."""
        try:
            import vnstock  # type: ignore[import-untyped]

            stock = vnstock.Vnstock().stock(symbol=symbol, source="VCI")
            candidates: list[tuple[str, Any]] = []

            news_attr = getattr(stock, "news", None)
            if callable(news_attr):
                candidates.append(("stock.news()", lambda: news_attr()))
            if news_attr is not None and hasattr(news_attr, "headlines"):
                candidates.append(("stock.news.headlines()", lambda: news_attr.headlines()))
            if news_attr is not None and hasattr(news_attr, "latest"):
                candidates.append(("stock.news.latest()", lambda: news_attr.latest()))

            company_attr = getattr(stock, "company", None)
            if company_attr is not None and hasattr(company_attr, "news"):
                candidates.append(("stock.company.news()", lambda: company_attr.news()))

            for label, fn in candidates:
                try:
                    raw = fn()
                    normalized = self._normalize_news(raw, limit)
                    if normalized:
                        logger.info("Fetched %d headlines for %s via %s", len(normalized), symbol, label)
                        return normalized
                except Exception:  # pragma: no cover - external library/api behavior
                    continue
        except ImportError:
            logger.info("vnstock package unavailable - skip external headlines for %s", symbol)
        except Exception:  # pragma: no cover - runtime/network dependent
            logger.exception("Failed to fetch vnstock headlines for %s", symbol)
        return []

    async def get_news(
        self,
        symbol: str,
        limit: int = 20,
    ) -> list[dict[str, object]]:
        """Fetch news for a symbol."""
        return self.get_headlines(symbol=symbol, limit=limit)
