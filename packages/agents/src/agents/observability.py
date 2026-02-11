from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("agents.pipeline")


def log_agent_step(
    run_id: str,
    agent_name: str,
    phase: str,
    input_summary: dict[str, Any],
    output_summary: dict[str, Any],
    duration_ms: float,
    prompt_version: str | None = None,
) -> None:
    """Structured log entry for every agent step.

    Every AI decision is traceable:
    - Which prompt version was used?
    - What data did the agent see?
    - What did it output?
    - How long did it take?
    """
    entry: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "agent": agent_name,
        "phase": phase,
        "duration_ms": round(duration_ms, 1),
        "input": input_summary,
        "output": output_summary,
    }

    if prompt_version:
        entry["prompt_version"] = prompt_version

    logger.info(json.dumps(entry, ensure_ascii=False))
