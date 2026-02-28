"""IdempotencyPort — abstract interface for idempotency key storage.

★ Allows swapping between in-memory (testing) and DuckDB (production) implementations.
★ Follows Dependency Inversion Principle: core depends on abstraction, not concrete adapter.

Ref: ROADMAP.md Sprint 2.3
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class IdempotencyPort(ABC):
    """Abstract interface for idempotency key storage.

    Implementations:
    - core.use_cases.place_order.IdempotencyStore (in-memory, for testing)
    - adapters.duckdb.idempotency_store.DuckDBIdempotencyStore (persistent, for production)
    """

    @abstractmethod
    async def check(self, key: str) -> dict[str, object] | None:
        """Check if a key exists and is not expired.

        Returns:
            The stored result dict if key exists and is valid, None otherwise.
        """

    @abstractmethod
    async def record(self, key: str, result: dict[str, object]) -> None:
        """Record a result for a key.

        Args:
            key: Idempotency key (client-generated unique identifier).
            result: Result to store (must be JSON-serializable).
        """

    @abstractmethod
    async def prune_expired(self) -> int:
        """Remove expired keys.

        Returns:
            Number of keys pruned.
        """
