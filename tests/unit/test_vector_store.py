from __future__ import annotations

import pytest
from adapters.duckdb.vector_store import DuckDBVectorStore


class TestDuckDBVectorStore:
    @pytest.mark.asyncio
    async def test_initialize_and_count(self) -> None:
        store = DuckDBVectorStore(db_path=":memory:")
        await store.initialize()
        count = await store.count()
        assert count == 0
        store.close()

    @pytest.mark.asyncio
    async def test_insert_and_search(self) -> None:
        store = DuckDBVectorStore(db_path=":memory:")
        await store.initialize()

        # Insert some embeddings
        embedding1 = [1.0] * 384
        embedding2 = [0.5] * 384

        row_id = await store.insert(
            symbol="FPT",
            headline="FPT tang truong manh Q4",
            embedding=embedding1,
        )
        assert row_id is not None

        await store.insert(
            symbol="VNM",
            headline="VNM giam loi nhuan",
            embedding=embedding2,
        )

        count = await store.count()
        assert count == 2

        # Search
        results = await store.search(
            query_embedding=embedding1,
            top_k=5,
        )
        assert len(results) >= 1
        assert results[0]["symbol"] in ("FPT", "VNM")

        store.close()

    @pytest.mark.asyncio
    async def test_search_with_symbol_filter(self) -> None:
        store = DuckDBVectorStore(db_path=":memory:")
        await store.initialize()

        await store.insert(
            symbol="FPT",
            headline="FPT news",
            embedding=[1.0] * 384,
        )
        await store.insert(
            symbol="VNM",
            headline="VNM news",
            embedding=[0.5] * 384,
        )

        results = await store.search(
            query_embedding=[1.0] * 384,
            symbol="FPT",
            top_k=5,
        )
        assert all(r["symbol"] == "FPT" for r in results)

        store.close()

    @pytest.mark.asyncio
    async def test_empty_search(self) -> None:
        store = DuckDBVectorStore(db_path=":memory:")
        await store.initialize()

        results = await store.search(
            query_embedding=[0.0] * 384,
            top_k=5,
        )
        assert results == []

        store.close()
