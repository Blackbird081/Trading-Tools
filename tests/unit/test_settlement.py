"""Unit tests for T+2.5 settlement logic.

Tests:
- Settlement date calculation (weekdays, weekends, holidays)
- can_sell_now() with various scenarios
- Holiday handling

Ref: Doc 05 §3.4
"""

from __future__ import annotations

from datetime import date

from core.use_cases.settlement import (
    calculate_settlement_date,
    can_sell_now,
    is_trading_day,
    next_trading_day,
)


class TestIsTradingDay:
    """Tests for is_trading_day()."""

    def test_weekday_is_trading_day(self) -> None:
        # Monday 2026-02-09
        assert is_trading_day(date(2026, 2, 9)) is True

    def test_saturday_is_not_trading_day(self) -> None:
        assert is_trading_day(date(2026, 2, 7)) is False  # Saturday

    def test_sunday_is_not_trading_day(self) -> None:
        assert is_trading_day(date(2026, 2, 8)) is False  # Sunday

    def test_new_year_holiday(self) -> None:
        assert is_trading_day(date(2026, 1, 1)) is False

    def test_reunification_day(self) -> None:
        assert is_trading_day(date(2026, 4, 30)) is False

    def test_labour_day(self) -> None:
        assert is_trading_day(date(2026, 5, 1)) is False

    def test_national_day(self) -> None:
        assert is_trading_day(date(2026, 9, 2)) is False


class TestNextTradingDay:
    """Tests for next_trading_day()."""

    def test_next_day_is_weekday(self) -> None:
        # Monday → Tuesday
        assert next_trading_day(date(2026, 2, 9)) == date(2026, 2, 10)

    def test_friday_to_monday(self) -> None:
        # Friday → Monday (skip weekend)
        assert next_trading_day(date(2026, 2, 6)) == date(2026, 2, 9)

    def test_skip_holiday(self) -> None:
        # Day before Reunification (April 29, Wednesday) → May 4 (Monday)
        # April 30 = Reunification, May 1 = Labour Day, May 2 = Sat, May 3 = Sun
        assert next_trading_day(date(2026, 4, 29)) == date(2026, 5, 4)


class TestCalculateSettlementDate:
    """Tests for T+2.5 settlement calculation."""

    def test_monday_trade(self) -> None:
        """Trade Monday → Sellable Wednesday afternoon."""
        result = calculate_settlement_date(date(2026, 2, 9))  # Monday
        assert result.settlement_date == date(2026, 2, 11)  # Wednesday
        assert result.sellable_session == "afternoon"

    def test_tuesday_trade(self) -> None:
        """Trade Tuesday → Sellable Thursday afternoon."""
        result = calculate_settlement_date(date(2026, 2, 10))  # Tuesday
        assert result.settlement_date == date(2026, 2, 12)  # Thursday
        assert result.sellable_session == "afternoon"

    def test_thursday_trade(self) -> None:
        """Trade Thursday → Sellable Monday afternoon (next week)."""
        result = calculate_settlement_date(date(2026, 2, 12))  # Thursday
        # T+1 = Friday (Feb 13), T+2 = Monday (Feb 16)
        assert result.settlement_date == date(2026, 2, 16)  # Monday

    def test_friday_trade(self) -> None:
        """Trade Friday → Sellable Tuesday afternoon (next week)."""
        result = calculate_settlement_date(date(2026, 2, 13))  # Friday
        # T+1 = Monday (Feb 16), T+2 = Tuesday (Feb 17)
        assert result.settlement_date == date(2026, 2, 17)  # Tuesday

    def test_trade_before_holiday(self) -> None:
        """Trade before holiday should skip holiday."""
        # Trade Apr 29 (Wed). April 30 = Reunification, May 1 = Labour
        # T+1 = May 4 (Mon), T+2 = May 5 (Tue)
        result = calculate_settlement_date(date(2026, 4, 29))
        assert result.settlement_date == date(2026, 5, 5)


class TestCanSellNow:
    """Tests for can_sell_now() T+2.5 check."""

    def test_before_settlement_cannot_sell(self) -> None:
        """Cannot sell before settlement date."""
        assert (
            can_sell_now(
                buy_date=date(2026, 2, 9),  # Monday
                current_date=date(2026, 2, 10),  # Tuesday (T+1)
                current_hour=10,
            )
            is False
        )

    def test_settlement_day_morning_cannot_sell(self) -> None:
        """Settlement day, morning session: NOT sellable (T+2.5, not T+2)."""
        assert (
            can_sell_now(
                buy_date=date(2026, 2, 9),  # Monday
                current_date=date(2026, 2, 11),  # Wednesday (T+2)
                current_hour=10,  # Morning
            )
            is False
        )

    def test_settlement_day_afternoon_can_sell(self) -> None:
        """Settlement day, afternoon session (>= 13:00): CAN sell."""
        assert (
            can_sell_now(
                buy_date=date(2026, 2, 9),  # Monday
                current_date=date(2026, 2, 11),  # Wednesday (T+2)
                current_hour=13,  # Afternoon
            )
            is True
        )

    def test_after_settlement_can_sell(self) -> None:
        """Day after settlement: always sellable."""
        assert (
            can_sell_now(
                buy_date=date(2026, 2, 9),  # Monday
                current_date=date(2026, 2, 12),  # Thursday (T+3)
                current_hour=9,
            )
            is True
        )

    def test_friday_buy_monday_cannot_sell(self) -> None:
        """Friday buy → Tuesday afternoon settlement. Monday cannot sell."""
        assert (
            can_sell_now(
                buy_date=date(2026, 2, 13),  # Friday
                current_date=date(2026, 2, 16),  # Monday
                current_hour=14,
            )
            is False
        )

    def test_friday_buy_tuesday_afternoon_can_sell(self) -> None:
        """Friday buy → Tuesday afternoon settlement."""
        assert (
            can_sell_now(
                buy_date=date(2026, 2, 13),  # Friday
                current_date=date(2026, 2, 17),  # Tuesday
                current_hour=13,
            )
            is True
        )
