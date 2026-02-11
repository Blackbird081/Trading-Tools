from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interface.rest.company import router as company_router
from interface.rest.data_loader import router as data_loader_router
from interface.rest.health import router as health_router
from interface.ws.market_ws import router as market_ws_router


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title="AlgoTrading API",
        description="Enterprise Algo-Trading Platform on Hybrid AI",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002","http://localhost:3003","http://localhost:3004","http://localhost:3005"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, prefix="/api")
    app.include_router(data_loader_router, prefix="/api")
    app.include_router(company_router, prefix="/api")
    app.include_router(market_ws_router)
    return app


app = create_app()
