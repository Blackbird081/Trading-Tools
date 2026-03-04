from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Query

from interface.observability import get_correlation_id, list_events

router = APIRouter(tags=["observability"])


@router.get("/observability/events")
async def get_observability_events(
    flow: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=400),
) -> dict[str, object]:
    items = list_events(flow=flow, limit=limit)
    return {
        "count": len(items),
        "flow": flow,
        "events": items,
        "correlation_id": get_correlation_id(),
        "timestamp": datetime.now(UTC).isoformat(),
    }

