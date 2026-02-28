"""Telegram notification adapter."""
from __future__ import annotations
import logging
import os
from decimal import Decimal
from typing import Any
import httpx

logger = logging.getLogger("adapters.notifier.telegram")
TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramNotifier:
    """Telegram bot notification adapter."""

    def __init__(self, bot_token: str | None = None, chat_id: str | None = None, http_client: httpx.AsyncClient | None = None) -> None:
        self._token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self._http = http_client or httpx.AsyncClient(timeout=httpx.Timeout(5.0))
        self._enabled = bool(self._token and self._chat_id)

    async def send_order_fill(self, symbol: str, side: str, quantity: int, price: Decimal, order_id: str) -> None:
        emoji = "🟢" if side == "BUY" else "🔴"
        await self._send(f"{emoji} *Order Filled*\nSymbol: `{symbol}`\nSide: `{side}`\nQty: `{quantity:,}`\nPrice: `{price:,.0f} VND`\nOrder ID: `{order_id}`")

    async def send_risk_alert(self, alert_type: str, symbol: str, reason: str) -> None:
        await self._send(f"⚠️ *Risk Alert*\nType: `{alert_type}`\nSymbol: `{symbol}`\nReason: {reason}")

    async def send_kill_switch_alert(self, activated: bool) -> None:
        msg = "🚨 *KILL SWITCH ACTIVATED*\nAll trading has been halted." if activated else "✅ *Kill Switch Deactivated*\nTrading resumed."
        await self._send(msg)

    async def send_daily_summary(self, date: str, realized_pnl: Decimal, unrealized_pnl: Decimal, nav: Decimal, orders_count: int) -> None:
        emoji = "📈" if realized_pnl >= 0 else "📉"
        await self._send(f"{emoji} *Daily Summary — {date}*\nRealized P&L: `{realized_pnl:+,.0f} VND`\nNAV: `{nav:,.0f} VND`\nOrders: `{orders_count}`")

    async def send_message(self, text: str) -> None:
        await self._send(text)

    async def _send(self, text: str) -> None:
        if not self._enabled:
            return
        try:
            url = TELEGRAM_API_BASE.format(token=self._token)
            payload: dict[str, Any] = {"chat_id": self._chat_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
            response = await self._http.post(url, json=payload)
            if response.status_code != 200:
                logger.warning("Telegram send failed: HTTP %d", response.status_code)
        except Exception as exc:
            logger.warning("Telegram notification failed: %s", exc)

    async def close(self) -> None:
        await self._http.aclose()
