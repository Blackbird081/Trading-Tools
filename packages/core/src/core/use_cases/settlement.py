"""T+2.5 settlement logic for Vietnamese stock market.

★ T+2.5 means: trade today → sellable afternoon (13:00) of T+2.
★ Must account for weekends and Vietnamese public holidays.
★ This is called by Risk Agent before approving SELL orders.

Ref: Doc 05 §3.4
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import NamedTuple


class SettlementDate(NamedTuple):
    """Settlement calculation result."""

    trade_date: date
    settlement_date: date
    sellable_session: str  # "morning" | "afternoon"


# Vietnam public holidays 2026 (update annually)
_VN_HOLIDAYS_2026: frozenset[date] = frozenset(
    {
        date(2026, 1, 1),  # New Year
        date(2026, 1, 26),  # Lunar New Year (approx)
        date(2026, 1, 27),
        date(2026, 1, 28),
        date(2026, 1, 29),
        date(2026, 1, 30),
        date(2026, 4, 30),  # Reunification Day
        date(2026, 5, 1),  # Labour Day
        date(2026, 9, 2),  # National Day
        # Add more as officially announced
    }
)


def is_trading_day(d: date) -> bool:
    """Check if a date is a valid trading day (weekday, not holiday)."""
    return d.weekday() < 5 and d not in _VN_HOLIDAYS_2026


def next_trading_day(d: date) -> date:
    """Find the next trading day after given date."""
    candidate = d + timedelta(days=1)
    while not is_trading_day(candidate):
        candidate += timedelta(days=1)
    return candidate


def calculate_settlement_date(trade_date: date) -> SettlementDate:
    """Calculate T+2.5 settlement date for a trade.

    T+2.5 means:
    - Count 2 full TRADING DAYS after trade date
    - Add half day (afternoon session of T+2)
    - Shares become sellable at 13:00 on settlement date

    Examples:
      Trade Monday    → Sellable Wednesday afternoon
      Trade Thursday  → Sellable Monday afternoon (next week)
      Trade Friday    → Sellable Tuesday afternoon (next week)
    """
    t1 = next_trading_day(trade_date)
    t2 = next_trading_day(t1)

    return SettlementDate(
        trade_date=trade_date,
        settlement_date=t2,
        sellable_session="afternoon",  # 13:00 onwards
    )


def can_sell_now(
    buy_date: date,
    current_date: date,
    current_hour: int,
) -> bool:
    """Check if shares bought on buy_date are sellable right now.

    ★ This function is called by Risk Agent before approving SELL orders.
    ★ Accounts for T+2.5 + holidays + weekend.
    """
    settlement = calculate_settlement_date(buy_date)

    if current_date > settlement.settlement_date:
        return True  # Past settlement date — fully sellable

    if current_date == settlement.settlement_date:
        return current_hour >= 13  # Afternoon session (T+2.5)

    return False  # Before settlement date — NOT sellable
