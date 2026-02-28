from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from agents.state import AgentPhase, AgentState


def build_trading_graph(
    screener: Any,
    technical: Any,
    risk: Any,
    executor: Any,
    fundamental: Any | None = None,
) -> StateGraph:  # type: ignore[type-arg]
    """Constructs the Multi-Agent trading pipeline as a LangGraph StateGraph.

    Flow: START -> Screener -> Technical -> Risk -> Executor -> END
    All routing decisions are DETERMINISTIC Python code.
    """
    graph = StateGraph(AgentState)

    # Register Nodes
    graph.add_node("inject_context", _inject_context)
    graph.add_node("screener", screener.run)
    graph.add_node("technical", technical.run)
    graph.add_node("risk", risk.run)
    graph.add_node("executor", executor.run)
    graph.add_node("finalize", _finalize)

    # Define Edges
    graph.set_entry_point("inject_context")
    graph.add_edge("inject_context", "screener")

    # Screener -> conditional
    graph.add_conditional_edges(
        "screener",
        _route_after_screener,
        {"has_candidates": "technical", "no_candidates": "finalize"},
    )

    if fundamental is not None:
        # ★ FIX: Fundamental runs SEQUENTIALLY after technical.
        # LangGraph cannot have both conditional and unconditional edges from same node.
        graph.add_node("fundamental", fundamental.run)
        graph.add_conditional_edges(
            "technical",
            _route_after_technical,
            {"has_signals": "fundamental", "no_signals": "finalize"},
        )
        graph.add_edge("fundamental", "risk")
    else:
        graph.add_conditional_edges(
            "technical",
            _route_after_technical,
            {"has_signals": "risk", "no_signals": "finalize"},
        )

    # Risk -> conditional
    graph.add_conditional_edges(
        "risk",
        _route_after_risk,
        {"has_approved": "executor", "none_approved": "finalize"},
    )

    # Executor -> finalize
    graph.add_edge("executor", "finalize")

    # Finalize -> END
    graph.add_edge("finalize", END)

    return graph


def _inject_context(state: AgentState) -> dict[str, Any]:
    """Initialize pipeline metadata. First node in graph."""
    return {
        "phase": AgentPhase.SCREENING,
        "run_id": str(uuid.uuid4()),
        "triggered_at": datetime.now(UTC),
        "error_message": None,
        "max_candidates": state.get("max_candidates", 10),
        "score_threshold": state.get("score_threshold", 5.0),
        "dry_run": state.get("dry_run", False),
    }


def _finalize(state: AgentState) -> dict[str, Any]:
    """Terminal node — mark pipeline as completed."""
    return {"phase": AgentPhase.COMPLETED}


# Routing Functions (Pure, Deterministic)


def _route_after_screener(
    state: AgentState,
) -> Literal["has_candidates", "no_candidates"]:
    watchlist = state.get("watchlist", [])
    if len(watchlist) > 0:
        return "has_candidates"
    return "no_candidates"


def _route_after_technical(
    state: AgentState,
) -> Literal["has_signals", "no_signals"]:
    top = state.get("top_candidates", [])
    if len(top) > 0:
        return "has_signals"
    return "no_signals"


def _route_after_risk(
    state: AgentState,
) -> Literal["has_approved", "none_approved"]:
    approved = state.get("approved_trades", [])
    if len(approved) > 0:
        return "has_approved"
    return "none_approved"
