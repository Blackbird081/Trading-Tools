from __future__ import annotations

import json
import logging

from agents.observability import log_agent_step


class TestLogAgentStep:
    def test_log_entry_structure(self, caplog: logging.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="agents.pipeline"):
            log_agent_step(
                run_id="test-run-123",
                agent_name="technical",
                phase="analyzing",
                input_summary={"symbols": ["FPT"], "count": 1},
                output_summary={"scores": {"FPT": 7.5}},
                duration_ms=150.3,
            )
        assert len(caplog.records) == 1
        entry = json.loads(caplog.records[0].message)
        assert entry["run_id"] == "test-run-123"
        assert entry["agent"] == "technical"
        assert entry["phase"] == "analyzing"
        assert entry["duration_ms"] == 150.3
        assert "timestamp" in entry

    def test_log_with_prompt_version(self, caplog: logging.LogCaptureFixture) -> None:
        with caplog.at_level(logging.INFO, logger="agents.pipeline"):
            log_agent_step(
                run_id="test-run-456",
                agent_name="fundamental",
                phase="analyzing",
                input_summary={},
                output_summary={},
                duration_ms=5000.0,
                prompt_version="v1.0.0",
            )
        entry = json.loads(caplog.records[0].message)
        assert entry["prompt_version"] == "v1.0.0"

    def test_log_without_prompt_version(
        self,
        caplog: logging.LogCaptureFixture,
    ) -> None:
        with caplog.at_level(logging.INFO, logger="agents.pipeline"):
            log_agent_step(
                run_id="test-run-789",
                agent_name="screener",
                phase="screening",
                input_summary={},
                output_summary={},
                duration_ms=200.0,
            )
        entry = json.loads(caplog.records[0].message)
        assert "prompt_version" not in entry
