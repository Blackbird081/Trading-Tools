"""AIEnginePort — outbound port for AI/LLM inference.

★ Abstracts OpenVINO NPU inference behind a Protocol.
★ Allows swapping between NPU, CPU, or cloud LLM backends.

Ref: Doc 04 §2
"""

from __future__ import annotations

from typing import Protocol

from core.entities.signal import AIInsight
from core.value_objects import Symbol


class AIEnginePort(Protocol):
    """Outbound port: run AI/LLM inference for fundamental analysis."""

    async def analyze(
        self,
        symbol: Symbol,
        context: str,
        max_tokens: int = 512,
    ) -> AIInsight:
        """Run LLM analysis on a symbol with given context.

        Args:
            symbol: Stock symbol to analyze.
            context: Formatted prompt/context for the LLM.
            max_tokens: Maximum tokens in response.

        Returns:
            Structured AIInsight with sentiment, summary, key factors.
        """
        ...

    async def is_available(self) -> bool:
        """Check if the AI engine (NPU/CPU) is available and ready."""
        ...
