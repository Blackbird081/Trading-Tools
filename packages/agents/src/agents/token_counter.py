"""Token Counter — track LLM token usage and costs.

★ Inspired by Dexter's token-counter.ts.
★ Tracks input/output tokens across multiple LLM calls.
★ Calculates tokens/second and estimated cost.
★ Integrated into observability pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger("agents.token_counter")

# Approximate cost per 1M tokens (USD) — update as needed
COST_PER_1M_INPUT: dict[str, float] = {
    "gpt-4o": 2.50,
    "gpt-4o-mini": 0.15,
    "claude-3-5-sonnet": 3.00,
    "claude-3-haiku": 0.25,
    "phi-3-mini": 0.0,  # Local model, no cost
    "default": 1.0,
}

COST_PER_1M_OUTPUT: dict[str, float] = {
    "gpt-4o": 10.00,
    "gpt-4o-mini": 0.60,
    "claude-3-5-sonnet": 15.00,
    "claude-3-haiku": 1.25,
    "phi-3-mini": 0.0,
    "default": 4.0,
}


@dataclass
class TokenUsage:
    """Token usage for a single LLM call.

    ★ total_tokens is auto-calculated as input + output if not provided.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    _total_tokens: int = field(default=0, repr=False)
    model: str = "unknown"
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        """Auto-calculate total_tokens if not explicitly set."""
        if self._total_tokens == 0 and (self.input_tokens > 0 or self.output_tokens > 0):
            self._total_tokens = self.input_tokens + self.output_tokens

    @property
    def total_tokens(self) -> int:
        """Total tokens = input + output."""
        return self._total_tokens if self._total_tokens > 0 else self.input_tokens + self.output_tokens

    @property
    def estimated_cost_usd(self) -> float:
        """Estimate cost in USD based on model pricing."""
        input_cost_per_1m = COST_PER_1M_INPUT.get(self.model, COST_PER_1M_INPUT["default"])
        output_cost_per_1m = COST_PER_1M_OUTPUT.get(self.model, COST_PER_1M_OUTPUT["default"])
        return (
            self.input_tokens * input_cost_per_1m / 1_000_000
            + self.output_tokens * output_cost_per_1m / 1_000_000
        )


class TokenCounter:
    """Tracks token usage across multiple LLM calls.

    ★ Inspired by Dexter's TokenCounter class.
    ★ Accumulates usage across all calls in a pipeline run.
    ★ Calculates tokens/second and total estimated cost.
    """

    def __init__(self) -> None:
        self._calls: list[TokenUsage] = []
        self._start_time: datetime = datetime.now(UTC)

    def add(self, usage: TokenUsage | None) -> None:
        """Add usage from an LLM call to the running total."""
        if usage is None:
            return
        self._calls.append(usage)

    def add_raw(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "unknown",
    ) -> None:
        """Add raw token counts."""
        self.add(TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            model=model,
        ))

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self._calls)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self._calls)

    @property
    def total_tokens(self) -> int:
        return sum(c.total_tokens for c in self._calls)  # Uses auto-calculated property

    @property
    def total_cost_usd(self) -> float:
        return sum(c.estimated_cost_usd for c in self._calls)

    @property
    def call_count(self) -> int:
        return len(self._calls)

    def get_tokens_per_second(self, elapsed_ms: float | None = None) -> float | None:
        """Calculate tokens per second given elapsed time."""
        if self.total_tokens == 0:
            return None
        if elapsed_ms is None:
            elapsed_ms = (datetime.now(UTC) - self._start_time).total_seconds() * 1000
        if elapsed_ms <= 0:
            return None
        return self.total_tokens / (elapsed_ms / 1000)

    def get_summary(self) -> dict[str, object]:
        """Get usage summary for logging/reporting."""
        elapsed_ms = (datetime.now(UTC) - self._start_time).total_seconds() * 1000
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "call_count": self.call_count,
            "tokens_per_second": self.get_tokens_per_second(elapsed_ms),
            "elapsed_seconds": round(elapsed_ms / 1000, 2),
        }

    def log_summary(self) -> None:
        """Log usage summary."""
        summary = self.get_summary()
        logger.info(
            "Token usage: %d total (%d in, %d out), $%.4f USD, %d calls, %.1f tok/s",
            summary["total_tokens"],
            summary["total_input_tokens"],
            summary["total_output_tokens"],
            summary["total_cost_usd"],
            summary["call_count"],
            summary.get("tokens_per_second") or 0,
        )
