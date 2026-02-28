from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interface.rest.company import router as company_router
from interface.rest.data_loader import router as data_loader_router
from interface.rest.health import router as health_router
from interface.ws.market_ws import router as market_ws_router

_DEFAULT_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003",
    "http://localhost:3004",
    "http://localhost:3005",
]

_ALLOWED_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
_ALLOWED_HEADERS = ["Content-Type", "Authorization", "X-Request-ID"]


def _get_cors_origins() -> list[str]:
    env_origins = os.getenv("CORS_ORIGINS", "")
    if env_origins:
        return [o.strip() for o in env_origins.split(",") if o.strip()]
    return _DEFAULT_DEV_ORIGINS


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="AlgoTrading API",
        description="Enterprise Algo-Trading Platform on Hybrid AI",
        version="0.1.0",
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
