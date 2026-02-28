"""Backtesting Engine — replay historical ticks through agent pipeline.

★ Inspired by FinceptTerminal's comprehensive metrics.
★ Includes: Sharpe, Sortino, Calmar, SQN, Profit Factor, CAGR.
"""
from __future__ import annotations
import logging
import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

logger = logging.getLogger("agents.backtesting")


@dataclass
class BacktestTrade:
    symbol: str
    side: str
    quantity: int
    price: Decimal
    date: date
    order_id: str


@dataclass
class BacktestResult:
    """Results of a backtest run with comprehensive metrics."""

    start_date: date
    end_date: date
    initial_capital: Decimal
    final_capital: Decimal
    trades: list[BacktestTrade] = field(default_factory=list)
    daily_nav: list[Decimal] = field(default_factory=list)

    @property
    def total_return(self) -> Decimal:
        return self.final_capital - self.initial_capital

    @property
    def total_return_pct(self) -> Decimal:
        if self.initial_capital == 0:
            return Decimal("0")
        return self.total_return / self.initial_capital

    @property
    def cagr(self) -> Decimal:
        days = (self.end_date - self.start_date).days
        if days <= 0 or self.initial_capital <= 0:
            return Decimal("0")
        ratio = float(self.final_capital / self.initial_capital)
        if ratio <= 0:
            return Decimal("0")
        return Decimal(str(round(ratio ** (365.25 / days) - 1.0, 4)))

    @property
    def trade_count(self) -> int:
        return len(self.trades)

    @property
    def _trade_pnls(self) -> list[Decimal]:
        buy_prices: dict[str, list[Decimal]] = {}
        pnls: list[Decimal] = []
        for trade in self.trades:
            if trade.side == "BUY":
                buy_prices.setdefault(trade.symbol, []).append(trade.price)
            elif trade.side == "SELL" and trade.symbol in buy_prices:
                buys = buy_prices[trade.symbol]
                if buys:
                    avg_buy = sum(buys) / len(buys)
                    pnls.append((trade.price - avg_buy) * trade.quantity)
        return pnls

    @property
    def win_rate(self) -> Decimal:
        pnls = self._trade_pnls
        if not pnls:
            return Decimal("0")
        wins = sum(1 for p in pnls if p > 0)
        return Decimal(str(wins)) / Decimal(str(len(pnls)))

    @property
    def profit_factor(self) -> Decimal:
        pnls = self._trade_pnls
        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        if gross_loss == 0:
            return Decimal("999") if gross_profit > 0 else Decimal("0")
        return gross_profit / gross_loss

    @property
    def sqn(self) -> Decimal:
        pnls = self._trade_pnls
        if len(pnls) < 2:
            return Decimal("0")
        mean_pnl = sum(pnls) / len(pnls)
        variance = sum((p - mean_pnl) ** 2 for p in pnls) / (len(pnls) - 1)
        std_dev = Decimal(str(math.sqrt(float(variance))))
        if std_dev == 0:
            return Decimal("0")
        return Decimal(str(round(float((mean_pnl / std_dev) * Decimal(str(math.sqrt(len(pnls))))), 4)))

    def _get_daily_returns(self) -> list[float]:
        if len(self.daily_nav) < 2:
            return []
        return [float((self.daily_nav[i] - self.daily_nav[i - 1]) / self.daily_nav[i - 1]) for i in range(1, len(self.daily_nav)) if self.daily_nav[i - 1] > 0]

    @property
    def sharpe_ratio(self) -> Decimal:
        returns = self._get_daily_returns()
        if len(returns) < 2:
            return Decimal("0")
        mean_r = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
        if std_dev == 0:
            return Decimal("0")
        return Decimal(str(round((mean_r / std_dev) * math.sqrt(252), 4)))

    @property
    def sortino_ratio(self) -> Decimal:
        returns = self._get_daily_returns()
        if len(returns) < 2:
            return Decimal("0")
        mean_r = sum(returns) / len(returns)
        downside = [r for r in returns if r < 0]
        if not downside:
            return Decimal("999")
        downside_std = math.sqrt(sum(r ** 2 for r in downside) / len(downside))
        if downside_std == 0:
            return Decimal("0")
        return Decimal(str(round((mean_r / downside_std) * math.sqrt(252), 4)))

    @property
    def max_drawdown_pct(self) -> Decimal:
        if len(self.daily_nav) < 2:
            return Decimal("0")
        peak = self.daily_nav[0]
        max_dd = Decimal("0")
        for nav in self.daily_nav:
            if nav > peak:
                peak = nav
            if peak > 0:
                dd = (peak - nav) / peak
                if dd > max_dd:
                    max_dd = dd
        return max_dd

    @property
    def calmar_ratio(self) -> Decimal:
        max_dd = self.max_drawdown_pct
        if max_dd == 0:
            return Decimal("999")
        cagr = self.cagr
        if cagr <= 0:
            return Decimal("0")
        return Decimal(str(round(float(cagr / max_dd), 4)))

    @property
    def volatility(self) -> Decimal:
        returns = self._get_daily_returns()
        if len(returns) < 2:
            return Decimal("0")
        mean_r = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
        return Decimal(str(round(math.sqrt(variance) * math.sqrt(252), 4)))

    def to_dict(self) -> dict[str, object]:
        return {
            "totalReturn": str(self.total_return), "totalReturnPct": str(self.total_return_pct),
            "CAGR": str(self.cagr), "sharpeRatio": str(self.sharpe_ratio),
            "sortinoRatio": str(self.sortino_ratio), "calmarRatio": str(self.calmar_ratio),
            "volatility": str(self.volatility), "maxDrawdown": str(self.max_drawdown_pct),
            "totalTrades": self.trade_count, "winRate": str(self.win_rate),
            "profitFactor": str(self.profit_factor), "SQN": str(self.sqn),
            "startDate": self.start_date.isoformat(), "endDate": self.end_date.isoformat(),
            "initialCapital": str(self.initial_capital), "finalCapital": str(self.final_capital),
        }


class BacktestEngine:
    """Backtesting engine — replays historical data through agent pipeline."""

    def __init__(self, tick_repo: Any, screener_port: Any | None = None, slippage_pct: Decimal = Decimal("0.001"), commission_pct: Decimal = Decimal("0.0015")) -> None:
        self._tick_repo = tick_repo
        self._screener = screener_port
        self._slippage_pct = slippage_pct
        self._commission_pct = commission_pct

    async def run(self, symbols: list[str], start_date: date, end_date: date, initial_capital: Decimal = Decimal("1000000000"), max_position_pct: Decimal = Decimal("0.20"), score_threshold: float = 5.0) -> BacktestResult:
        capital = initial_capital
        positions: dict[str, tuple[int, Decimal]] = {}
        trades: list[BacktestTrade] = []
        daily_nav: list[Decimal] = [initial_capital]
        trade_counter = 0

        for symbol in symbols:
            try:
                ohlcv_data = await self._tick_repo.get_ohlcv(symbol, start_date, end_date)
                if len(ohlcv_data) < 20:
                    continue
                for i in range(20, len(ohlcv_data)):
                    window = ohlcv_data[max(0, i - 200):i]
                    current = ohlcv_data[i]
                    current_price = Decimal(str(current.get("close", 0)))
                    current_date_str = str(current.get("trading_date", ""))
                    current_date = date.fromisoformat(current_date_str[:10]) if current_date_str else end_date
                    if current_price <= 0:
                        continue
                    score = self._compute_score(window)
                    in_position = symbol in positions
                    if score >= score_threshold and not in_position:
                        qty = int(capital * max_position_pct / current_price / 100) * 100
                        if qty > 0:
                            cost = current_price * qty * (1 + self._slippage_pct + self._commission_pct)
                            if cost <= capital:
                                capital -= cost
                                positions[symbol] = (qty, current_price)
                                trade_counter += 1
                                trades.append(BacktestTrade(symbol=symbol, side="BUY", quantity=qty, price=current_price, date=current_date, order_id=f"BT-{trade_counter:06d}"))
                    elif score <= -score_threshold and in_position:
                        qty, avg_price = positions[symbol]
                        proceeds = current_price * qty * (1 - self._slippage_pct - self._commission_pct)
                        capital += proceeds
                        del positions[symbol]
                        trade_counter += 1
                        trades.append(BacktestTrade(symbol=symbol, side="SELL", quantity=qty, price=current_price, date=current_date, order_id=f"BT-{trade_counter:06d}"))
                    nav = capital + sum(Decimal(str(p[0])) * current_price for sym, p in positions.items() if sym == symbol)
                    daily_nav.append(nav)
            except Exception:
                logger.exception("Backtest failed for %s", symbol)

        result = BacktestResult(start_date=start_date, end_date=end_date, initial_capital=initial_capital, final_capital=capital, trades=trades, daily_nav=daily_nav)
        logger.info("Backtest complete: return=%.2f%%, trades=%d", float(result.total_return_pct * 100), result.trade_count)
        return result

    @staticmethod
    def _compute_score(ohlcv_window: list[dict[str, Any]]) -> float:
        if len(ohlcv_window) < 2:
            return 0.0
        closes = [float(c.get("close", 0)) for c in ohlcv_window[-5:] if c.get("close")]
        if len(closes) < 2 or closes[0] <= 0:
            return 0.0
        return max(-10.0, min(10.0, (closes[-1] - closes[0]) / closes[0] * 100))
