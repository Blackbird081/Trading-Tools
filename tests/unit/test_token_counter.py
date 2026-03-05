from __future__ import annotations

import pytest

from agents.token_counter import TokenCounter, TokenUsage


def test_token_usage_uses_new_default_model_prices() -> None:
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000, model="gpt-5-mini")
    assert usage.estimated_cost_usd == pytest.approx(2.25)


def test_token_usage_handles_versioned_alias_models() -> None:
    usage = TokenUsage(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        model="claude-sonnet-4-20250514",
    )
    assert usage.estimated_cost_usd == pytest.approx(18.0)


def test_token_usage_handles_provider_prefixed_model_names() -> None:
    usage = TokenUsage(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        model="models/qwen3-max-2025-09-23",
    )
    assert usage.estimated_cost_usd == pytest.approx(5.85)


def test_token_usage_unknown_model_falls_back_to_default_bucket() -> None:
    usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000, model="unknown-future-model")
    assert usage.estimated_cost_usd == pytest.approx(5.0)


def test_token_counter_aggregates_cost_with_new_models() -> None:
    counter = TokenCounter()
    counter.add_raw(500_000, 200_000, model="gpt-5-mini")
    counter.add_raw(300_000, 100_000, model="gemini-2.5-flash")

    expected = ((500_000 * 0.25 + 200_000 * 2.0) / 1_000_000) + ((300_000 * 0.30 + 100_000 * 2.5) / 1_000_000)
    assert counter.total_cost_usd == pytest.approx(expected)
