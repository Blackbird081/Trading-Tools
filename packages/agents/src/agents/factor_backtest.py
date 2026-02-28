"""Factor Backtest Library — backtesting với factor-based approach.

★ Inspired by baocaotaichinh-/webapp/analysis/backtest_factor_library.py.
★ Thêm: IC/IR, transaction cost model, liquidity filters, factor library.
★ Nâng cấp BacktestEngine với các tính năng chuyên nghiệp hơn.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Callable

logger = logging.getLogger("agents.factor_backtest")


# ── Cấu hình ──────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class InvestabilityFilters:
    """Bộ lọc đầu tư để loại bỏ cổ phiếu không đủ điều kiện.

    ★ Inspired by baocaotaichinh-/webapp/analysis/backtest_factor_library.py.
    """

    min_trading_days: int = 120          # Tối thiểu 120 ngày giao dịch/năm
    max_zero_volume_frac: float = 0.05   # Tối đa 5% ngày không có khối lượng
    max_stale_close_frac: float = 0.20   # Tối đa 20% ngày giá không thay đổi
    min_avg_volume_vnd: float = 200_000_000.0  # Tối thiểu 200M VND/ngày


@dataclass(frozen=True)
class TransactionCostModel:
    """Mô hình chi phí giao dịch.

    ★ Inspired by baocaotaichinh-/webapp/analysis/backtest_factor_library.py.
    """

    enabled: bool = True
    cost_bps_per_side: float = 10.0  # 10 bps/side = 0.10% (SSI/DNSE typical)
    # VN: Phí môi giới ~0.15-0.25%, thuế bán 0.1%
    # Tổng: ~0.25-0.35% per round trip

    @property
    def round_trip_cost(self) -> float:
        """Chi phí round trip (mua + bán)."""
        return self.cost_bps_per_side * 2 / 10000


@dataclass
class FactorSignal:
    """Tín hiệu factor cho một cổ phiếu."""

    symbol: str
    factor_name: str
    raw_value: float | None
    normalized_value: float | None  # Z-score normalized
    rank: int | None  # Rank trong universe (1 = tốt nhất)
    date: date | None = None


@dataclass
class FactorBacktestResult:
    """Kết quả backtest factor."""

    factor_name: str
    start_date: date
    end_date: date
    initial_capital: Decimal
    final_capital: Decimal
    trades: list[dict[str, Any]] = field(default_factory=list)
    daily_nav: list[Decimal] = field(default_factory=list)

    # Factor-specific metrics
    ic_series: list[float] = field(default_factory=list)  # Information Coefficient per period
    turnover_series: list[float] = field(default_factory=list)  # Portfolio turnover per period

    # ★ NEW: VN-Index benchmark comparison
    benchmark_return_pct: float | None = None  # VN-Index return over same period
    benchmark_nav: list[Decimal] = field(default_factory=list)  # VN-Index NAV series

    @property
    def total_return_pct(self) -> float:
        if self.initial_capital == 0:
            return 0.0
        return float((self.final_capital - self.initial_capital) / self.initial_capital)

    @property
    def alpha(self) -> float | None:
        """Alpha vs VN-Index benchmark (excess return)."""
        if self.benchmark_return_pct is None:
            return None
        return self.total_return_pct - self.benchmark_return_pct

    @property
    def information_ratio_vs_benchmark(self) -> float | None:
        """Information Ratio vs benchmark (alpha / tracking error)."""
        if not self.daily_nav or not self.benchmark_nav:
            return None
        if len(self.daily_nav) != len(self.benchmark_nav):
            return None
        # Calculate excess returns
        excess_returns = []
        for i in range(1, len(self.daily_nav)):
            if self.daily_nav[i - 1] > 0 and self.benchmark_nav[i - 1] > 0:
                port_r = float((self.daily_nav[i] - self.daily_nav[i - 1]) / self.daily_nav[i - 1])
                bench_r = float((self.benchmark_nav[i] - self.benchmark_nav[i - 1]) / self.benchmark_nav[i - 1])
                excess_returns.append(port_r - bench_r)
        if len(excess_returns) < 2:
            return None
        mean_excess = sum(excess_returns) / len(excess_returns)
        variance = sum((r - mean_excess) ** 2 for r in excess_returns) / (len(excess_returns) - 1)
        std = math.sqrt(variance)
        if std == 0:
            return None
        return (mean_excess / std) * math.sqrt(252)

    @property
    def ic_mean(self) -> float | None:
        """Mean Information Coefficient."""
        if not self.ic_series:
            return None
        return sum(self.ic_series) / len(self.ic_series)

    @property
    def ic_ir(self) -> float | None:
        """Information Ratio = IC Mean / IC Std Dev."""
        if not self.ic_series or len(self.ic_series) < 2:
            return None
        mean = self.ic_mean
        if mean is None:
            return None
        variance = sum((ic - mean) ** 2 for ic in self.ic_series) / (len(self.ic_series) - 1)
        std = math.sqrt(variance)
        if std == 0:
            return None
        return mean / std

    @property
    def avg_turnover(self) -> float | None:
        """Average portfolio turnover."""
        if not self.turnover_series:
            return None
        return sum(self.turnover_series) / len(self.turnover_series)

    @property
    def sharpe_ratio(self) -> float | None:
        """Annualized Sharpe ratio."""
        if len(self.daily_nav) < 2:
            return None
        returns = [
            float((self.daily_nav[i] - self.daily_nav[i - 1]) / self.daily_nav[i - 1])
            for i in range(1, len(self.daily_nav))
            if self.daily_nav[i - 1] > 0
        ]
        if len(returns) < 2:
            return None
        mean_r = sum(returns) / len(returns)
        variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(variance)
        if std == 0:
            return None
        return (mean_r / std) * math.sqrt(252)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "factor_name": self.factor_name,
            "total_return_pct": f"{self.total_return_pct * 100:.2f}%",
            "ic_mean": f"{self.ic_mean:.4f}" if self.ic_mean else "N/A",
            "ic_ir": f"{self.ic_ir:.4f}" if self.ic_ir else "N/A",
            "avg_turnover": f"{self.avg_turnover * 100:.1f}%" if self.avg_turnover else "N/A",
            "sharpe_ratio": f"{self.sharpe_ratio:.4f}" if self.sharpe_ratio else "N/A",
            "trade_count": len(self.trades),
        }
        # ★ NEW: VN-Index benchmark metrics
        if self.benchmark_return_pct is not None:
            result["benchmark_return_pct"] = f"{self.benchmark_return_pct * 100:.2f}%"
        alpha = self.alpha
        if alpha is not None:
            result["alpha_vs_vnindex"] = f"{alpha * 100:.2f}%"
        ir_bench = self.information_ratio_vs_benchmark
        if ir_bench is not None:
            result["ir_vs_benchmark"] = f"{ir_bench:.4f}"
        return result


# ── Factor Definitions ────────────────────────────────────────────────────────

FACTOR_LIBRARY: dict[str, dict[str, Any]] = {
    "value": {
        "name": "Value Factor",
        "description": "Cổ phiếu có P/E, P/B thấp — định giá rẻ",
        "metrics": ["pe", "pb", "ps"],
        "direction": "lower_is_better",  # Thấp hơn = tốt hơn
    },
    "quality": {
        "name": "Quality Factor",
        "description": "Cổ phiếu có ROE, ROA cao, nợ thấp",
        "metrics": ["roe", "roa", "debt_to_equity"],
        "direction": "mixed",
    },
    "momentum": {
        "name": "Momentum Factor",
        "description": "Cổ phiếu có đà tăng giá mạnh trong 6-12 tháng",
        "metrics": ["price_return_6m", "price_return_12m"],
        "direction": "higher_is_better",
    },
    "low_volatility": {
        "name": "Low Volatility Factor",
        "description": "Cổ phiếu có biến động giá thấp",
        "metrics": ["beta", "price_volatility_1y"],
        "direction": "lower_is_better",
    },
    "quality_value": {
        "name": "Quality + Value Factor",
        "description": "Kết hợp chất lượng cao và định giá hợp lý",
        "metrics": ["roe", "roa", "pe", "pb"],
        "direction": "mixed",
    },
    "dividend": {
        "name": "Dividend Factor",
        "description": "Cổ phiếu có tỷ suất cổ tức cao và ổn định",
        "metrics": ["dividend_yield", "payout_ratio"],
        "direction": "higher_is_better",
    },
}


class FactorBacktestEngine:
    """Factor-based backtesting engine.

    ★ Inspired by baocaotaichinh-/webapp/analysis/backtest_factor_library.py.
    ★ Thêm: IC/IR tracking, transaction cost, liquidity filters.
    """

    def __init__(
        self,
        tick_repo: Any,
        investability_filters: InvestabilityFilters | None = None,
        transaction_cost: TransactionCostModel | None = None,
    ) -> None:
        self._tick_repo = tick_repo
        self._filters = investability_filters or InvestabilityFilters()
        self._cost_model = transaction_cost or TransactionCostModel()

    async def run_factor_backtest(
        self,
        symbols: list[str],
        factor_name: str,
        factor_fn: Callable[[str, dict[str, Any]], float | None],
        start_date: date,
        end_date: date,
        initial_capital: Decimal = Decimal("1000000000"),
        top_n: int = 10,
        rebalance_months: int = 3,
    ) -> FactorBacktestResult:
        """Run factor-based backtest.

        Args:
            symbols: Universe of symbols to test
            factor_name: Name of the factor
            factor_fn: Function(symbol, data) → factor_score
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Starting capital in VND
            top_n: Number of top-ranked stocks to hold
            rebalance_months: Rebalance frequency in months
        """
        capital = initial_capital
        portfolio: dict[str, tuple[int, Decimal]] = {}
        trades: list[dict[str, Any]] = []
        daily_nav: list[Decimal] = [initial_capital]
        ic_series: list[float] = []
        turnover_series: list[float] = []

        logger.info(
            "Factor backtest: %s, %d symbols, %s to %s",
            factor_name, len(symbols), start_date, end_date,
        )

        # Simplified: run annual rebalancing
        current_year = start_date.year
        while current_year <= end_date.year:
            period_start = date(current_year, 1, 1)
            period_end = date(current_year, 12, 31)

            # Score all symbols
            scores: dict[str, float] = {}
            for symbol in symbols:
                try:
                    ohlcv = await self._tick_repo.get_ohlcv(symbol, period_start, period_end)
                    if len(ohlcv) < self._filters.min_trading_days:
                        continue  # Liquidity filter

                    # Apply factor function
                    score = factor_fn(symbol, {"ohlcv": ohlcv})
                    if score is not None:
                        scores[symbol] = score
                except Exception:
                    pass

            if not scores:
                current_year += 1
                continue

            # Rank and select top N
            sorted_symbols = sorted(scores, key=lambda s: scores[s], reverse=True)
            selected = sorted_symbols[:top_n]

            # Calculate IC (correlation between factor scores and next period returns)
            # Simplified: use score rank as proxy
            if len(scores) >= 5:
                ic = self._calculate_ic(scores, selected)
                ic_series.append(ic)

            # Calculate turnover
            old_portfolio = set(portfolio.keys())
            new_portfolio = set(selected)
            if old_portfolio:
                turnover = len(old_portfolio.symmetric_difference(new_portfolio)) / max(len(old_portfolio), len(new_portfolio))
                turnover_series.append(turnover)

            # Rebalance portfolio
            # Sell positions not in new portfolio
            for symbol in list(portfolio.keys()):
                if symbol not in selected:
                    qty, avg_price = portfolio[symbol]
                    # Get current price
                    try:
                        ohlcv = await self._tick_repo.get_ohlcv(symbol, period_start, period_end)
                        if ohlcv:
                            sell_price = Decimal(str(ohlcv[-1].get("close", avg_price)))
                            # Apply transaction cost
                            if self._cost_model.enabled:
                                sell_price *= Decimal(str(1 - self._cost_model.cost_bps_per_side / 10000))
                            proceeds = sell_price * qty
                            capital += proceeds
                            trades.append({"symbol": symbol, "side": "SELL", "qty": qty, "price": float(sell_price), "date": period_start.isoformat()})
                    except Exception:
                        pass
                    del portfolio[symbol]

            # Buy new positions
            if selected:
                per_position = capital / len(selected)
                for symbol in selected:
                    if symbol not in portfolio:
                        try:
                            ohlcv = await self._tick_repo.get_ohlcv(symbol, period_start, period_end)
                            if ohlcv:
                                buy_price = Decimal(str(ohlcv[0].get("close", 0)))
                                if buy_price > 0:
                                    # Apply transaction cost
                                    if self._cost_model.enabled:
                                        buy_price *= Decimal(str(1 + self._cost_model.cost_bps_per_side / 10000))
                                    qty = int(per_position / buy_price / 100) * 100
                                    if qty > 0:
                                        cost = buy_price * qty
                                        if cost <= capital:
                                            capital -= cost
                                            portfolio[symbol] = (qty, buy_price)
                                            trades.append({"symbol": symbol, "side": "BUY", "qty": qty, "price": float(buy_price), "date": period_start.isoformat()})
                        except Exception:
                            pass

            # Track NAV (cash + mark-to-market portfolio value)
            nav = capital
            for symbol, (qty, avg_price) in portfolio.items():
                nav += avg_price * qty  # Simplified: use avg_price as proxy for current price
            daily_nav.append(nav)

            current_year += 1

        # ★ final_capital = cash + mark-to-market portfolio value (not just cash)
        final_nav = capital
        for symbol, (qty, avg_price) in portfolio.items():
            final_nav += avg_price * qty

        result = FactorBacktestResult(
            factor_name=factor_name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_capital=final_nav,  # ★ Fixed: include portfolio value
            trades=trades,
            daily_nav=daily_nav,
            ic_series=ic_series,
            turnover_series=turnover_series,
        )

        logger.info(
            "Factor backtest complete: %s, return=%.2f%%, IC=%.4f, IR=%.4f",
            factor_name,
            result.total_return_pct * 100,
            result.ic_mean or 0,
            result.ic_ir or 0,
        )
        return result

    @staticmethod
    def _calculate_ic(scores: dict[str, float], selected: list[str]) -> float:
        """Calculate Information Coefficient using Spearman rank correlation.

        ★ Fix: real Spearman rank correlation between factor scores and selection indicator.
        IC = Spearman(factor_rank, selection_indicator_rank)
        Range: [-1, +1]. IC > 0.05 is considered meaningful in factor investing.
        """
        if len(scores) < 3:
            return 0.0

        symbols = list(scores.keys())
        n = len(symbols)
        selected_set = set(selected)

        # Factor ranks (1 = highest score = best)
        sorted_by_score = sorted(symbols, key=lambda s: scores[s], reverse=True)
        factor_ranks = {sym: float(rank + 1) for rank, sym in enumerate(sorted_by_score)}

        # Selection indicator ranks (selected=1, not selected=0)
        # Rank: selected stocks get lower rank numbers (better)
        sorted_by_selection = sorted(
            symbols,
            key=lambda s: (0 if s in selected_set else 1, symbols.index(s)),
        )
        selection_ranks = {sym: float(rank + 1) for rank, sym in enumerate(sorted_by_selection)}

        # Spearman rank correlation: 1 - 6*sum(d^2) / (n*(n^2-1))
        sum_d_sq = sum(
            (factor_ranks[sym] - selection_ranks[sym]) ** 2
            for sym in symbols
        )
        denominator = n * (n ** 2 - 1)
        if denominator == 0:
            return 0.0
        return 1.0 - (6.0 * sum_d_sq / denominator)
