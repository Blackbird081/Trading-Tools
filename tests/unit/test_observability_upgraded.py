"""Tests for upgraded Observability module.

★ Tests: PipelineMetrics, latency percentiles, error tracking,
         agent_health_check, pipeline_dashboard.
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal

import pytest

from agents.observability import (
    AgentMetrics,
    PipelineMetrics,
    agent_health_check,
    log_agent_step,
    log_pipeline_error,
    pipeline_dashboard,
    reset_pipeline_metrics,
)


class TestAgentMetrics:
    """Tests for AgentMetrics latency percentiles."""

    def test_record_single_call(self) -> None:
        m = AgentMetrics(agent_name="screener")
        m.record(150.0)
        assert m.call_count == 1
        assert m.error_count == 0
        assert m.avg_duration_ms == pytest.approx(150.0)

    def test_record_error(self) -> None:
        m = AgentMetrics(agent_name="screener")
        m.record(100.0, error=True)
        assert m.error_count == 1
        assert m.error_rate == pytest.approx(1.0)

    def test_percentiles_single_value(self) -> None:
        m = AgentMetrics(agent_name="technical")
        m.record(200.0)
        assert m.p50 == pytest.approx(200.0)
        assert m.p95 == pytest.approx(200.0)
        assert m.p99 == pytest.approx(200.0)

    def test_percentiles_multiple_values(self) -> None:
        m = AgentMetrics(agent_name="risk")
        for ms in [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]:
            m.record(float(ms))
        # p50 should be around 500-600ms
        assert m.p50 is not None
        assert 400 <= m.p50 <= 600
        # p95 should be near 1000ms
        assert m.p95 is not None
        assert m.p95 >= 900

    def test_empty_metrics_returns_none(self) -> None:
        m = AgentMetrics(agent_name="executor")
        assert m.p50 is None
        assert m.p95 is None
        assert m.p99 is None
        assert m.avg_duration_ms is None

    def test_to_dict_structure(self) -> None:
        m = AgentMetrics(agent_name="screener")
        m.record(100.0)
        m.record(200.0, error=True)
        d = m.to_dict()
        assert d["agent"] == "screener"
        assert d["call_count"] == 2
        assert d["error_count"] == 1
        assert "error_rate_pct" in d
        assert "p50_ms" in d
        assert "p95_ms" in d
        assert "p99_ms" in d


class TestPipelineMetrics:
    """Tests for PipelineMetrics aggregation."""

    def test_record_agent_creates_entry(self) -> None:
        m = PipelineMetrics()
        m.record_agent("screener", 150.0)
        agent_m = m.get_agent_metrics("screener")
        assert agent_m is not None
        assert agent_m.call_count == 1

    def test_record_pipeline_run(self) -> None:
        m = PipelineMetrics()
        m.record_pipeline_run(1000.0)
        m.record_pipeline_run(2000.0)
        assert m._pipeline_runs == 2
        assert m.pipeline_p50_ms is not None

    def test_pipeline_error_tracking(self) -> None:
        m = PipelineMetrics()
        m.record_pipeline_run(1000.0)
        m.record_pipeline_run(500.0, error=True)
        assert m._pipeline_errors == 1

    def test_to_dict_structure(self) -> None:
        m = PipelineMetrics()
        m.record_agent("screener", 100.0)
        m.record_pipeline_run(500.0)
        d = m.to_dict()
        assert "pipeline_runs" in d
        assert "pipeline_errors" in d
        assert "agents" in d
        assert "uptime_seconds" in d


class TestLogPipelineError:
    """Tests for structured error logging."""

    def test_log_error_structure(self, caplog: logging.LogCaptureFixture) -> None:
        with caplog.at_level(logging.ERROR, logger="agents.pipeline"):
            try:
                raise ValueError("Test error")
            except ValueError as exc:
                log_pipeline_error(
                    run_id="run-001",
                    agent_name="technical",
                    exc=exc,
                    context={"symbol": "FPT"},
                )

        assert len(caplog.records) == 1
        entry = json.loads(caplog.records[0].message)
        assert entry["event"] == "pipeline_error"
        assert entry["error_type"] == "ValueError"
        assert entry["error_message"] == "Test error"
        assert "stack_trace" in entry
        assert entry["context"]["symbol"] == "FPT"

    def test_log_error_without_context(self, caplog: logging.LogCaptureFixture) -> None:
        with caplog.at_level(logging.ERROR, logger="agents.pipeline"):
            try:
                raise RuntimeError("No context")
            except RuntimeError as exc:
                log_pipeline_error("run-002", "risk", exc)

        entry = json.loads(caplog.records[0].message)
        assert "context" not in entry


class TestLogAgentStepWithError:
    """Tests for log_agent_step with error field."""

    def test_log_step_with_error_uses_error_level(
        self, caplog: logging.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.ERROR, logger="agents.pipeline"):
            log_agent_step(
                run_id="run-003",
                agent_name="executor",
                phase="executing",
                input_summary={},
                output_summary={},
                duration_ms=100.0,
                error="Broker connection failed",
            )

        assert len(caplog.records) == 1
        assert caplog.records[0].levelno == logging.ERROR
        entry = json.loads(caplog.records[0].message)
        assert entry["error"] == "Broker connection failed"


class TestAgentHealthCheck:
    """Tests for agent_health_check()."""

    def test_unknown_status_for_no_data(self) -> None:
        m = PipelineMetrics()
        statuses = agent_health_check(m)
        for s in statuses:
            assert s.status == "unknown"

    def test_healthy_status_low_error_rate(self) -> None:
        m = PipelineMetrics()
        for _ in range(10):
            m.record_agent("screener", 100.0)
        statuses = agent_health_check(m)
        screener = next(s for s in statuses if s.agent_name == "screener")
        assert screener.status == "healthy"

    def test_degraded_status_high_error_rate(self) -> None:
        m = PipelineMetrics()
        for _ in range(5):
            m.record_agent("technical", 100.0, error=True)
        for _ in range(5):
            m.record_agent("technical", 100.0)
        statuses = agent_health_check(m)
        technical = next(s for s in statuses if s.agent_name == "technical")
        assert technical.status in ("degraded", "unhealthy")

    def test_unhealthy_status_very_high_error_rate(self) -> None:
        m = PipelineMetrics()
        for _ in range(10):
            m.record_agent("risk", 100.0, error=True)
        statuses = agent_health_check(m)
        risk = next(s for s in statuses if s.agent_name == "risk")
        assert risk.status == "unhealthy"

    def test_degraded_status_high_latency(self) -> None:
        m = PipelineMetrics()
        for _ in range(10):
            m.record_agent("fundamental", 10000.0)  # 10s — very slow
        statuses = agent_health_check(m, p95_threshold_ms=5000.0)
        fundamental = next(s for s in statuses if s.agent_name == "fundamental")
        assert fundamental.status == "degraded"


class TestPipelineDashboard:
    """Tests for pipeline_dashboard()."""

    def test_dashboard_structure(self) -> None:
        m = PipelineMetrics()
        m.record_agent("screener", 100.0)
        m.record_pipeline_run(500.0)
        dashboard = pipeline_dashboard(m)
        assert "timestamp" in dashboard
        assert "overall_health" in dashboard
        assert "pipeline" in dashboard
        assert "agents" in dashboard

    def test_dashboard_overall_health_healthy(self) -> None:
        m = PipelineMetrics()
        for agent in ["screener", "technical", "risk", "executor"]:
            for _ in range(5):
                m.record_agent(agent, 100.0)
        dashboard = pipeline_dashboard(m)
        assert dashboard["overall_health"] == "healthy"

    def test_dashboard_overall_health_degraded(self) -> None:
        m = PipelineMetrics()
        # 50% error rate on screener
        for _ in range(5):
            m.record_agent("screener", 100.0, error=True)
        for _ in range(5):
            m.record_agent("screener", 100.0)
        dashboard = pipeline_dashboard(m)
        assert dashboard["overall_health"] in ("degraded", "unhealthy")
