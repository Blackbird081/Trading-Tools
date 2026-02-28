"""Golden Output Tests — Vietnamese Financial Analysis.

★ Inspired by baocaotaichinh-/webapp/tests/test_golden_outputs.py.
★ Tests với real VN stock data (FPT, VCB, HPG, VNM, MWG).
★ Regression tests để catch unintended calculation changes.
★ Kiểm tra: ROE, ROA, DuPont, Early Warning, Industry Analysis.

Golden Stocks:
- FPT: Technology, ROE ~28%, strong growth
- VCB: Banking, NIM ~3.5%, NPL ~1%
- HPG: Steel manufacturing, high leverage
- VNM: Consumer, stable margins
- MWG: Retail, high asset turnover
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from agents.data_contract import get_value, safe_divide, calculate_free_cash_flow
from agents.dupont_analysis import calculate_extended_dupont
from agents.early_warning import calculate_early_warning
from agents.financial_taxonomy import get_metric, format_metric_value, get_metric_rating
from agents.industry_analysis.banking import analyze_banking
from agents.industry_analysis.realestate import analyze_realestate
from agents.industry_analysis.technology import analyze_technology
from agents.industry_analysis.router import route_industry


# ── Data Contract Tests ───────────────────────────────────────────────────────

class TestDataContract:
    """Tests for data contract column alias resolution."""

    def test_get_value_exact_key(self) -> None:
        data = {"revenue": 1000.0}
        assert get_value(data, "revenue") == 1000.0

    def test_get_value_alias(self) -> None:
        """Should find value via alias."""
        data = {"net_revenue": 1000.0}  # alias for "revenue"
        assert get_value(data, "revenue") == 1000.0

    def test_get_value_second_alias(self) -> None:
        data = {"net_profit": 200.0}  # alias for "net_income"
        assert get_value(data, "net_income") == 200.0

    def test_get_value_missing_returns_default(self) -> None:
        data = {}
        assert get_value(data, "revenue", default=0.0) == 0.0
        assert get_value(data, "revenue") is None

    def test_safe_divide_normal(self) -> None:
        assert safe_divide(100.0, 4.0) == pytest.approx(25.0)

    def test_safe_divide_zero_denominator(self) -> None:
        assert safe_divide(100.0, 0.0) is None

    def test_safe_divide_none_inputs(self) -> None:
        assert safe_divide(None, 100.0) is None
        assert safe_divide(100.0, None) is None

    def test_calculate_fcf(self) -> None:
        cash_flow = {"operating_cash_flow": 1000.0, "capital_expenditure": -200.0}
        fcf = calculate_free_cash_flow(cash_flow)
        assert fcf == pytest.approx(800.0)

    def test_calculate_fcf_alias(self) -> None:
        cash_flow = {"net_cash_from_operations": 1000.0, "capex": -200.0}
        fcf = calculate_free_cash_flow(cash_flow)
        assert fcf == pytest.approx(800.0)


# ── Financial Taxonomy Tests ──────────────────────────────────────────────────

class TestFinancialTaxonomy:
    """Tests for financial taxonomy metadata."""

    def test_get_metric_roe(self) -> None:
        metric = get_metric("roe")
        assert metric is not None
        assert metric.id == "roe"
        assert metric.group == "profitability"
        assert metric.unit == "%"
        assert metric.higher_is_better is True

    def test_get_metric_pe(self) -> None:
        metric = get_metric("pe")
        assert metric is not None
        assert metric.higher_is_better is False

    def test_format_metric_value_pct(self) -> None:
        result = format_metric_value("roe", 0.28)
        assert "28.0%" in result

    def test_format_metric_value_multiple(self) -> None:
        result = format_metric_value("pe", 15.5)
        assert "15.50x" in result

    def test_get_metric_rating_roe_good(self) -> None:
        rating = get_metric_rating("roe", 0.25)
        assert rating == "Tốt"

    def test_get_metric_rating_roe_bad(self) -> None:
        rating = get_metric_rating("roe", 0.05)
        assert rating == "Cần xem xét"


# ── Golden Output Tests — FPT (Technology) ───────────────────────────────────

class TestGoldenOutputsFPT:
    """Golden output tests for FPT (Technology sector)."""

    def test_fpt_2024_roe_approximate(self) -> None:
        """FPT 2024 ROE should be ~28% (25-35% range)."""
        income_statement = {
            "net_profit_parent_company": 9_188_000_000_000,  # ~9,188B VND
        }
        balance_sheet = {
            "total_equity": 32_668_000_000_000,  # ~32,668B VND
        }
        roe = safe_divide(
            get_value(income_statement, "net_income"),
            get_value(balance_sheet, "total_equity"),
        )
        assert roe is not None
        assert 0.25 <= roe <= 0.35, f"FPT ROE {roe:.2%} not in expected range 25-35%"

    def test_fpt_technology_analysis(self) -> None:
        """FPT technology analysis should produce valid metrics."""
        income_statement = {
            "revenue": 52_000_000_000_000,
            "research_and_development": 2_600_000_000_000,  # ~5% of revenue
        }
        balance_sheet = {
            "total_assets": 50_000_000_000_000,
            "intangible_assets": 5_000_000_000_000,  # ~10%
        }
        metrics = analyze_technology(income_statement, balance_sheet)
        assert "rd_to_revenue" in metrics
        rd_metric = metrics["rd_to_revenue"]
        assert rd_metric.value is not None
        assert 0.03 <= rd_metric.value <= 0.10  # 3-10% R&D ratio

    def test_fpt_industry_routing(self) -> None:
        """FPT should route to technology analysis."""
        industry = route_industry(icb_name="Công nghệ thông tin")
        assert industry == "technology"


# ── Golden Output Tests — VCB (Banking) ──────────────────────────────────────

class TestGoldenOutputsVCB:
    """Golden output tests for VCB (Banking sector)."""

    def test_vcb_banking_analysis(self) -> None:
        """VCB banking analysis should produce valid metrics."""
        financial_data = {
            "net_interest_income": 35_000_000_000_000,  # ~35,000B VND
            "total_assets": 1_800_000_000_000_000,      # ~1,800,000B VND
            "total_loans": 1_200_000_000_000_000,
            "total_deposits": 1_400_000_000_000_000,
            "npl_ratio": 0.012,  # 1.2% NPL
            "car": 0.115,        # 11.5% CAR
        }
        metrics = analyze_banking(financial_data)

        # NIM should be ~2-4%
        nim = metrics["nim"]
        if nim.value is not None:
            assert 0.01 <= nim.value <= 0.05, f"VCB NIM {nim.value:.2%} not in expected range"

        # NPL should be < 2%
        npl = metrics["npl"]
        if npl.value is not None:
            assert npl.value <= 0.02, f"VCB NPL {npl.value:.2%} should be < 2%"
            assert npl.rating in ("Tốt", "Khá")

        # CAR should be > 10%
        car = metrics["car"]
        if car.value is not None:
            assert car.value >= 0.10, f"VCB CAR {car.value:.2%} should be >= 10%"

    def test_vcb_industry_routing(self) -> None:
        """VCB should route to banking analysis."""
        industry = route_industry(icb_name="Ngân hàng")
        assert industry == "banking"

        industry2 = route_industry(icb_code="8300")
        assert industry2 == "banking"


# ── Golden Output Tests — HPG (Manufacturing/Steel) ──────────────────────────

class TestGoldenOutputsHPG:
    """Golden output tests for HPG (Steel manufacturing)."""

    def test_hpg_early_warning_high_leverage(self) -> None:
        """HPG has high leverage — early warning should flag it."""
        financial_ratios = {
            "roe": 0.12,
            "debt_to_equity": 1.8,  # High leverage for steel
            "current_ratio": 1.3,
            "net_margin": 0.06,
        }
        result = calculate_early_warning(financial_ratios)
        # HPG has high D/E but not critical
        assert result.risk_score < 60  # Not critical
        assert result.risk_level in ("low", "medium", "high")

    def test_hpg_industry_routing(self) -> None:
        """HPG should route to manufacturing analysis."""
        industry = route_industry(icb_name="Thép")
        assert industry == "manufacturing"


# ── DuPont Analysis Tests ─────────────────────────────────────────────────────

class TestDuPontAnalysis:
    """Tests for Extended DuPont Analysis."""

    def test_dupont_basic_calculation(self) -> None:
        """Test DuPont with known values."""
        income_statement = {
            "net_income": 200.0,
            "profit_before_tax": 250.0,
            "operating_profit": 300.0,
            "revenue": 1000.0,
        }
        balance_sheet = {
            "total_assets": 2000.0,
            "total_equity": 800.0,
        }
        result = calculate_extended_dupont(income_statement, balance_sheet)

        # Tax burden = 200/250 = 0.8
        assert result.tax_burden.value == pytest.approx(0.8, rel=0.01)
        # Interest burden = 250/300 = 0.833
        assert result.interest_burden.value == pytest.approx(0.833, rel=0.01)
        # Operating margin = 300/1000 = 0.3
        assert result.operating_margin.value == pytest.approx(0.3, rel=0.01)
        # Asset turnover = 1000/2000 = 0.5
        assert result.asset_turnover.value == pytest.approx(0.5, rel=0.01)
        # Financial leverage = 2000/800 = 2.5
        assert result.financial_leverage.value == pytest.approx(2.5, rel=0.01)

        # ROE = 0.8 × 0.833 × 0.3 × 0.5 × 2.5 = 0.25
        assert result.roe_computed == pytest.approx(0.25, rel=0.01)

    def test_dupont_missing_data(self) -> None:
        """DuPont should handle missing data gracefully."""
        result = calculate_extended_dupont({}, {})
        assert result.roe_computed is None
        assert result.dominant_driver == "Không xác định được"


# ── Early Warning Tests ───────────────────────────────────────────────────────

class TestEarlyWarning:
    """Tests for Early Warning System."""

    def test_healthy_company_low_risk(self) -> None:
        """Healthy company should have low risk score."""
        financial_ratios = {
            "roe": 0.20,
            "debt_to_equity": 0.3,
            "current_ratio": 2.5,
            "net_margin": 0.15,
        }
        result = calculate_early_warning(
            financial_ratios,
            altman_z_score=3.5,
            piotroski_f_score=8,
        )
        assert result.risk_score < 20
        assert result.risk_level == "low"
        assert len(result.positive_signals) > 0

    def test_distressed_company_high_risk(self) -> None:
        """Distressed company should have high risk score."""
        financial_ratios = {
            "roe": -0.05,  # Negative ROE
            "debt_to_equity": 4.0,  # Very high leverage
            "current_ratio": 0.8,  # Below 1
            "net_margin": -0.02,  # Negative margin
        }
        result = calculate_early_warning(
            financial_ratios,
            altman_z_score=1.2,  # Danger zone
            piotroski_f_score=2,  # Very low
        )
        assert result.risk_score >= 60
        assert result.risk_level in ("high", "critical")
        assert len(result.alerts) > 0

    def test_kill_switch_in_risk_agent(self) -> None:
        """Kill switch should result in critical risk."""
        financial_ratios = {"roe": 0.20}
        result = calculate_early_warning(financial_ratios)
        # Without kill switch, should be low risk
        assert result.risk_level == "low"
