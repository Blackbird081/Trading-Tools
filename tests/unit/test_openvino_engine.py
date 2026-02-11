from __future__ import annotations

from pathlib import Path

from adapters.openvino.engine import OpenVINOEngine, detect_optimal_device


class TestOpenVINOEngine:
    def test_engine_not_available_without_openvino(self) -> None:
        engine = OpenVINOEngine(model_path=Path("/nonexistent"))
        engine.initialize()  # Should not raise
        assert engine.is_available is False

    def test_generate_sync_returns_fallback_when_unavailable(self) -> None:
        engine = OpenVINOEngine(model_path=Path("/nonexistent"))
        result = engine.generate_sync("test prompt")
        assert result == "[AI engine unavailable]"


class TestDetectDevice:
    def test_detect_returns_cpu_without_openvino(self) -> None:
        # Without openvino installed, should fallback to CPU
        device = detect_optimal_device()
        assert device == "CPU"
