from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from interface.ws.manager import ConnectionManager

logger = logging.getLogger("ws.market")

router = APIRouter()
manager = ConnectionManager()


@router.websocket("/ws/market")
async def market_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time market data and approval responses."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("Received from client: %s", data)

            # Handle approval responses from frontend
            try:
                import json
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
            except Exception:
                pass  # Non-JSON or non-approval messages are fine

    except WebSocketDisconnect:
        await manager.disconnect(websocket)
