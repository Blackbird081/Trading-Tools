from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("adapters.openvino")


class OpenVINOEngine:
    """OpenVINO GenAI inference engine with NPU/GPU/CPU auto-detection.

    Gracefully degrades when openvino_genai is not installed.
    """

    def __init__(
        self,
        model_path: Path,
        device: str = "AUTO",
        max_new_tokens: int = 512,
        temperature: float = 0.3,
    ) -> None:
        self._model_path = model_path
        self._device = device
        self._max_new_tokens = max_new_tokens
        self._temperature = temperature
        self._pipe: Any = None
        self._available = False

    def initialize(self) -> None:
        """Load model. Call once at startup."""
        try:
            import openvino_genai as ov_genai

            if self._device == "AUTO":
                self._device = detect_optimal_device()

            self._pipe = ov_genai.LLMPipeline(
                str(self._model_path),
                self._device,
            )
            # Warmup
            _ = self._pipe.generate("Hello", max_new_tokens=5, do_sample=False)
            self._available = True
            logger.info("OpenVINO engine initialized on %s", self._device)
        except ImportError:
            logger.warning("openvino_genai not installed — AI engine unavailable")
            self._available = False
        except Exception:
            logger.exception("Failed to initialize OpenVINO engine")
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def generate_sync(self, prompt: str) -> str:
        """Synchronous generation — blocks calling thread."""
        if not self._available or self._pipe is None:
            return "[AI engine unavailable]"

        try:
            import openvino_genai as ov_genai

            config = ov_genai.GenerationConfig()
            config.max_new_tokens = self._max_new_tokens
            config.temperature = self._temperature
            config.do_sample = self._temperature > 0
            config.top_p = 0.9
            config.repetition_penalty = 1.1
            result: str = self._pipe.generate(prompt, config)
            return result
        except Exception:
            logger.exception("Generation failed")
            return "[Generation error]"

    async def generate(self, prompt: str) -> str:
        """Async wrapper — offloads to thread pool."""
        return await asyncio.to_thread(self.generate_sync, prompt)


def detect_optimal_device() -> str:
    """Auto-detect best device: NPU > GPU > CPU."""
    try:
        import openvino as ov

        core = ov.Core()
        available = core.available_devices
        if "NPU" in available:
            return "NPU"
        if "GPU" in available:
            return "GPU"
    except ImportError:
        pass
    return "CPU"


def get_device_info() -> dict[str, str]:
    """Return info about available compute devices."""
    try:
        import openvino as ov

        core = ov.Core()
        info: dict[str, str] = {}
        for device in core.available_devices:
            try:
                name: str = core.get_property(device, "FULL_DEVICE_NAME")
                info[device] = name
            except Exception:
                info[device] = "Unknown"
        return info
    except ImportError:
        return {"CPU": "OpenVINO not installed"}
