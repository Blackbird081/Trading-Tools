"""Extended DuPont Analysis (5-Component) — Phân tích DuPont mở rộng.

★ Inspired by baocaotaichinh-/webapp/analysis/dupont_extended.py.
★ ROE = Tax Burden × Interest Burden × Operating Margin × Asset Turnover × Financial Leverage
★ Giúp hiểu nguồn gốc của ROE — rất quan trọng cho value investing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("agents.dupont")


@dataclass
class DuPontComponent:
    """Một thành phần trong phân tích DuPont."""

    name: str
    label_vi: str
    value: float | None
    formula: str
    interpretation: str


@dataclass
class DuPontResult:
    """Kết quả phân tích DuPont 5 thành phần."""

    # 5 thành phần
    tax_burden: DuPontComponent
    interest_burden: DuPontComponent
    operating_margin: DuPontComponent
    asset_turnover: DuPontComponent
    financial_leverage: DuPontComponent

    # ROE tổng hợp
    roe_computed: float | None  # Tính từ 5 thành phần
    roe_reported: float | None  # ROE từ báo cáo tài chính

    # Phân tích
    dominant_driver: str  # Thành phần đóng góp nhiều nhất
    summary: str


def _get(data: dict[str, Any], key: str) -> float | None:
    val = data.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _safe_divide(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def calculate_extended_dupont(
    income_statement: dict[str, Any],
    balance_sheet: dict[str, Any],
    financial_ratios: dict[str, Any] | None = None,
) -> DuPontResult:
    """Tính toán phân tích DuPont mở rộng 5 thành phần.

    ROE = Tax Burden × Interest Burden × Operating Margin × Asset Turnover × Financial Leverage

    Args:
        income_statement: Báo cáo kết quả kinh doanh
        balance_sheet: Bảng cân đối kế toán
        financial_ratios: Chỉ số tài chính (optional, để lấy ROE báo cáo)
    """
    financial_ratios = financial_ratios or {}

    # Lấy dữ liệu cần thiết
    net_income = _get(income_statement, "net_income") or _get(income_statement, "net_profit")
    ebt = _get(income_statement, "profit_before_tax") or _get(income_statement, "ebt")
    operating_profit = _get(income_statement, "operating_profit") or _get(income_statement, "operating_income")
    financial_expense = _get(income_statement, "financial_expense") or _get(income_statement, "interest_expense")
    revenue = _get(income_statement, "revenue") or _get(income_statement, "net_revenue")
    total_assets = _get(balance_sheet, "total_assets")
    total_equity = _get(balance_sheet, "total_equity")

    # EBIT = Operating Profit (hoặc EBT + Financial Expense)
    if operating_profit is not None:
        ebit = operating_profit
    elif financial_expense is not None and ebt is not None:
        ebit = ebt + financial_expense
    else:
        ebit = None

    # ── Thành phần 1: Tax Burden = Net Income / EBT ───────────────────────────
    tax_burden_val = _safe_divide(net_income, ebt)
    tax_burden = DuPontComponent(
        name="tax_burden",
        label_vi="Gánh nặng thuế",
        value=tax_burden_val,
        formula="Net Income / EBT",
        interpretation=(
            f"Tỷ lệ lợi nhuận giữ lại sau thuế: {tax_burden_val * 100:.1f}%"
            if tax_burden_val else "Không có dữ liệu"
        ),
    )

    # ── Thành phần 2: Interest Burden = EBT / EBIT ────────────────────────────
    interest_burden_val = _safe_divide(ebt, ebit)
    interest_burden = DuPontComponent(
        name="interest_burden",
        label_vi="Gánh nặng lãi vay",
        value=interest_burden_val,
        formula="EBT / EBIT",
        interpretation=(
            f"Tỷ lệ lợi nhuận còn lại sau lãi vay: {interest_burden_val * 100:.1f}%"
            if interest_burden_val else "Không có dữ liệu"
        ),
    )

    # ── Thành phần 3: Operating Margin = EBIT / Revenue ───────────────────────
    operating_margin_val = _safe_divide(ebit, revenue)
    operating_margin = DuPontComponent(
        name="operating_margin",
        label_vi="Biên lợi nhuận hoạt động",
        value=operating_margin_val,
        formula="EBIT / Revenue",
        interpretation=(
            f"Biên lợi nhuận hoạt động: {operating_margin_val * 100:.1f}%"
            if operating_margin_val else "Không có dữ liệu"
        ),
    )

    # ── Thành phần 4: Asset Turnover = Revenue / Total Assets ─────────────────
    asset_turnover_val = _safe_divide(revenue, total_assets)
    asset_turnover = DuPontComponent(
        name="asset_turnover",
        label_vi="Vòng quay tài sản",
        value=asset_turnover_val,
        formula="Revenue / Total Assets",
        interpretation=(
            f"Mỗi đồng tài sản tạo ra {asset_turnover_val:.2f}x doanh thu"
            if asset_turnover_val else "Không có dữ liệu"
        ),
    )

    # ── Thành phần 5: Financial Leverage = Total Assets / Total Equity ─────────
    financial_leverage_val = _safe_divide(total_assets, total_equity)
    financial_leverage = DuPontComponent(
        name="financial_leverage",
        label_vi="Đòn bẩy tài chính",
        value=financial_leverage_val,
        formula="Total Assets / Total Equity",
        interpretation=(
            f"Đòn bẩy tài chính: {financial_leverage_val:.2f}x"
            if financial_leverage_val else "Không có dữ liệu"
        ),
    )

    # ── ROE tổng hợp ──────────────────────────────────────────────────────────
    components = [tax_burden_val, interest_burden_val, operating_margin_val, asset_turnover_val, financial_leverage_val]
    if all(c is not None for c in components):
        roe_computed = tax_burden_val * interest_burden_val * operating_margin_val * asset_turnover_val * financial_leverage_val  # type: ignore[operator]
    else:
        roe_computed = None

    roe_reported = _get(financial_ratios, "roe")

    # ── Xác định thành phần đóng góp nhiều nhất ───────────────────────────────
    dominant_driver = _identify_dominant_driver(
        tax_burden_val, interest_burden_val, operating_margin_val,
        asset_turnover_val, financial_leverage_val,
    )

    # ── Tóm tắt ───────────────────────────────────────────────────────────────
    summary = _build_summary(
        roe_computed, roe_reported, dominant_driver,
        tax_burden_val, interest_burden_val, operating_margin_val,
        asset_turnover_val, financial_leverage_val,
    )

    return DuPontResult(
        tax_burden=tax_burden,
        interest_burden=interest_burden,
        operating_margin=operating_margin,
        asset_turnover=asset_turnover,
        financial_leverage=financial_leverage,
        roe_computed=roe_computed,
        roe_reported=roe_reported,
        dominant_driver=dominant_driver,
        summary=summary,
    )


def _identify_dominant_driver(
    tax_burden: float | None,
    interest_burden: float | None,
    operating_margin: float | None,
    asset_turnover: float | None,
    financial_leverage: float | None,
) -> str:
    """Xác định thành phần đóng góp nhiều nhất vào ROE."""
    # Normalize each component relative to "neutral" value
    # Tax burden: 0.75 is neutral (25% tax rate)
    # Interest burden: 0.9 is neutral
    # Operating margin: 0.1 is neutral (10%)
    # Asset turnover: 1.0 is neutral
    # Financial leverage: 2.0 is neutral

    scores = {}
    if operating_margin is not None:
        scores["Biên lợi nhuận hoạt động"] = operating_margin / 0.10
    if asset_turnover is not None:
        scores["Vòng quay tài sản"] = asset_turnover / 1.0
    if financial_leverage is not None:
        scores["Đòn bẩy tài chính"] = financial_leverage / 2.0
    if interest_burden is not None:
        scores["Gánh nặng lãi vay"] = interest_burden / 0.9
    if tax_burden is not None:
        scores["Gánh nặng thuế"] = tax_burden / 0.75

    if not scores:
        return "Không xác định được"

    return max(scores, key=lambda k: scores[k])


def _build_summary(
    roe_computed: float | None,
    roe_reported: float | None,
    dominant_driver: str,
    tax_burden: float | None,
    interest_burden: float | None,
    operating_margin: float | None,
    asset_turnover: float | None,
    financial_leverage: float | None,
) -> str:
    """Xây dựng tóm tắt phân tích DuPont."""
    lines = []

    if roe_computed is not None:
        lines.append(f"ROE (tính toán): {roe_computed * 100:.1f}%")
    if roe_reported is not None:
        lines.append(f"ROE (báo cáo): {roe_reported * 100:.1f}%")

    lines.append(f"\nThành phần đóng góp chính: {dominant_driver}")

    lines.append("\nPhân tích 5 thành phần:")
    if operating_margin is not None:
        lines.append(f"  - Biên lợi nhuận hoạt động: {operating_margin * 100:.1f}%")
    if asset_turnover is not None:
        lines.append(f"  - Vòng quay tài sản: {asset_turnover:.2f}x")
    if financial_leverage is not None:
        lines.append(f"  - Đòn bẩy tài chính: {financial_leverage:.2f}x")
    if interest_burden is not None:
        lines.append(f"  - Gánh nặng lãi vay: {interest_burden * 100:.1f}%")
    if tax_burden is not None:
        lines.append(f"  - Gánh nặng thuế: {tax_burden * 100:.1f}%")

    # Nhận xét
    if financial_leverage is not None and financial_leverage > 4:
        lines.append("\n⚠️ Đòn bẩy tài chính cao — ROE được khuếch đại bởi nợ, không phải hiệu quả thực sự")
    if operating_margin is not None and operating_margin > 0.20:
        lines.append("\n✅ Biên lợi nhuận hoạt động cao — lợi thế cạnh tranh mạnh")

    return "\n".join(lines)
