from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interface.rest.company import router as company_router
from interface.rest.data_loader import router as data_loader_router
from interface.rest.health import router as health_router
from interface.ws.market_ws import router as market_ws_router

logger = logging.getLogger("interface.app")

_DEFAULT_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3004",
    "http://localhost:3005",
]

_ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
_ALLOWED_HEADERS = ["Content-Type", "Authorization", "X-Request-ID", "X-Consumer-ID", "X-Timestamp", "X-Signature"]


def _get_cors_origins() -> list[str]:
    env_origins = os.getenv("CORS_ORIGINS", "")
    if env_origins:
        return [o.strip() for o in env_origins.split(",") if o.strip()]
    return _DEFAULT_DEV_ORIGINS


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """★ RES-02: Graceful startup and shutdown lifecycle.

    Startup: initialize dependencies.
    Shutdown: drain in-flight requests, close connections.
    """
    logger.info("Application starting up...")

    # Startup: initialize DuckDB pool
    try:
        from adapters.duckdb.connection import get_default_pool
        db_path = os.getenv("DUCKDB_PATH", "data/trading.duckdb")
        max_conn = int(os.getenv("DUCKDB_MAX_CONNECTIONS", "5"))
        pool = get_default_pool(db_path=db_path, max_connections=max_conn)
        app.state.db_pool = pool
        logger.info("DuckDB pool initialized: path=%s, max_connections=%d", db_path, max_conn)
    except Exception:
        logger.warning("DuckDB pool initialization failed — running without pool")

    logger.info("Application startup complete")
    yield

    # ★ Shutdown: graceful cleanup
    logger.info("Application shutting down...")

    # Close DuckDB pool
    pool = getattr(app.state, "db_pool", None)
    if pool is not None:
        await pool.shutdown()

    # Close WebSocket connections
    try:
        from interface.ws.manager import ws_manager
        await ws_manager.close_all()
    except Exception:
        pass

    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """FastAPI application factory with graceful shutdown."""
    app = FastAPI(
        title="AlgoTrading API",
        description="Enterprise Algo-Trading Platform on Hybrid AI",
        version="0.1.0",
        lifespan=lifespan,  # ★ RES-02: Graceful shutdown
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_cors_origins(),
        allow_credentials=True,
        allow_methods=_ALLOWED_METHODS,
        allow_headers=_ALLOWED_HEADERS,
    )
    app.include_router(health_router, prefix="/api")
    app.include_router(data_loader_router, prefix="/api")
    app.include_router(company_router, prefix="/api")
    app.include_router(market_ws_router)
    return app


app = create_app()
