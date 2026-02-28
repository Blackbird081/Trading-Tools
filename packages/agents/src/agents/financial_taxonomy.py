"""Financial Taxonomy — metadata cho chỉ số tài chính Việt Nam.

★ Inspired by baocaotaichinh-/stock_database/financial_taxonomy.py.
★ Chuẩn hóa tên, đơn vị, mô tả cho tất cả chỉ số tài chính.
★ Hỗ trợ 24 nhóm chỉ số: market, valuation, profitability, leverage, liquidity, etc.
★ Dùng để hiển thị chỉ số trong UI và chuẩn hóa output của FundamentalAgent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FinancialMetric:
    """Metadata cho một chỉ số tài chính."""

    id: str
    group: str
    label_vi: str       # Tên tiếng Việt
    label_en: str       # Tên tiếng Anh
    unit: str           # Đơn vị (%, x, tỷ VND, etc.)
    description: str    # Mô tả ý nghĩa
    statement: str | None = None   # Nguồn: financial_ratios, balance_sheet, income_statement, cash_flow
    higher_is_better: bool | None = None  # None = depends on context


# ── Nhóm chỉ số ───────────────────────────────────────────────────────────────

METRIC_GROUPS: dict[str, dict[str, str]] = {
    "market": {"label_vi": "Thị trường", "note": "Quy mô/biến động giá/đầu vào định giá"},
    "valuation": {"label_vi": "Định giá", "note": "Bội số định giá (multiples)"},
    "profitability": {"label_vi": "Sinh lời", "note": "Biên lợi nhuận và ROE/ROA/ROIC"},
    "leverage": {"label_vi": "Đòn bẩy", "note": "Cấu trúc vốn và sức chịu nợ"},
    "liquidity": {"label_vi": "Thanh khoản", "note": "Khả năng thanh toán ngắn hạn"},
    "efficiency": {"label_vi": "Hiệu quả vận hành", "note": "Vòng quay và chu kỳ tiền mặt"},
    "payout": {"label_vi": "Cổ tức", "note": "Chính sách trả cổ tức"},
    "scale": {"label_vi": "Quy mô", "note": "Số tuyệt đối (không phải ratio)"},
    "risk": {"label_vi": "Rủi ro", "note": "Độ nhạy thị trường"},
    "growth": {"label_vi": "Tăng trưởng", "note": "Tốc độ tăng trưởng"},
    "cashflow": {"label_vi": "Dòng tiền", "note": "Chất lượng và cấu trúc dòng tiền"},
    "dupont": {"label_vi": "DuPont", "note": "Phân tích DuPont 5 thành phần"},
    "altman": {"label_vi": "Altman Z-Score", "note": "Dự báo phá sản"},
    "piotroski": {"label_vi": "Piotroski F-Score", "note": "Chất lượng tài chính 9 tiêu chí"},
    "early_warning": {"label_vi": "Cảnh báo sớm", "note": "Tín hiệu rủi ro tài chính"},
}


# ── Chỉ số tài chính ──────────────────────────────────────────────────────────

FINANCIAL_METRICS: dict[str, FinancialMetric] = {
    # ── Định giá ──────────────────────────────────────────────────────────────
    "pe": FinancialMetric(
        id="pe", group="valuation", label_vi="P/E", label_en="Price/Earnings",
        unit="x", description="Giá / Lợi nhuận mỗi cổ phiếu. P/E thấp = rẻ hơn so với lợi nhuận.",
        statement="financial_ratios", higher_is_better=False,
    ),
    "pb": FinancialMetric(
        id="pb", group="valuation", label_vi="P/B", label_en="Price/Book",
        unit="x", description="Giá / Giá trị sổ sách. P/B < 1 = giao dịch dưới book value.",
        statement="financial_ratios", higher_is_better=False,
    ),
    "ps": FinancialMetric(
        id="ps", group="valuation", label_vi="P/S", label_en="Price/Sales",
        unit="x", description="Giá / Doanh thu mỗi cổ phiếu.",
        statement="financial_ratios", higher_is_better=False,
    ),
    "ev_ebitda": FinancialMetric(
        id="ev_ebitda", group="valuation", label_vi="EV/EBITDA", label_en="EV/EBITDA",
        unit="x", description="Enterprise Value / EBITDA. Chỉ số định giá không bị ảnh hưởng bởi cấu trúc vốn.",
        statement="financial_ratios", higher_is_better=False,
    ),
    "peg": FinancialMetric(
        id="peg", group="valuation", label_vi="PEG", label_en="Price/Earnings-to-Growth",
        unit="x", description="P/E / Tốc độ tăng trưởng EPS. PEG < 1 = rẻ so với tăng trưởng.",
        statement="financial_ratios", higher_is_better=False,
    ),

    # ── Sinh lời ──────────────────────────────────────────────────────────────
    "roe": FinancialMetric(
        id="roe", group="profitability", label_vi="ROE", label_en="Return on Equity",
        unit="%", description="Lợi nhuận / Vốn chủ sở hữu. ROE ≥ 15% trong 5 năm = lợi thế cạnh tranh.",
        statement="financial_ratios", higher_is_better=True,
    ),
    "roa": FinancialMetric(
        id="roa", group="profitability", label_vi="ROA", label_en="Return on Assets",
        unit="%", description="Lợi nhuận / Tổng tài sản. Đo hiệu quả sử dụng tài sản.",
        statement="financial_ratios", higher_is_better=True,
    ),
    "roic": FinancialMetric(
        id="roic", group="profitability", label_vi="ROIC", label_en="Return on Invested Capital",
        unit="%", description="Lợi nhuận / Vốn đầu tư. ROIC > WACC = tạo giá trị.",
        statement="financial_ratios", higher_is_better=True,
    ),
    "gross_margin": FinancialMetric(
        id="gross_margin", group="profitability", label_vi="Biên lợi nhuận gộp", label_en="Gross Margin",
        unit="%", description="(Doanh thu - COGS) / Doanh thu. Biên cao = lợi thế cạnh tranh.",
        statement="income_statement", higher_is_better=True,
    ),
    "operating_margin": FinancialMetric(
        id="operating_margin", group="profitability", label_vi="Biên lợi nhuận hoạt động", label_en="Operating Margin",
        unit="%", description="EBIT / Doanh thu. Đo hiệu quả hoạt động cốt lõi.",
        statement="income_statement", higher_is_better=True,
    ),
    "net_margin": FinancialMetric(
        id="net_margin", group="profitability", label_vi="Biên lợi nhuận ròng", label_en="Net Margin",
        unit="%", description="Lợi nhuận ròng / Doanh thu.",
        statement="income_statement", higher_is_better=True,
    ),

    # ── Đòn bẩy ───────────────────────────────────────────────────────────────
    "debt_to_equity": FinancialMetric(
        id="debt_to_equity", group="leverage", label_vi="D/E", label_en="Debt/Equity",
        unit="x", description="Tổng nợ / Vốn chủ. D/E ≤ 0.5 = an toàn (phi ngân hàng).",
        statement="financial_ratios", higher_is_better=False,
    ),
    "debt_to_assets": FinancialMetric(
        id="debt_to_assets", group="leverage", label_vi="Nợ/Tài sản", label_en="Debt/Assets",
        unit="%", description="Tổng nợ / Tổng tài sản.",
        statement="financial_ratios", higher_is_better=False,
    ),
    "interest_coverage": FinancialMetric(
        id="interest_coverage", group="leverage", label_vi="Khả năng trả lãi", label_en="Interest Coverage",
        unit="x", description="EBIT / Chi phí lãi vay. ≥ 3x = an toàn.",
        statement="financial_ratios", higher_is_better=True,
    ),

    # ── Thanh khoản ───────────────────────────────────────────────────────────
    "current_ratio": FinancialMetric(
        id="current_ratio", group="liquidity", label_vi="Tỷ số thanh toán hiện hành", label_en="Current Ratio",
        unit="x", description="Tài sản ngắn hạn / Nợ ngắn hạn. ≥ 1.5 = an toàn.",
        statement="financial_ratios", higher_is_better=True,
    ),
    "quick_ratio": FinancialMetric(
        id="quick_ratio", group="liquidity", label_vi="Tỷ số thanh toán nhanh", label_en="Quick Ratio",
        unit="x", description="(Tài sản ngắn hạn - Hàng tồn kho) / Nợ ngắn hạn.",
        statement="financial_ratios", higher_is_better=True,
    ),
    "cash_ratio": FinancialMetric(
        id="cash_ratio", group="liquidity", label_vi="Tỷ số tiền mặt", label_en="Cash Ratio",
        unit="x", description="Tiền mặt / Nợ ngắn hạn.",
        statement="financial_ratios", higher_is_better=True,
    ),

    # ── Hiệu quả vận hành ─────────────────────────────────────────────────────
    "asset_turnover": FinancialMetric(
        id="asset_turnover", group="efficiency", label_vi="Vòng quay tài sản", label_en="Asset Turnover",
        unit="x", description="Doanh thu / Tổng tài sản. Cao = sử dụng tài sản hiệu quả.",
        statement="financial_ratios", higher_is_better=True,
    ),
    "inventory_turnover": FinancialMetric(
        id="inventory_turnover", group="efficiency", label_vi="Vòng quay hàng tồn kho", label_en="Inventory Turnover",
        unit="x", description="COGS / Hàng tồn kho trung bình.",
        statement="financial_ratios", higher_is_better=True,
    ),
    "receivables_turnover": FinancialMetric(
        id="receivables_turnover", group="efficiency", label_vi="Vòng quay khoản phải thu", label_en="Receivables Turnover",
        unit="x", description="Doanh thu / Khoản phải thu trung bình.",
        statement="financial_ratios", higher_is_better=True,
    ),
    "dso": FinancialMetric(
        id="dso", group="efficiency", label_vi="Số ngày thu tiền (DSO)", label_en="Days Sales Outstanding",
        unit="ngày", description="Số ngày trung bình để thu tiền từ khách hàng.",
        statement="financial_ratios", higher_is_better=False,
    ),
    "dio": FinancialMetric(
        id="dio", group="efficiency", label_vi="Số ngày tồn kho (DIO)", label_en="Days Inventory Outstanding",
        unit="ngày", description="Số ngày trung bình hàng tồn kho trước khi bán.",
        statement="financial_ratios", higher_is_better=False,
    ),
    "dpo": FinancialMetric(
        id="dpo", group="efficiency", label_vi="Số ngày trả tiền (DPO)", label_en="Days Payable Outstanding",
        unit="ngày", description="Số ngày trung bình để trả tiền cho nhà cung cấp.",
        statement="financial_ratios", higher_is_better=True,
    ),
    "ccc": FinancialMetric(
        id="ccc", group="efficiency", label_vi="Chu kỳ tiền mặt (CCC)", label_en="Cash Conversion Cycle",
        unit="ngày", description="DSO + DIO - DPO. Số ngày từ khi bỏ tiền đến khi thu tiền về.",
        statement="financial_ratios", higher_is_better=False,
    ),

    # ── Cổ tức ────────────────────────────────────────────────────────────────
    "dividend_yield": FinancialMetric(
        id="dividend_yield", group="payout", label_vi="Tỷ suất cổ tức", label_en="Dividend Yield",
        unit="%", description="Cổ tức / Giá cổ phiếu. ≥ 4% = hấp dẫn cho nhà đầu tư cổ tức.",
        statement="financial_ratios", higher_is_better=True,
    ),
    "payout_ratio": FinancialMetric(
        id="payout_ratio", group="payout", label_vi="Tỷ lệ chi trả cổ tức", label_en="Payout Ratio",
        unit="%", description="Cổ tức / Lợi nhuận ròng. ≤ 70% = bền vững.",
        statement="financial_ratios", higher_is_better=None,
    ),

    # ── Tăng trưởng ───────────────────────────────────────────────────────────
    "revenue_growth": FinancialMetric(
        id="revenue_growth", group="growth", label_vi="Tăng trưởng doanh thu", label_en="Revenue Growth",
        unit="%", description="Tốc độ tăng trưởng doanh thu YoY.",
        statement="income_statement", higher_is_better=True,
    ),
    "eps_growth": FinancialMetric(
        id="eps_growth", group="growth", label_vi="Tăng trưởng EPS", label_en="EPS Growth",
        unit="%", description="Tốc độ tăng trưởng lợi nhuận mỗi cổ phiếu YoY.",
        statement="income_statement", higher_is_better=True,
    ),
    "cagr_5y": FinancialMetric(
        id="cagr_5y", group="growth", label_vi="CAGR 5 năm", label_en="5-Year CAGR",
        unit="%", description="Tốc độ tăng trưởng kép hàng năm trong 5 năm.",
        statement="financial_ratios", higher_is_better=True,
    ),

    # ── Dòng tiền ─────────────────────────────────────────────────────────────
    "fcf": FinancialMetric(
        id="fcf", group="cashflow", label_vi="Dòng tiền tự do (FCF)", label_en="Free Cash Flow",
        unit="tỷ VND", description="OCF - CapEx. Tiền thực sự tạo ra sau đầu tư.",
        statement="cash_flow", higher_is_better=True,
    ),
    "fcf_yield": FinancialMetric(
        id="fcf_yield", group="cashflow", label_vi="FCF Yield", label_en="FCF Yield",
        unit="%", description="FCF / Market Cap. Tỷ suất dòng tiền tự do.",
        statement="financial_ratios", higher_is_better=True,
    ),
    "ocf_to_net_income": FinancialMetric(
        id="ocf_to_net_income", group="cashflow", label_vi="OCF/Lợi nhuận ròng", label_en="OCF/Net Income",
        unit="x", description="Dòng tiền hoạt động / Lợi nhuận ròng. > 1 = chất lượng lợi nhuận tốt.",
        statement="cash_flow", higher_is_better=True,
    ),

    # ── Quy mô ────────────────────────────────────────────────────────────────
    "market_cap": FinancialMetric(
        id="market_cap", group="scale", label_vi="Vốn hóa thị trường", label_en="Market Cap",
        unit="tỷ VND", description="Giá × Số cổ phiếu lưu hành.",
        statement="financial_ratios", higher_is_better=None,
    ),
    "revenue": FinancialMetric(
        id="revenue", group="scale", label_vi="Doanh thu", label_en="Revenue",
        unit="tỷ VND", description="Tổng doanh thu thuần.",
        statement="income_statement", higher_is_better=True,
    ),
    "net_income": FinancialMetric(
        id="net_income", group="scale", label_vi="Lợi nhuận ròng", label_en="Net Income",
        unit="tỷ VND", description="Lợi nhuận sau thuế.",
        statement="income_statement", higher_is_better=True,
    ),
    "total_assets": FinancialMetric(
        id="total_assets", group="scale", label_vi="Tổng tài sản", label_en="Total Assets",
        unit="tỷ VND", description="Tổng tài sản trên bảng cân đối kế toán.",
        statement="balance_sheet", higher_is_better=None,
    ),

    # ── Rủi ro ────────────────────────────────────────────────────────────────
    "beta": FinancialMetric(
        id="beta", group="risk", label_vi="Beta", label_en="Beta",
        unit="x", description="Độ nhạy giá so với thị trường. Beta > 1 = biến động hơn thị trường.",
        statement="financial_ratios", higher_is_better=None,
    ),
    "altman_z_score": FinancialMetric(
        id="altman_z_score", group="altman", label_vi="Altman Z-Score", label_en="Altman Z-Score",
        unit="điểm", description="Z > 2.99 = an toàn, 1.81-2.99 = vùng xám, < 1.81 = nguy hiểm.",
        statement="financial_ratios", higher_is_better=True,
    ),
    "piotroski_f_score": FinancialMetric(
        id="piotroski_f_score", group="piotroski", label_vi="Piotroski F-Score", label_en="Piotroski F-Score",
        unit="điểm/9", description="0-9 điểm. ≥ 7 = chất lượng tài chính tốt, ≤ 2 = yếu.",
        statement="financial_ratios", higher_is_better=True,
    ),
    "early_warning_score": FinancialMetric(
        id="early_warning_score", group="early_warning", label_vi="Điểm cảnh báo rủi ro", label_en="Early Warning Risk Score",
        unit="điểm/100", description="0-100, thấp hơn = an toàn hơn. ≥ 70 = cần chú ý.",
        statement="financial_ratios", higher_is_better=False,
    ),
}


def get_metric(metric_id: str) -> FinancialMetric | None:
    """Get metric metadata by ID."""
    return FINANCIAL_METRICS.get(metric_id)


def get_metrics_by_group(group: str) -> list[FinancialMetric]:
    """Get all metrics in a group."""
    return [m for m in FINANCIAL_METRICS.values() if m.group == group]


def format_metric_value(metric_id: str, value: float | None) -> str:
    """Format a metric value with its unit."""
    if value is None:
        return "N/A"
    metric = get_metric(metric_id)
    if metric is None:
        return str(value)
    unit = metric.unit
    if unit == "%":
        return f"{value * 100:.1f}%"
    elif unit == "x":
        return f"{value:.2f}x"
    elif unit == "ngày":
        return f"{value:.0f} ngày"
    elif unit == "tỷ VND":
        if abs(value) >= 1000:
            return f"{value / 1000:.1f} nghìn tỷ"
        return f"{value:.1f} tỷ"
    elif unit == "điểm":
        return f"{value:.2f}"
    elif unit == "điểm/9":
        return f"{value:.0f}/9"
    elif unit == "điểm/100":
        return f"{value:.0f}/100"
    return f"{value:.2f} {unit}"


def get_metric_rating(metric_id: str, value: float | None) -> str:
    """Get a simple rating for a metric value."""
    if value is None:
        return "N/A"
    metric = get_metric(metric_id)
    if metric is None or metric.higher_is_better is None:
        return "—"

    # Simple thresholds for common metrics
    thresholds: dict[str, tuple[float, float]] = {
        "roe": (0.15, 0.25),
        "roa": (0.05, 0.15),
        "gross_margin": (0.20, 0.40),
        "net_margin": (0.05, 0.15),
        "current_ratio": (1.5, 2.5),
        "debt_to_equity": (0.3, 0.8),
        "dividend_yield": (0.03, 0.06),
        "piotroski_f_score": (4, 7),
        "altman_z_score": (1.81, 2.99),
    }

    if metric_id in thresholds:
        low, high = thresholds[metric_id]
        if metric.higher_is_better:
            if value >= high:
                return "Tốt"
            elif value >= low:
                return "Khá"
            else:
                return "Cần xem xét"
        else:
            if value <= low:
                return "Tốt"
            elif value <= high:
                return "Khá"
            else:
                return "Cần xem xét"

    return "—"
