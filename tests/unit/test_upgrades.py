"""Tests for all 10 upgrades from the roadmap.

★ TEST-01: EarlyWarning + RiskAgent integration (block critical)
★ TEST-02: PaperOrderMatcher VN lot size + price band
★ TEST-03: SSIBrokerClient._parse_order() with invalid OrderType
★ TEST-04: FundamentalAgent with financial_data_port
★ TEST-06: FactorBacktestResult alpha + IR vs benchmark
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.early_warning import calculate_early_warning
from agents.factor_backtest import FactorBacktestResult
from adapters.paper_trading.order_matcher import (
    PaperOrderMatcher,
    PriceData,
    VN_LOT_SIZE,
)
from core.entities.order import Order, OrderSide, OrderStatus, OrderType
from core.value_objects import Price, Quantity, Symbol


# ── TEST-01: EarlyWarning + RiskAgent Integration ─────────────────────────────

class TestEarlyWarningRiskAgentIntegration:
    """Tests for EarlyWarning integration with RiskAgent."""

    @pytest.mark.asyncio
    async def test_risk_agent_blocks_critical_early_warning(self) -> None:
        """RiskAgent should block trade when early_warning_results has critical level."""
        from agents.risk_agent import RiskAgent
        from agents.state import AgentPhase, AgentState, TechnicalScore, SignalAction
        from core.value_objects import Symbol

        # Mock tick_repo and risk_limits
        tick_repo = MagicMock()
        tick_repo.calculate_var_historical = MagicMock(return_value=0.02)
        tick_repo.get_latest_price = MagicMock(return_value=100000)
        risk_limits = MagicMock()
        risk_limits.kill_switch_active = False
        risk_limits.max_position_pct = Decimal("0.20")

        agent = RiskAgent(tick_repo=tick_repo, risk_limits=risk_limits)

        symbol = Symbol("HPG")
        state: AgentState = {
            "top_candidates": [symbol],
            "technical_scores": [
                TechnicalScore(
                    symbol=symbol,
                    rsi_14=45.0,
                    macd_signal="bullish",
                    bb_position="inside",
                    trend_ma="bullish",
                    composite_score=7.0,
                    recommended_action=SignalAction.BUY,
                    analysis_timestamp=datetime.now(),
                )
            ],
            "current_nav": Decimal("1000000000"),
            "current_positions": {},
            "purchasing_power": Decimal("100000000"),
            # ★ Critical early warning for HPG
            "early_warning_results": {
                "HPG": {
                    "risk_score": 75.0,
                    "risk_level": "critical",
                    "alerts": ["ROE âm", "D/E rất cao", "Dòng tiền âm"],
                    "positive_signals": [],
                    "recommendation": "Không nên đầu tư",
                    "summary": "Risk Score: 75/100 (CRITICAL)",
                }
            },
        }

        result = await agent.run(state)
        # Should be blocked
        assert len(result["approved_trades"]) == 0
        assert len(result["risk_assessments"]) == 1
        assessment = result["risk_assessments"][0]
        assert assessment.approved is False
        assert "CRITICAL" in (assessment.rejection_reason or "").upper() or \
               "critical" in (assessment.rejection_reason or "").lower() or \
               "Early Warning" in (assessment.rejection_reason or "")

    @pytest.mark.asyncio
    async def test_risk_agent_allows_low_early_warning(self) -> None:
        """RiskAgent should NOT block trade when early_warning_results has low level."""
        from agents.risk_agent import RiskAgent
        from agents.state import AgentState, TechnicalScore, SignalAction
        from core.value_objects import Symbol

        tick_repo = MagicMock()
        tick_repo.calculate_var_historical = MagicMock(return_value=0.02)
        tick_repo.get_latest_price = MagicMock(return_value=100000)
        risk_limits = MagicMock()
        risk_limits.kill_switch_active = False
        risk_limits.max_position_pct = Decimal("0.20")

        agent = RiskAgent(tick_repo=tick_repo, risk_limits=risk_limits)
        symbol = Symbol("FPT")

        state: AgentState = {
            "top_candidates": [symbol],
            "technical_scores": [
                TechnicalScore(
                    symbol=symbol,
                    rsi_14=55.0,
                    macd_signal="bullish",
                    bb_position="inside",
                    trend_ma="bullish",
                    composite_score=8.0,
                    recommended_action=SignalAction.BUY,
                    analysis_timestamp=datetime.now(),
                )
            ],
            "current_nav": Decimal("1000000000"),
            "current_positions": {},
            "purchasing_power": Decimal("100000000"),
            # ★ Low early warning for FPT
            "early_warning_results": {
                "FPT": {
                    "risk_score": 10.0,
                    "risk_level": "low",
                    "alerts": [],
                    "positive_signals": ["ROE tốt", "Dòng tiền dương"],
                    "recommendation": "Sức khỏe tài chính tốt",
                    "summary": "Risk Score: 10/100 (LOW)",
                }
            },
        }

        result = await agent.run(state)
        # Should be approved (not blocked by early warning)
        assert len(result["approved_trades"]) == 1


# ── TEST-02: PaperOrderMatcher VN Lot Size + Price Band ──────────────────────

class TestPaperOrderMatcherVNRules:
    """Tests for VN-specific rules in PaperOrderMatcher."""

    def _make_order(self, quantity: int, price: Decimal = Decimal("100000")) -> Order:
        now = datetime.now()
        return Order(
            order_id="ORD-001",
            symbol=Symbol("FPT"),
            side=OrderSide.BUY,
            order_type=OrderType.LO,
            quantity=Quantity(quantity),
            price=Price(price),
            ceiling_price=Price(Decimal("107000")),
            floor_price=Price(Decimal("93000")),
            status=OrderStatus.CREATED,
            filled_quantity=Quantity(0),
            avg_fill_price=Price(Decimal("0")),
            broker_order_id=None,
            rejection_reason=None,
            idempotency_key="IDEM-001",
            created_at=now,
            updated_at=now,
        )

    def test_lot_size_100_accepted(self) -> None:
        matcher = PaperOrderMatcher()
        matcher.initialize_portfolio("p1", Decimal("100000000"))
        order = self._make_order(quantity=100)
        result = matcher.add_order(order, "p1")
        assert result is True

    def test_lot_size_500_accepted(self) -> None:
        matcher = PaperOrderMatcher()
        matcher.initialize_portfolio("p1", Decimal("100000000"))
        order = self._make_order(quantity=500)
        result = matcher.add_order(order, "p1")
        assert result is True

    def test_lot_size_150_rejected(self) -> None:
        """150 is not a multiple of 100 — should be rejected."""
        matcher = PaperOrderMatcher()
        matcher.initialize_portfolio("p1", Decimal("100000000"))
        order = self._make_order(quantity=150)
        result = matcher.add_order(order, "p1")
        assert result is False

    def test_lot_size_1_rejected(self) -> None:
        matcher = PaperOrderMatcher()
        matcher.initialize_portfolio("p1", Decimal("100000000"))
        order = self._make_order(quantity=1)
        result = matcher.add_order(order, "p1")
        assert result is False

    def test_price_within_band_accepted(self) -> None:
        """Price within ±7% of reference should be accepted."""
        matcher = PaperOrderMatcher()
        matcher.initialize_portfolio("p1", Decimal("100000000"))
        ref_price = Decimal("100000")
        # 103000 is within ±7% of 100000
        order = self._make_order(quantity=100, price=Decimal("103000"))
        result = matcher.add_order(order, "p1", reference_price=ref_price, exchange="HOSE")
        assert result is True

    def test_price_outside_band_rejected(self) -> None:
        """Price outside ±7% of reference should be rejected."""
        matcher = PaperOrderMatcher()
        matcher.initialize_portfolio("p1", Decimal("100000000"))
        ref_price = Decimal("100000")
        # 110000 is outside ±7% of 100000 (ceiling = 107000)
        order = self._make_order(quantity=100, price=Decimal("110000"))
        result = matcher.add_order(order, "p1", reference_price=ref_price, exchange="HOSE")
        assert result is False

    def test_hnx_wider_band_accepted(self) -> None:
        """HNX has ±10% band — 108000 should be accepted."""
        matcher = PaperOrderMatcher()
        matcher.initialize_portfolio("p1", Decimal("100000000"))
        ref_price = Decimal("100000")
        # 108000 is within ±10% of 100000
        order = self._make_order(quantity=100, price=Decimal("108000"))
        result = matcher.add_order(order, "p1", reference_price=ref_price, exchange="HNX")
        assert result is True

    def test_no_reference_price_skips_band_check(self) -> None:
        """Without reference_price, price band check is skipped."""
        matcher = PaperOrderMatcher()
        matcher.initialize_portfolio("p1", Decimal("100000000"))
        # Even extreme price should be accepted without reference
        order = self._make_order(quantity=100, price=Decimal("200000"))
        result = matcher.add_order(order, "p1")  # No reference_price
        assert result is True


# ── TEST-03: SSIBrokerClient._parse_order() with invalid OrderType ────────────

class TestSSIBrokerParseOrder:
    """Tests for SSIBrokerClient._parse_order() graceful handling."""

    def _make_broker(self) -> object:
        """Create SSIBrokerClient with mocked dependencies."""
        from adapters.ssi.broker import SSIBrokerClient
        auth = MagicMock()
        return SSIBrokerClient(auth_client=auth, account_no="TEST001")

    def test_parse_order_valid_type(self) -> None:
        from adapters.ssi.broker import SSIBrokerClient
        auth = MagicMock()
        broker = SSIBrokerClient(auth_client=auth, account_no="TEST001")

        data = {
            "requestID": "REQ-001",
            "instrumentID": "FPT",
            "buySell": "B",
            "orderType": "LO",
            "orderQty": 1000,
            "price": "98500",
            "ceilingPrice": "105400",
            "floorPrice": "91600",
            "orderStatus": "New",
            "filledQty": 0,
            "avgPrice": "0",
            "orderID": "BROKER-001",
        }
        order = broker._parse_order(data)
        assert order.order_type == OrderType.LO
        assert str(order.symbol) == "FPT"

    def test_parse_order_invalid_type_defaults_to_lo(self) -> None:
        """Invalid OrderType should default to LO, not raise ValueError."""
        from adapters.ssi.broker import SSIBrokerClient
        auth = MagicMock()
        broker = SSIBrokerClient(auth_client=auth, account_no="TEST001")

        data = {
            "requestID": "REQ-002",
            "instrumentID": "VCB",
            "buySell": "S",
            "orderType": "UNKNOWN_TYPE",  # ★ Invalid type
            "orderQty": 500,
            "price": "85000",
            "ceilingPrice": "90000",
            "floorPrice": "80000",
            "orderStatus": "Filled",
            "filledQty": 500,
            "avgPrice": "85000",
            "orderID": "BROKER-002",
        }
        # Should NOT raise ValueError
        order = broker._parse_order(data)
        assert order.order_type == OrderType.LO  # Defaults to LO
        assert order.status == OrderStatus.MATCHED

    def test_parse_order_sell_side(self) -> None:
        from adapters.ssi.broker import SSIBrokerClient
        auth = MagicMock()
        broker = SSIBrokerClient(auth_client=auth, account_no="TEST001")

        data = {
            "requestID": "REQ-003",
            "instrumentID": "HPG",
            "buySell": "S",
            "orderType": "ATC",
            "orderQty": 200,
            "price": "25000",
            "ceilingPrice": "27000",
            "floorPrice": "23000",
            "orderStatus": "Pending",
            "filledQty": 0,
            "avgPrice": "0",
            "orderID": "BROKER-003",
        }
        order = broker._parse_order(data)
        assert order.side == OrderSide.SELL
        assert order.order_type == OrderType.ATC


# ── TEST-06: FactorBacktestResult Alpha + IR vs Benchmark ────────────────────

class TestFactorBacktestBenchmark:
    """Tests for FactorBacktestResult benchmark comparison."""

    def _make_result(
        self,
        initial: Decimal = Decimal("1000000"),
        final: Decimal = Decimal("1200000"),
        benchmark_return: float | None = None,
    ) -> FactorBacktestResult:
        return FactorBacktestResult(
            factor_name="value",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            initial_capital=initial,
            final_capital=final,
            benchmark_return_pct=benchmark_return,
        )

    def test_total_return_pct(self) -> None:
        result = self._make_result(
            initial=Decimal("1000000"),
            final=Decimal("1200000"),
        )
        assert result.total_return_pct == pytest.approx(0.20)

    def test_alpha_positive(self) -> None:
        """Portfolio +20%, benchmark +10% → alpha = +10%."""
        result = self._make_result(
            initial=Decimal("1000000"),
            final=Decimal("1200000"),
            benchmark_return=0.10,
        )
        assert result.alpha == pytest.approx(0.10)

    def test_alpha_negative(self) -> None:
        """Portfolio +5%, benchmark +15% → alpha = -10%."""
        result = self._make_result(
            initial=Decimal("1000000"),
            final=Decimal("1050000"),
            benchmark_return=0.15,
        )
        assert result.alpha == pytest.approx(-0.10, abs=0.01)

    def test_alpha_none_without_benchmark(self) -> None:
        result = self._make_result()
        assert result.alpha is None

    def test_ir_vs_benchmark_with_data(self) -> None:
        """IR vs benchmark should be calculable with NAV series."""
        result = FactorBacktestResult(
            factor_name="quality",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            initial_capital=Decimal("1000000"),
            final_capital=Decimal("1100000"),
            benchmark_return_pct=0.08,
            daily_nav=[Decimal(str(1000000 + i * 1000)) for i in range(10)],
            benchmark_nav=[Decimal(str(1000000 + i * 800)) for i in range(10)],
        )
        ir = result.information_ratio_vs_benchmark
        # IR should be calculable (not None)
        assert ir is not None

    def test_ir_vs_benchmark_none_without_nav(self) -> None:
        result = self._make_result(benchmark_return=0.10)
        assert result.information_ratio_vs_benchmark is None

    def test_to_dict_includes_benchmark_metrics(self) -> None:
        result = self._make_result(
            initial=Decimal("1000000"),
            final=Decimal("1200000"),
            benchmark_return=0.10,
        )
        d = result.to_dict()
        assert "benchmark_return_pct" in d
        assert "alpha_vs_vnindex" in d
        assert "10.00%" in d["alpha_vs_vnindex"]


# ── TEST-04: FundamentalAgent with financial_data_port ────────────────────────

class TestFundamentalAgentFinancialData:
    """Tests for FundamentalAgent with financial_data_port integration."""

    @pytest.mark.asyncio
    async def test_fundamental_agent_runs_early_warning(self) -> None:
        """FundamentalAgent should run early warning when financial_data_port provided."""
        from agents.fundamental_agent import FundamentalAgent
        from agents.prompt_builder import FinancialPromptBuilder
        from agents.state import AgentState, ScreenerResult, TechnicalScore, SignalAction
        from core.value_objects import Symbol

        # Mock dependencies
        engine = MagicMock()
        engine.generate = AsyncMock(return_value="FPT analysis: BUY")

        prompt_builder = MagicMock(spec=FinancialPromptBuilder)
        prompt_builder.build_analysis_prompt = MagicMock(
            return_value=("test prompt", MagicMock())
        )

        news_port = MagicMock()
        news_port.get_headlines = MagicMock(return_value=[])

        # Financial data port with VCB-like data
        financial_data_port = MagicMock()
        financial_data_port.get_financial_data = MagicMock(return_value={
            "financial_ratios": {
                "roe": 0.20,
                "debt_to_equity": 0.5,
                "current_ratio": 2.0,
                "net_margin": 0.15,
            },
            "balance_sheet": {"total_assets": 1000000, "total_equity": 500000},
            "income_statement": {"net_income": 100000, "revenue": 666667},
            "cash_flow": {"operating_cash_flow": 120000},
            "icb_name": "Công nghệ thông tin",
            "icb_code": "9500",
        })

        agent = FundamentalAgent(
            engine=engine,
            prompt_builder=prompt_builder,
            news_port=news_port,
            financial_data_port=financial_data_port,
        )

        symbol = Symbol("FPT")
        state: AgentState = {
            "watchlist": [
                ScreenerResult(
                    symbol=symbol,
                    eps_growth=0.25,
                    pe_ratio=15.0,
                    volume_spike=False,
                    passed_at=datetime.now(),
                )
            ],
            "technical_scores": [
                TechnicalScore(
                    symbol=symbol,
                    rsi_14=55.0,
                    macd_signal="bullish",
                    bb_position="inside",
                    trend_ma="bullish",
                    composite_score=7.5,
                    recommended_action=SignalAction.BUY,
                    analysis_timestamp=datetime.now(),
                )
            ],
        }

        result = await agent.run(state)

        # Should have insights
        assert "ai_insights" in result
        assert str(symbol) in result["ai_insights"]

        # Should have early warning results
        assert "early_warning_results" in result
        assert str(symbol) in result["early_warning_results"]
        ew = result["early_warning_results"][str(symbol)]
        assert "risk_score" in ew
        assert "risk_level" in ew
        assert ew["risk_level"] == "low"  # Healthy company

        # Should have industry analysis results
        assert "industry_analysis_results" in result
        assert str(symbol) in result["industry_analysis_results"]
        ia = result["industry_analysis_results"][str(symbol)]
        assert ia["industry_type"] == "technology"

    @pytest.mark.asyncio
    async def test_fundamental_agent_without_financial_data_port(self) -> None:
        """FundamentalAgent should work without financial_data_port (graceful degradation)."""
        from agents.fundamental_agent import FundamentalAgent
        from agents.prompt_builder import FinancialPromptBuilder
        from agents.state import AgentState, ScreenerResult, TechnicalScore, SignalAction
        from core.value_objects import Symbol

        engine = MagicMock()
        engine.generate = AsyncMock(return_value="Analysis")
        prompt_builder = MagicMock(spec=FinancialPromptBuilder)
        prompt_builder.build_analysis_prompt = MagicMock(
            return_value=("prompt", MagicMock())
        )
        news_port = MagicMock()
        news_port.get_headlines = MagicMock(return_value=[])

        # No financial_data_port
        agent = FundamentalAgent(
            engine=engine,
            prompt_builder=prompt_builder,
            news_port=news_port,
        )

        symbol = Symbol("VCB")
        state: AgentState = {
            "watchlist": [
                ScreenerResult(
                    symbol=symbol,
                    eps_growth=0.10,
                    pe_ratio=12.0,
                    volume_spike=False,
                    passed_at=datetime.now(),
                )
            ],
            "technical_scores": [],
        }

        result = await agent.run(state)
        # Should still produce insights
        assert "ai_insights" in result
        # Early warning should be empty (no data)
        assert result.get("early_warning_results", {}) == {}
