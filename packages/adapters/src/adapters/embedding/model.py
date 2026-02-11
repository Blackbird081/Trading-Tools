from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("adapters.embedding")


class EmbeddingModel:
    """Sentence embedding model for vector search.

    Uses sentence-transformers for generating text embeddings.
    Gracefully degrades when library not installed.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        self._model_name = model_name
        self._model: Any = None
        self._available = False

    def initialize(self) -> None:
        """Load the embedding model."""
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            self._available = True
            logger.info("Embedding model loaded: %s", self._model_name)
        except ImportError:
            logger.warning("sentence-transformers not installed — embedding unavailable")
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def encode(self, text: str) -> list[float]:
        """Encode text to embedding vector."""
        if not self._available or self._model is None:
            # Return zero vector as fallback
            return [0.0] * 384

        embedding: Any = self._model.encode(text)
        result: list[float] = embedding.tolist()
        return result

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """Encode batch of texts."""
        if not self._available or self._model is None:
            return [[0.0] * 384 for _ in texts]

        embeddings: Any = self._model.encode(texts)
        return [e.tolist() for e in embeddings]

    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        return 384
