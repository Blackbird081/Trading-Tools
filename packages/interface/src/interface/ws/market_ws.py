from __future__ import annotations

import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from interface.observability import record_event, reset_correlation_id, set_correlation_id
from interface.ws.manager import ws_manager

logger = logging.getLogger("ws.market")

router = APIRouter()


@router.websocket("/ws/market")
async def market_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time market data and approval responses."""
    incoming_correlation = websocket.headers.get("x-correlation-id", "").strip() or str(uuid.uuid4())
    token = set_correlation_id(incoming_correlation)
    await ws_manager.connect(websocket)
    record_event(
        flow="ws",
        level="info",
        message="WebSocket client connected",
        metadata={"path": "/ws/market", "client": str(getattr(websocket.client, "host", "unknown"))},
    )
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("Received from client: %s", data)
            record_event(
                flow="ws",
                level="info",
                message="WebSocket message received",
                metadata={"size": len(data), "path": "/ws/market"},
            )

            # Handle approval responses from frontend
            try:
                msg = json.loads(data)
                if msg.get("type") == "tool_approval_response":
                    from agents.approval import handle_approval_response
                    request_id = msg.get("requestId", "")
                    decision = msg.get("decision", "deny")
                    resolved = handle_approval_response(request_id, decision)
                    logger.info(
                        "Approval response: requestId=%s, decision=%s, resolved=%s",
                        request_id, decision, resolved,
                    )
                    record_event(
                        flow="ws",
                        level="info",
                        message="Tool approval response received",
                        metadata={"request_id": request_id, "decision": decision, "resolved": bool(resolved)},
                    )
            except Exception:
                pass  # Non-JSON or non-approval messages are fine

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
        record_event(
            flow="ws",
            level="info",
            message="WebSocket client disconnected",
            metadata={"path": "/ws/market"},
        )
    except Exception as exc:
        record_event(
            flow="ws",
            level="error",
            message=f"WebSocket endpoint error: {exc}",
            metadata={"path": "/ws/market"},
        )
        await ws_manager.disconnect(websocket)
    finally:
        reset_correlation_id(token)
