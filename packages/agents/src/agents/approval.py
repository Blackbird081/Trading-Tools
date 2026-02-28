"""Tool Approval Flow — confirm trước khi đặt lệnh thật.

★ Inspired by Dexter's tool approval mechanism.
★ Trước khi ExecutorAgent đặt lệnh thật, cần user confirm qua WebSocket.
★ 3 loại quyết định: allow-once, allow-session, deny.
★ Session-approved tools không cần confirm lại trong cùng session.

Usage:
    approval = ApprovalManager(ws_manager)
    decision = await approval.request_approval(
        tool="place_order",
        args={"symbol": "FPT", "side": "BUY", "quantity": 1000, "price": "98500"},
    )
    if decision == ApprovalDecision.DENY:
        raise OrderDeniedError("User từ chối đặt lệnh")
"""

from __future__ import annotations

import asyncio
import logging
from enum import StrEnum
from typing import Any

logger = logging.getLogger("agents.approval")


class ApprovalDecision(StrEnum):
    """User's response to a tool approval prompt."""

    ALLOW_ONCE = "allow-once"       # Cho phép lần này
    ALLOW_SESSION = "allow-session"  # Cho phép cả session
    DENY = "deny"                    # Từ chối và dừng agent


class OrderDeniedError(Exception):
    """Raised when user denies an order placement."""


class ApprovalManager:
    """Manages tool approval flow via WebSocket.

    ★ Sends approval request to frontend via WebSocket.
    ★ Waits for user response (timeout: 30 seconds).
    ★ Session-approved tools skip future confirmations.
    ★ Graceful degradation: if no WebSocket, auto-deny for safety.
    """

    def __init__(
        self,
        ws_manager: Any,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._ws_manager = ws_manager
        self._timeout = timeout_seconds
        self._session_approved: set[str] = set()
        self._pending_approvals: dict[str, asyncio.Future[ApprovalDecision]] = {}

    async def request_approval(
        self,
        tool: str,
        args: dict[str, Any],
    ) -> ApprovalDecision:
        """Request user approval for a tool call.

        ★ If tool is session-approved, returns ALLOW_ONCE immediately.
        ★ Sends approval request via WebSocket and waits for response.
        ★ Times out after timeout_seconds → returns DENY for safety.
        """
        # Check session approval
        if tool in self._session_approved:
            logger.info("Tool '%s' is session-approved, skipping confirmation", tool)
            return ApprovalDecision.ALLOW_ONCE

        # If no WebSocket manager, auto-deny for safety
        if self._ws_manager is None:
            logger.warning("No WebSocket manager — auto-denying tool '%s' for safety", tool)
            return ApprovalDecision.DENY

        # Create approval request ID
        request_id = f"approval_{tool}_{id(args)}"

        # Create future for response
        future: asyncio.Future[ApprovalDecision] = asyncio.get_event_loop().create_future()
        self._pending_approvals[request_id] = future

        # Send approval request to frontend
        try:
            await self._ws_manager.broadcast_json({
                "type": "tool_approval_request",
                "payload": {
                    "requestId": request_id,
                    "tool": tool,
                    "args": args,
                    "message": self._format_approval_message(tool, args),
                    "timeoutSeconds": self._timeout,
                },
            })
        except Exception:
            logger.exception("Failed to send approval request")
            self._pending_approvals.pop(request_id, None)
            return ApprovalDecision.DENY

        # Wait for response with timeout
        try:
            decision = await asyncio.wait_for(future, timeout=self._timeout)
        except asyncio.TimeoutError:
            logger.warning("Approval timeout for tool '%s' — auto-denying", tool)
            decision = ApprovalDecision.DENY
        finally:
            self._pending_approvals.pop(request_id, None)

        # Handle session approval
        if decision == ApprovalDecision.ALLOW_SESSION:
            self._session_approved.add(tool)
            logger.info("Tool '%s' approved for entire session", tool)

        # Notify frontend of decision
        try:
            await self._ws_manager.broadcast_json({
                "type": "tool_approval_decision",
                "payload": {
                    "requestId": request_id,
                    "tool": tool,
                    "decision": decision.value,
                },
            })
        except Exception:
            pass

        return decision

    def resolve_approval(self, request_id: str, decision: str) -> bool:
        """Resolve a pending approval request (called when frontend responds).

        Returns True if request was found and resolved.
        """
        future = self._pending_approvals.get(request_id)
        if future is None or future.done():
            return False

        try:
            approval_decision = ApprovalDecision(decision)
            future.set_result(approval_decision)
            return True
        except ValueError:
            logger.warning("Invalid approval decision: %s", decision)
            future.set_result(ApprovalDecision.DENY)
            return False

    def clear_session_approvals(self) -> None:
        """Clear all session-approved tools (e.g., on session end)."""
        self._session_approved.clear()

    @staticmethod
    def _format_approval_message(tool: str, args: dict[str, Any]) -> str:
        """Format human-readable approval message."""
        if tool == "place_order":
            symbol = args.get("symbol", "?")
            side = args.get("side", "?")
            quantity = args.get("quantity", "?")
            price = args.get("price", "?")
            value = float(str(price).replace(",", "")) * int(str(quantity).replace(",", "")) if price and quantity else 0
            return (
                f"⚠️ Xác nhận đặt lệnh THẬT:\n"
                f"  {side} {symbol} × {quantity:,} @ {price} VND\n"
                f"  Giá trị: {value:,.0f} VND\n"
                f"Bạn có muốn tiếp tục không?"
            )
        elif tool == "cancel_order":
            order_id = args.get("order_id", "?")
            return f"⚠️ Xác nhận hủy lệnh: {order_id}"
        else:
            return f"⚠️ Xác nhận thực thi tool: {tool}\nTham số: {args}"
