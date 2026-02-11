from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("adapters.vector_store")


class DuckDBVectorStore:
    """DuckDB-backed vector store using vss extension.

    Stores news embeddings for RAG retrieval by FundamentalAgent.
    Uses DuckDB vss (Vector Similarity Search) for approximate nearest neighbor.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._conn: Any = None

    async def initialize(self) -> None:
        """Create tables and load vss extension."""
        try:
            import duckdb

            self._conn = duckdb.connect(self._db_path)
            # Try to install and load vss extension
            try:
                self._conn.execute("INSTALL vss")
                self._conn.execute("LOAD vss")
            except Exception:
                logger.warning("DuckDB vss extension not available — using exact search")

            self._conn.execute("""
                CREATE SEQUENCE IF NOT EXISTS seq_news_id START 1;
                CREATE TABLE IF NOT EXISTS news_embeddings (
                    id INTEGER PRIMARY KEY DEFAULT nextval('seq_news_id'),
                    symbol VARCHAR NOT NULL,
                    headline VARCHAR NOT NULL,
                    content VARCHAR,
                    embedding FLOAT[384],
                    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source VARCHAR DEFAULT 'unknown'
                )
            """)
            logger.info("Vector store initialized at %s", self._db_path)
        except ImportError:
            logger.warning("DuckDB not available — vector store disabled")

    async def insert(
        self,
        symbol: str,
        headline: str,
        embedding: list[float],
        content: str = "",
        source: str = "vnstock",
    ) -> int | None:
        """Insert a news embedding. Returns row ID."""
        if self._conn is None:
            return None

        self._conn.execute(
            """
            INSERT INTO news_embeddings (symbol, headline, content, embedding, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            [symbol, headline, content, embedding, source],
        )
        result = self._conn.execute("SELECT MAX(id) FROM news_embeddings").fetchone()
        return int(result[0]) if result and result[0] is not None else None

    async def search(
        self,
        query_embedding: list[float],
        symbol: str | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for similar news embeddings.

        Falls back to exact cosine similarity if vss is not available.
        """
        if self._conn is None:
            return []

        # Use exact cosine similarity (works without vss extension)
        where_clause = f"WHERE symbol = '{symbol}'" if symbol else ""

        query = f"""
            SELECT
                id, symbol, headline, content, source,
                list_cosine_similarity(embedding, ?::FLOAT[384]) AS score
            FROM news_embeddings
            {where_clause}
            ORDER BY score DESC
            LIMIT ?
        """
        try:
            rows = self._conn.execute(query, [query_embedding, top_k]).fetchall()
            return [
                {
                    "id": row[0],
                    "symbol": row[1],
                    "headline": row[2],
                    "content": row[3],
                    "source": row[4],
                    "score": row[5],
                }
                for row in rows
            ]
        except Exception:
            logger.exception("Vector search failed")
            return []

    async def count(self) -> int:
        """Count total embeddings."""
        if self._conn is None:
            return 0
        result = self._conn.execute("SELECT COUNT(*) FROM news_embeddings").fetchone()
        return int(result[0]) if result else 0

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
