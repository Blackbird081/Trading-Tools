from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio")
async def get_portfolio() -> dict[str, object]:
    """Get current portfolio state. Stub for Phase 2."""
    return {"status": "stub", "message": "Portfolio endpoint pending Phase 5 integration"}
