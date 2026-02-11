from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger("agents.runner")


async def run_trading_pipeline(
    graph: Any,
    nav: Decimal,
    positions: dict[str, int],
    purchasing_power: Decimal,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Execute the full Multi-Agent pipeline. Returns final state."""
    app = graph.compile()

    initial_state: dict[str, Any] = {
        "current_nav": nav,
        "current_positions": positions,
        "purchasing_power": purchasing_power,
        "dry_run": dry_run,
        "max_candidates": 10,
        "score_threshold": 5.0,
    }

    final_state: dict[str, Any] = await app.ainvoke(initial_state)
    logger.info("Pipeline completed. Phase: %s", final_state.get("phase"))
    return final_state


async def run_with_streaming(
    graph: Any,
    initial_state: dict[str, Any],
) -> None:
    """Execute with real-time streaming for WebSocket updates."""
    app = graph.compile()
    async for event in app.astream(initial_state, stream_mode="updates"):
        node_name = next(iter(event.keys()))
        update = event[node_name]
        await _broadcast_agent_update(node_name, update)


async def _broadcast_agent_update(node: str, update: dict[str, Any]) -> None:
    """Stub: push to WebSocket ConnectionManager."""
    logger.debug("Agent update from %s: %s", node, list(update.keys()))
