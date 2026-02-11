from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("interface.di")


class SystemDependencies:
    """Dependency injection container for the full system.

    Wires together all components: data pipeline, agents, OMS, and AI engine.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._components: dict[str, Any] = {}

    async def initialize(self) -> None:
        """Initialize all system dependencies in order."""
        logger.info("Initializing system dependencies...")

        # 1. AI Engine (optional — degrades gracefully)
        await self._init_ai_engine()

        # 2. Agent Pipeline
        self._init_agents()

        # 3. OMS (Order Management)
        self._init_oms()

        logger.info("System dependencies initialized")

    async def _init_ai_engine(self) -> None:
        """Initialize OpenVINO engine with auto-device detection."""
        try:
            from adapters.openvino.engine import OpenVINOEngine

            model_path = Path(self._config.get("model_path", "data/models/phi-3-mini-int4"))
            if model_path.exists():  # noqa: ASYNC240
                engine = OpenVINOEngine(model_path=model_path, device="AUTO")
                engine.initialize()
                self._components["ai_engine"] = engine
                logger.info(
                    "AI engine: %s",
                    "available" if engine.is_available else "unavailable",
                )
            else:
                logger.warning("Model not found at %s — AI engine disabled", model_path)
        except Exception:
            logger.warning("AI engine initialization failed — running without AI")

    def _init_agents(self) -> None:
        """Initialize the multi-agent pipeline."""
        try:
            from agents.executor_agent import ExecutorAgent
            from agents.risk_agent import RiskAgent
            from agents.screener_agent import ScreenerAgent
            from agents.technical_agent import TechnicalAgent

            self._components["screener"] = ScreenerAgent(
                screener_port=self._components.get("screener_port"),
                tick_repo=self._components.get("tick_repo"),
            )
            self._components["technical"] = TechnicalAgent(
                tick_repo=self._components.get("tick_repo"),
            )
            self._components["risk"] = RiskAgent(
                tick_repo=self._components.get("tick_repo"),
                risk_limits=self._components.get("risk_limits"),
            )
            self._components["executor"] = ExecutorAgent(
                broker_port=self._components.get("broker"),
            )
            logger.info("Agent pipeline initialized")
        except Exception:
            logger.exception("Failed to initialize agent pipeline")

    def _init_oms(self) -> None:
        """Initialize Order Management System."""
        try:
            from core.use_cases.place_order import IdempotencyStore

            self._components["idempotency_store"] = IdempotencyStore()
            logger.info("OMS initialized")
        except Exception:
            logger.exception("Failed to initialize OMS")

    def get(self, name: str) -> Any:
        """Get a component by name."""
        return self._components.get(name)

    async def shutdown(self) -> None:
        """Graceful shutdown of all components."""
        logger.info("Shutting down system...")
        # Stop order sync if running
        sync = self._components.get("order_sync")
        if sync and hasattr(sync, "stop"):
            await sync.stop()
        logger.info("System shutdown complete")
