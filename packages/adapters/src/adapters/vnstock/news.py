from __future__ import annotations

import logging

logger = logging.getLogger("vnstock.news")


class VnstockNewsAdapter:
    """Vnstock news feed wrapper for Fundamental Agent."""

    async def get_news(
        self,
        symbol: str,
        limit: int = 20,
    ) -> list[dict[str, object]]:
        """Fetch news for a symbol. Stub for Phase 3."""
        logger.info("Fetching news for %s (stub)", symbol)
        return []
