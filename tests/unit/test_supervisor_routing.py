from __future__ import annotations

from datetime import UTC, datetime

from agents.state import (
    AgentPhase,
    AgentState,
    ScreenerResult,
)
from agents.supervisor import (
    _inject_context,
    _route_after_risk,
    _route_after_screener,
    _route_after_technical,
)
from core.value_objects import Symbol


class TestRouting:
    def test_route_after_screener_has_candidates(self) -> None:
        now = datetime.now(UTC)
        state: AgentState = {
            "watchlist": [
                ScreenerResult(
                    symbol=Symbol("FPT"),
                    eps_growth=0.15,
                    pe_ratio=12.0,
                    volume_spike=True,
                    passed_at=now,
                )
            ]
        }
        assert _route_after_screener(state) == "has_candidates"

    def test_route_after_screener_no_candidates(self) -> None:
        state: AgentState = {"watchlist": []}
        assert _route_after_screener(state) == "no_candidates"

    def test_route_after_screener_missing_key(self) -> None:
        state: AgentState = {}
        assert _route_after_screener(state) == "no_candidates"

    def test_route_after_technical_has_signals(self) -> None:
        state: AgentState = {"top_candidates": [Symbol("FPT")]}
        assert _route_after_technical(state) == "has_signals"

    def test_route_after_technical_no_signals(self) -> None:
        state: AgentState = {"top_candidates": []}
        assert _route_after_technical(state) == "no_signals"

    def test_route_after_risk_has_approved(self) -> None:
        state: AgentState = {"approved_trades": [Symbol("FPT")]}
        assert _route_after_risk(state) == "has_approved"

    def test_route_after_risk_none_approved(self) -> None:
        state: AgentState = {"approved_trades": []}
        assert _route_after_risk(state) == "none_approved"


class TestInjectContext:
    def test_inject_context_sets_defaults(self) -> None:
        state: AgentState = {}
        result = _inject_context(state)
        assert result["phase"] == AgentPhase.SCREENING
        assert "run_id" in result
        assert result["max_candidates"] == 10
        assert result["score_threshold"] == 5.0
        assert result["dry_run"] is False

    def test_inject_context_preserves_overrides(self) -> None:
        state: AgentState = {
            "max_candidates": 3,
            "score_threshold": 7.0,
            "dry_run": True,
        }
        result = _inject_context(state)
        assert result["max_candidates"] == 3
        assert result["score_threshold"] == 7.0
        assert result["dry_run"] is True
