"""Technology Industry Analysis — chỉ số đặc thù ngành công nghệ.

★ Inspired by baocaotaichinh-/webapp/analysis/technology_analysis.py.
★ Các chỉ số: R&D/Revenue, Recurring Revenue, Rule of 40, SaaS metrics.
★ Áp dụng cho: FPT, CMG, VGI, ELC, ITD.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TechMetric:
    """Kết quả tính toán một chỉ số công nghệ."""

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


def calculate_rd_to_revenue(income_statement: dict[str, Any]) -> TechMetric:
    """R&D / Doanh thu — mức độ đầu tư vào nghiên cứu phát triển.

    Tech companies: 5-15% là bình thường.
    > 15%: Đầu tư mạnh vào tương lai, < 5%: Ít đổi mới.
    """
    rd_expense = _get(income_statement, "research_and_development") or _get(income_statement, "rd_expense")
    revenue = _get(income_statement, "revenue") or _get(income_statement, "net_revenue")
    ratio = _safe_divide(rd_expense, revenue)

    if ratio is None:
        rating = "Không có dữ liệu"
    elif ratio >= 0.10:
        rating = "Đầu tư mạnh"
    elif ratio >= 0.05:
        rating = "Bình thường"
    elif ratio >= 0.02:
        rating = "Thấp"
    else:
        rating = "Rất thấp"

    return TechMetric(
        value=ratio,
        rating=rating,
        label="R&D/Doanh thu",
        description="Chi phí R&D / Doanh thu. Phản ánh mức độ đầu tư vào đổi mới.",
        benchmark="5-15% là bình thường cho tech",
    )


def calculate_rule_of_40(
    revenue_growth: float | None,
    operating_margin: float | None,
) -> TechMetric:
    """Rule of 40 — tổng tăng trưởng doanh thu + biên lợi nhuận.

    Rule of 40 = Revenue Growth % + Operating Margin %
    > 40: Tốt, 20-40: Khá, < 20: Cần cải thiện.
    """
    if revenue_growth is None or operating_margin is None:
        return TechMetric(
            value=None,
            rating="Không có dữ liệu",
            label="Rule of 40",
            description="Tăng trưởng doanh thu + Biên lợi nhuận hoạt động. > 40 là tốt.",
            benchmark="> 40 là tốt cho SaaS/Tech",
        )

    rule_of_40 = (revenue_growth * 100) + (operating_margin * 100)

    if rule_of_40 >= 40:
        rating = "Tốt"
    elif rule_of_40 >= 20:
        rating = "Khá"
    elif rule_of_40 >= 0:
        rating = "Cần cải thiện"
    else:
        rating = "Kém"

    return TechMetric(
        value=rule_of_40,
        rating=rating,
        label="Rule of 40",
        description="Tăng trưởng doanh thu % + Biên lợi nhuận hoạt động %. > 40 là tốt.",
        benchmark="> 40 là tốt cho SaaS/Tech",
    )


def calculate_recurring_revenue_ratio(income_statement: dict[str, Any]) -> TechMetric:
    """Tỷ lệ doanh thu định kỳ (Recurring Revenue).

    Doanh thu từ dịch vụ/subscription / Tổng doanh thu.
    > 60%: Tốt (ổn định), 30-60%: Khá, < 30%: Phụ thuộc dự án.
    """
    recurring = _get(income_statement, "recurring_revenue") or _get(income_statement, "service_revenue")
    total = _get(income_statement, "revenue") or _get(income_statement, "net_revenue")
    ratio = _safe_divide(recurring, total)

    if ratio is None:
        rating = "Không có dữ liệu"
    elif ratio >= 0.60:
        rating = "Tốt"
    elif ratio >= 0.30:
        rating = "Khá"
    else:
        rating = "Phụ thuộc dự án"

    return TechMetric(
        value=ratio,
        rating=rating,
        label="Doanh thu định kỳ/Tổng DT",
        description="Doanh thu từ dịch vụ/subscription / Tổng doanh thu. Cao = ổn định hơn.",
        benchmark="> 60% là tốt",
    )


def calculate_asset_light_ratio(balance_sheet: dict[str, Any]) -> TechMetric:
    """Asset-light ratio — tỷ lệ tài sản vô hình/tổng tài sản.

    Tech companies thường có nhiều tài sản vô hình (IP, software).
    > 30%: Asset-light model, < 10%: Phụ thuộc tài sản vật chất.
    """
    intangible_assets = _get(balance_sheet, "intangible_assets") or _get(balance_sheet, "goodwill_and_intangibles")
    total_assets = _get(balance_sheet, "total_assets")
    ratio = _safe_divide(intangible_assets, total_assets)

    if ratio is None:
        rating = "Không có dữ liệu"
    elif ratio >= 0.30:
        rating = "Asset-light"
    elif ratio >= 0.10:
        rating = "Trung bình"
    else:
        rating = "Asset-heavy"

    return TechMetric(
        value=ratio,
        rating=rating,
        label="Tài sản vô hình/Tổng TS",
        description="Tài sản vô hình (IP, software) / Tổng tài sản. Cao = asset-light model.",
        benchmark="> 30% là asset-light",
    )


def analyze_technology(
    income_statement: dict[str, Any],
    balance_sheet: dict[str, Any],
    revenue_growth: float | None = None,
    operating_margin: float | None = None,
) -> dict[str, TechMetric]:
    """Phân tích toàn diện ngành công nghệ."""
    return {
        "rd_to_revenue": calculate_rd_to_revenue(income_statement),
        "rule_of_40": calculate_rule_of_40(revenue_growth, operating_margin),
        "recurring_revenue": calculate_recurring_revenue_ratio(income_statement),
        "asset_light": calculate_asset_light_ratio(balance_sheet),
    }


def get_technology_summary(
    income_statement: dict[str, Any],
    balance_sheet: dict[str, Any],
    revenue_growth: float | None = None,
    operating_margin: float | None = None,
) -> str:
    """Tóm tắt phân tích công nghệ bằng tiếng Việt."""
    metrics = analyze_technology(income_statement, balance_sheet, revenue_growth, operating_margin)
    lines = []
    for key, metric in metrics.items():
        if metric.value is not None:
            if metric.value < 1:
                value_str = f"{metric.value * 100:.1f}%"
            else:
                value_str = f"{metric.value:.1f}"
            lines.append(f"- {metric.label}: {value_str} ({metric.rating})")
    return "\n".join(lines) if lines else "Không đủ dữ liệu để phân tích công nghệ."
