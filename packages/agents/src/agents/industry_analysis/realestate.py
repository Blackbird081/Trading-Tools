"""Real Estate Industry Analysis — chỉ số đặc thù ngành bất động sản.

★ Inspired by baocaotaichinh-/webapp/analysis/realestate_analysis.py.
★ Các chỉ số: Inventory/Assets, Debt/Equity, Revenue Recognition, Gross Margin.
★ Áp dụng cho: VHM, NVL, PDR, DXG, KDH, BCM, SZC, KBC.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class REMetric:
    """Kết quả tính toán một chỉ số BĐS."""

    value: float | None
    rating: str
    label: str
    description: str
    benchmark: str | None = None


def _safe_divide(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _get(data: dict[str, Any], key: str) -> float | None:
    val = data.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def calculate_inventory_to_assets(balance_sheet: dict[str, Any]) -> REMetric:
    """Tỷ lệ Hàng tồn kho / Tổng tài sản.

    Đối với BĐS: Tỷ lệ cao là bình thường (dự án đang phát triển).
    40-70%: Bình thường, > 70%: Cần xem xét vòng quay, < 40%: Giai đoạn giữa dự án.
    """
    inventory = _get(balance_sheet, "inventory")
    total_assets = _get(balance_sheet, "total_assets")
    ratio = _safe_divide(inventory, total_assets)

    if ratio is None:
        rating = "Không có dữ liệu"
    elif 0.40 <= ratio <= 0.70:
        rating = "Bình thường"
    elif ratio > 0.70:
        rating = "Cần xem xét"
    else:
        rating = "Thấp"

    return REMetric(
        value=ratio,
        rating=rating,
        label="Hàng tồn kho/Tổng tài sản",
        description="Tỷ lệ hàng tồn kho (dự án BĐS) trên tổng tài sản. 40-70% là bình thường.",
        benchmark="40-70% cho doanh nghiệp phát triển BĐS",
    )


def calculate_debt_to_equity_re(balance_sheet: dict[str, Any]) -> REMetric:
    """Tỷ lệ Nợ/Vốn chủ cho BĐS.

    BĐS thường có D/E cao hơn các ngành khác do đặc thù vốn lớn.
    < 1.0: Tốt, 1.0-2.0: Chấp nhận được, > 2.0: Rủi ro cao.
    """
    total_debt = _get(balance_sheet, "total_debt") or _get(balance_sheet, "total_liabilities")
    total_equity = _get(balance_sheet, "total_equity")
    ratio = _safe_divide(total_debt, total_equity)

    if ratio is None:
        rating = "Không có dữ liệu"
    elif ratio <= 1.0:
        rating = "Tốt"
    elif ratio <= 2.0:
        rating = "Chấp nhận được"
    elif ratio <= 3.0:
        rating = "Cần xem xét"
    else:
        rating = "Rủi ro cao"

    return REMetric(
        value=ratio,
        rating=rating,
        label="D/E (Nợ/Vốn chủ)",
        description="Tổng nợ / Vốn chủ sở hữu. BĐS thường có D/E cao hơn các ngành khác.",
        benchmark="< 1.0 là tốt, > 2.0 là rủi ro",
    )


def calculate_gross_margin_re(income_statement: dict[str, Any]) -> REMetric:
    """Biên lợi nhuận gộp ngành BĐS.

    BĐS thường có biên gộp cao (30-50%) do giá trị đất.
    > 40%: Tốt, 25-40%: Khá, < 25%: Thấp.
    """
    revenue = _get(income_statement, "revenue") or _get(income_statement, "net_revenue")
    cogs = _get(income_statement, "cost_of_goods_sold") or _get(income_statement, "cost_of_revenue")
    if revenue and cogs:
        gross_profit = revenue - cogs
        margin = _safe_divide(gross_profit, revenue)
    else:
        margin = _get(income_statement, "gross_margin")

    if margin is None:
        rating = "Không có dữ liệu"
    elif margin >= 0.40:
        rating = "Tốt"
    elif margin >= 0.25:
        rating = "Khá"
    elif margin >= 0.15:
        rating = "Trung bình"
    else:
        rating = "Thấp"

    return REMetric(
        value=margin,
        rating=rating,
        label="Biên lợi nhuận gộp",
        description="(Doanh thu - COGS) / Doanh thu. BĐS thường có biên cao do giá trị đất.",
        benchmark="> 40% là tốt cho BĐS",
    )


def calculate_cash_to_short_term_debt(balance_sheet: dict[str, Any]) -> REMetric:
    """Tiền mặt / Nợ ngắn hạn — thanh khoản ngắn hạn.

    Quan trọng cho BĐS vì rủi ro thanh khoản cao.
    > 0.5: Tốt, 0.3-0.5: Khá, < 0.3: Cần chú ý.
    """
    cash = _get(balance_sheet, "cash") or _get(balance_sheet, "cash_and_equivalents")
    short_term_debt = _get(balance_sheet, "short_term_debt") or _get(balance_sheet, "current_liabilities")
    ratio = _safe_divide(cash, short_term_debt)

    if ratio is None:
        rating = "Không có dữ liệu"
    elif ratio >= 0.5:
        rating = "Tốt"
    elif ratio >= 0.3:
        rating = "Khá"
    elif ratio >= 0.1:
        rating = "Cần chú ý"
    else:
        rating = "Rủi ro thanh khoản"

    return REMetric(
        value=ratio,
        rating=rating,
        label="Tiền/Nợ ngắn hạn",
        description="Tiền mặt / Nợ ngắn hạn. Quan trọng cho BĐS vì rủi ro thanh khoản cao.",
        benchmark="> 0.5 là tốt",
    )


def analyze_realestate(
    balance_sheet: dict[str, Any],
    income_statement: dict[str, Any],
) -> dict[str, REMetric]:
    """Phân tích toàn diện ngành bất động sản."""
    return {
        "inventory_to_assets": calculate_inventory_to_assets(balance_sheet),
        "debt_to_equity": calculate_debt_to_equity_re(balance_sheet),
        "gross_margin": calculate_gross_margin_re(income_statement),
        "cash_to_short_term_debt": calculate_cash_to_short_term_debt(balance_sheet),
    }


def get_realestate_summary(
    balance_sheet: dict[str, Any],
    income_statement: dict[str, Any],
) -> str:
    """Tóm tắt phân tích BĐS bằng tiếng Việt."""
    metrics = analyze_realestate(balance_sheet, income_statement)
    lines = []
    for key, metric in metrics.items():
        if metric.value is not None:
            if metric.value < 1:
                value_str = f"{metric.value * 100:.1f}%"
            else:
                value_str = f"{metric.value:.2f}x"
            lines.append(f"- {metric.label}: {value_str} ({metric.rating})")
    return "\n".join(lines) if lines else "Không đủ dữ liệu để phân tích BĐS."
