"""Observability — structured logging, metrics, health checks for agent pipeline.

★ Upgraded: PipelineMetrics with latency percentiles (p50/p95/p99).
★ Upgraded: Structured error tracking with error_type, stack_trace, context.
★ New: agent_health_check() — per-agent status monitoring.
★ New: pipeline_dashboard() — summary metrics for ops monitoring.
"""
from __future__ import annotations

import json
import logging
import math
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("agents.pipeline")


# ── Structured Logging ────────────────────────────────────────────────────────

def log_agent_step(
    run_id: str,
    agent_name: str,
    phase: str,
    input_summary: dict[str, Any],
    output_summary: dict[str, Any],
    duration_ms: float,
    prompt_version: str | None = None,
    error: str | None = None,  # ★ NEW: optional error field
) -> None:
    """Structured log entry for every agent step.

    Every AI decision is traceable:
    - Which prompt version was used?
    - What data did the agent see?
    - What did it output?
    - How long did it take?
    - Did it error?
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

    if error:
        entry["error"] = error
        logger.error(json.dumps(entry, ensure_ascii=False))
    else:
        logger.info(json.dumps(entry, ensure_ascii=False))


def log_pipeline_error(
    run_id: str,
    agent_name: str,
    exc: Exception,
    context: dict[str, Any] | None = None,
) -> None:
    """★ NEW: Structured error log with full traceback and context.

    Captures:
    - error_type: exception class name
    - error_message: str(exc)
    - stack_trace: full traceback
    - context: additional debugging info
    """
    entry: dict[str, Any] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "run_id": run_id,
        "agent": agent_name,
        "event": "pipeline_error",
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "stack_trace": traceback.format_exc(),
    }
    if context:
        entry["context"] = context

    logger.error(json.dumps(entry, ensure_ascii=False))


# ── Pipeline Metrics ──────────────────────────────────────────────────────────

@dataclass
class AgentMetrics:
    """Per-agent performance metrics."""

    agent_name: str
    call_count: int = 0
    error_count: int = 0
    total_duration_ms: float = 0.0
    durations_ms: list[float] = field(default_factory=list)

    def record(self, duration_ms: float, error: bool = False) -> None:
        self.call_count += 1
        self.total_duration_ms += duration_ms
        self.durations_ms.append(duration_ms)
        if error:
            self.error_count += 1

    @property
    def avg_duration_ms(self) -> float | None:
        if not self.durations_ms:
            return None
        return self.total_duration_ms / len(self.durations_ms)

    @property
    def error_rate(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.error_count / self.call_count

    def percentile(self, p: float) -> float | None:
        """Calculate latency percentile (0-100)."""
        if not self.durations_ms:
            return None
        sorted_d = sorted(self.durations_ms)
        idx = math.ceil(p / 100 * len(sorted_d)) - 1
        return sorted_d[max(0, min(idx, len(sorted_d) - 1))]

    @property
    def p50(self) -> float | None:
        return self.percentile(50)

    @property
    def p95(self) -> float | None:
        return self.percentile(95)

    @property
    def p99(self) -> float | None:
        return self.percentile(99)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent_name,
            "call_count": self.call_count,
            "error_count": self.error_count,
            "error_rate_pct": f"{self.error_rate * 100:.1f}%",
            "avg_ms": round(self.avg_duration_ms or 0, 1),
            "p50_ms": round(self.p50 or 0, 1),
            "p95_ms": round(self.p95 or 0, 1),
            "p99_ms": round(self.p99 or 0, 1),
        }


@dataclass
class PipelineMetrics:
    """★ NEW: Aggregated pipeline metrics with latency percentiles.

    Tracks per-agent and overall pipeline performance.
    Thread-safe for single-process use (no locks needed for asyncio).
    """

    _agents: dict[str, AgentMetrics] = field(default_factory=dict)
    _pipeline_runs: int = 0
    _pipeline_errors: int = 0
    _pipeline_durations_ms: list[float] = field(default_factory=list)
    _started_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def record_agent(
        self,
        agent_name: str,
        duration_ms: float,
        error: bool = False,
    ) -> None:
        """Record a single agent execution."""
        if agent_name not in self._agents:
            self._agents[agent_name] = AgentMetrics(agent_name=agent_name)
        self._agents[agent_name].record(duration_ms, error=error)

    def record_pipeline_run(self, duration_ms: float, error: bool = False) -> None:
        """Record a complete pipeline run."""
        self._pipeline_runs += 1
        self._pipeline_durations_ms.append(duration_ms)
        if error:
            self._pipeline_errors += 1

    def get_agent_metrics(self, agent_name: str) -> AgentMetrics | None:
        return self._agents.get(agent_name)

    @property
    def pipeline_p50_ms(self) -> float | None:
        if not self._pipeline_durations_ms:
            return None
        sorted_d = sorted(self._pipeline_durations_ms)
        idx = len(sorted_d) // 2
        return sorted_d[idx]

    @property
    def pipeline_p95_ms(self) -> float | None:
        if not self._pipeline_durations_ms:
            return None
        sorted_d = sorted(self._pipeline_durations_ms)
        idx = math.ceil(0.95 * len(sorted_d)) - 1
        return sorted_d[max(0, idx)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_runs": self._pipeline_runs,
            "pipeline_errors": self._pipeline_errors,
            "pipeline_error_rate_pct": f"{(self._pipeline_errors / max(self._pipeline_runs, 1)) * 100:.1f}%",
            "pipeline_p50_ms": round(self.pipeline_p50_ms or 0, 1),
            "pipeline_p95_ms": round(self.pipeline_p95_ms or 0, 1),
            "agents": [m.to_dict() for m in self._agents.values()],
            "uptime_seconds": round((datetime.now(UTC) - self._started_at).total_seconds(), 1),
        }


# ── Global Metrics Instance ───────────────────────────────────────────────────

_global_metrics = PipelineMetrics()


def get_pipeline_metrics() -> PipelineMetrics:
    """Get the global PipelineMetrics singleton."""
    return _global_metrics


def reset_pipeline_metrics() -> None:
    """Reset metrics (useful for testing)."""
    global _global_metrics  # noqa: PLW0603
    _global_metrics = PipelineMetrics()


# ── Health Check ──────────────────────────────────────────────────────────────

@dataclass
class AgentHealthStatus:
    """★ NEW: Health status for a single agent."""

    agent_name: str
    status: str  # "healthy", "degraded", "unhealthy", "unknown"
    last_run_ms: float | None
    error_rate: float
    call_count: int
    message: str


def agent_health_check(
    metrics: PipelineMetrics | None = None,
    error_rate_threshold: float = 0.10,  # 10% error rate = degraded
    p95_threshold_ms: float = 5000.0,    # 5s p95 = degraded
) -> list[AgentHealthStatus]:
    """★ NEW: Check health of all agents based on metrics.

    Returns list of AgentHealthStatus with status: healthy/degraded/unhealthy/unknown.
    """
    if metrics is None:
        metrics = _global_metrics

    statuses: list[AgentHealthStatus] = []
    known_agents = ["screener", "technical", "fundamental", "risk", "executor"]

    for agent_name in known_agents:
        agent_m = metrics.get_agent_metrics(agent_name)
        if agent_m is None or agent_m.call_count == 0:
            statuses.append(AgentHealthStatus(
                agent_name=agent_name,
                status="unknown",
                last_run_ms=None,
                error_rate=0.0,
                call_count=0,
                message="No data — agent has not run yet",
            ))
            continue

        # Determine health
        p95 = agent_m.p95 or 0.0
        error_rate = agent_m.error_rate

        if error_rate >= 0.50:
            status = "unhealthy"
            message = f"Error rate {error_rate:.0%} ≥ 50%"
        elif error_rate >= error_rate_threshold or p95 >= p95_threshold_ms:
            status = "degraded"
            reasons = []
            if error_rate >= error_rate_threshold:
                reasons.append(f"error rate {error_rate:.0%}")
            if p95 >= p95_threshold_ms:
                reasons.append(f"p95={p95:.0f}ms ≥ {p95_threshold_ms:.0f}ms")
            message = "Degraded: " + ", ".join(reasons)
        else:
            status = "healthy"
            message = f"OK — p95={p95:.0f}ms, errors={error_rate:.0%}"

        statuses.append(AgentHealthStatus(
            agent_name=agent_name,
            status=status,
            last_run_ms=agent_m.durations_ms[-1] if agent_m.durations_ms else None,
            error_rate=error_rate,
            call_count=agent_m.call_count,
            message=message,
        ))

    return statuses


# ── Pipeline Dashboard ────────────────────────────────────────────────────────

def pipeline_dashboard(metrics: PipelineMetrics | None = None) -> dict[str, Any]:
    """★ NEW: Generate a monitoring dashboard summary.

    Returns a dict suitable for:
    - Logging to structured log
    - Sending to monitoring endpoint
    - Displaying in admin UI
    """
    if metrics is None:
        metrics = _global_metrics

    health_statuses = agent_health_check(metrics)
    overall_health = "healthy"
    for h in health_statuses:
        if h.status == "unhealthy":
            overall_health = "unhealthy"
            break
        if h.status == "degraded":
            overall_health = "degraded"

    dashboard = {
        "timestamp": datetime.now(UTC).isoformat(),
        "overall_health": overall_health,
        "pipeline": metrics.to_dict(),
        "agents": [
            {
                "name": h.agent_name,
                "status": h.status,
                "error_rate_pct": f"{h.error_rate * 100:.1f}%",
                "call_count": h.call_count,
                "message": h.message,
            }
            for h in health_statuses
        ],
    }

    # Log dashboard summary
    logger.info(
        json.dumps({
            "event": "pipeline_dashboard",
            "overall_health": overall_health,
            "pipeline_runs": metrics._pipeline_runs,
            "pipeline_p95_ms": metrics.pipeline_p95_ms,
        }, ensure_ascii=False)
    )

    return dashboard
