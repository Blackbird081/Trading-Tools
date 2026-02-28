"""Agent Pipeline Runner — execute trading pipeline with streaming and context management.

★ Inspired by Dexter's agent loop with Anthropic-style context management.
★ Integrates: Scratchpad, TokenCounter, Streaming, Context Clearing.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, AsyncIterator

from agents.scratchpad import AgentScratchpad
from agents.token_counter import TokenCounter

logger = logging.getLogger("agents.runner")

# Context management constants (Dexter-inspired)
CONTEXT_THRESHOLD_TOKENS = 100_000  # Clear context when estimated tokens exceed this
KEEP_TOOL_RESULTS = 5               # Keep N most recent tool results after clearing
MAX_ITERATIONS = 10                 # Max pipeline iterations before giving up


async def run_trading_pipeline(
    graph: Any,
    nav: Decimal,
    positions: dict[str, int],
    purchasing_power: Decimal,
    dry_run: bool = True,
    query: str = "Trading pipeline run",
) -> dict[str, Any]:
    """Execute the full Multi-Agent pipeline with scratchpad tracking.

    ★ Creates a scratchpad for this run (JSONL audit trail).
    ★ Tracks token usage across all LLM calls.
    ★ Returns final state with metadata.
    """
    app = graph.compile()
    scratchpad = AgentScratchpad(query=query)
    token_counter = TokenCounter()

    scratchpad.add_thinking(
        f"Starting trading pipeline: NAV={nav}, dry_run={dry_run}, "
        f"positions={len(positions)}"
    )

    initial_state: dict[str, Any] = {
        "current_nav": nav,
        "current_positions": positions,
        "purchasing_power": purchasing_power,
        "dry_run": dry_run,
        "max_candidates": 10,
        "score_threshold": 5.0,
    }

    try:
        final_state: dict[str, Any] = await app.ainvoke(initial_state)
        phase = final_state.get("phase", "unknown")
        scratchpad.add_thinking(f"Pipeline completed. Phase: {phase}")
        logger.info("Pipeline completed. Phase: %s", phase)

        # Log token usage
        token_counter.log_summary()

        return {
            **final_state,
            "_scratchpad_path": str(scratchpad.filepath),
            "_token_usage": token_counter.get_summary(),
        }
    except Exception as exc:
        scratchpad.add_thinking(f"Pipeline error: {exc}")
        logger.exception("Pipeline failed")
        raise


async def run_with_streaming(
    graph: Any,
    initial_state: dict[str, Any],
    ws_manager: Any = None,
    query: str = "Streaming pipeline run",
) -> AsyncIterator[dict[str, Any]]:
    """Execute with real-time streaming for WebSocket updates.

    ★ Yields events for each agent node update.
    ★ Broadcasts to WebSocket clients if ws_manager provided.
    ★ Tracks scratchpad for debugging.
    """
    app = graph.compile()
    scratchpad = AgentScratchpad(query=query)

    node_messages = {
        "inject_context": "Khởi tạo context pipeline...",
        "screener": "Đang sàng lọc cổ phiếu...",
        "technical": "Đang phân tích kỹ thuật...",
        "fundamental": "Đang phân tích cơ bản với AI...",
        "risk": "Đang kiểm tra rủi ro...",
        "executor": "Đang thực thi lệnh...",
        "finalize": "Hoàn thiện kết quả...",
    }

    async for event in app.astream(initial_state, stream_mode="updates"):
        node_name = next(iter(event.keys()), "unknown")
        update = event.get(node_name, {})

        message = node_messages.get(node_name, f"Đang xử lý: {node_name}")
        scratchpad.add_thinking(f"Node: {node_name} — {message}")

        # Build stream chunk
        chunk = {
            "type": "agent_stream",
            "payload": {
                "node": node_name,
                "message": message,
                "metadata": _extract_metadata(node_name, update),
            },
        }

        # Broadcast to WebSocket
        if ws_manager is not None:
            try:
                await ws_manager.broadcast_json(chunk)
            except Exception:
                logger.debug("Failed to broadcast agent update")

        yield chunk

    # Final completion event
    completion = {
        "type": "agent_stream",
        "payload": {
            "node": "complete",
            "message": "Pipeline hoàn thành",
            "metadata": {"scratchpad_path": str(scratchpad.filepath)},
        },
    }
    if ws_manager is not None:
        try:
            await ws_manager.broadcast_json(completion)
        except Exception:
            pass
    yield completion


def _extract_metadata(node_name: str, update: dict[str, Any]) -> dict[str, Any]:
    """Extract relevant metadata from node update for streaming."""
    metadata: dict[str, Any] = {"node": node_name}

    if "watchlist" in update:
        metadata["candidates"] = len(update["watchlist"])
    if "technical_scores" in update:
        metadata["analyzed"] = len(update.get("technical_scores", []))
        metadata["top_candidates"] = len(update.get("top_candidates", []))
    if "risk_assessments" in update:
        metadata["approved"] = len(update.get("approved_trades", []))
        metadata["total"] = len(update.get("risk_assessments", []))
    if "execution_plans" in update:
        metadata["executed"] = len(update.get("execution_plans", []))
    if "ai_insights" in update:
        metadata["insights"] = len(update.get("ai_insights", {}))

    return metadata
