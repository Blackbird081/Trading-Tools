"""Banking Industry Analysis — chỉ số đặc thù ngành ngân hàng.

★ Inspired by baocaotaichinh-/webapp/analysis/banking_analysis.py.
★ Các chỉ số: NIM, NPL, CAR, LDR, CASA, Cost-to-Income.
★ Áp dụng cho: VCB, BID, CTG, TCB, MBB, ACB, VPB, HDB, STB, TPB.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BankingMetric:
    """Kết quả tính toán một chỉ số ngân hàng."""

    value: float | None
    rating: str  # "Tốt", "Khá", "Trung bình", "Cần xem xét", "Rủi ro"
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


def calculate_nim(financial_data: dict[str, Any]) -> BankingMetric:
    """Net Interest Margin (NIM) — Biên lãi thuần.

    NIM = Thu nhập lãi thuần / Tổng tài sản sinh lãi trung bình
    Benchmark VN: 3-5% là tốt
    """
    net_interest_income = _get(financial_data, "net_interest_income")
    interest_earning_assets = _get(financial_data, "interest_earning_assets") or _get(financial_data, "total_assets")
    nim = _safe_divide(net_interest_income, interest_earning_assets)

    if nim is None:
        rating = "Không có dữ liệu"
    elif nim >= 0.04:
        rating = "Tốt"
    elif nim >= 0.03:
        rating = "Khá"
    elif nim >= 0.02:
        rating = "Trung bình"
    else:
        rating = "Cần xem xét"

    return BankingMetric(
        value=nim,
        rating=rating,
        label="NIM (Biên lãi thuần)",
        description="Thu nhập lãi thuần / Tổng tài sản sinh lãi. NIM cao = hiệu quả cho vay tốt.",
        benchmark="3-5% là tốt cho ngân hàng VN",
    )


def calculate_npl(financial_data: dict[str, Any]) -> BankingMetric:
    """Non-Performing Loan Ratio (NPL) — Tỷ lệ nợ xấu.

    NPL = Nợ xấu (nhóm 3-5) / Tổng dư nợ
    Benchmark VN: < 2% là tốt, > 3% là đáng lo ngại
    """
    npl = _get(financial_data, "npl_ratio") or _get(financial_data, "bad_debt_ratio")
    total_loans = _get(financial_data, "total_loans")
    bad_debt = _get(financial_data, "bad_debt")

    if npl is None and bad_debt is not None and total_loans is not None:
        npl = _safe_divide(bad_debt, total_loans)

    if npl is None:
        rating = "Không có dữ liệu"
    elif npl <= 0.01:
        rating = "Tốt"
    elif npl <= 0.02:
        rating = "Khá"
    elif npl <= 0.03:
        rating = "Trung bình"
    else:
        rating = "Rủi ro"

    return BankingMetric(
        value=npl,
        rating=rating,
        label="NPL (Tỷ lệ nợ xấu)",
        description="Nợ xấu / Tổng dư nợ. NPL thấp = chất lượng tín dụng tốt.",
        benchmark="< 2% là tốt, > 3% cần chú ý",
    )


def calculate_car(financial_data: dict[str, Any]) -> BankingMetric:
    """Capital Adequacy Ratio (CAR) — Tỷ lệ an toàn vốn.

    CAR = Vốn tự có / Tổng tài sản có rủi ro
    Quy định NHNN: ≥ 8% (Basel II), ≥ 10% (Basel III)
    """
    car = _get(financial_data, "car") or _get(financial_data, "capital_adequacy_ratio")

    if car is None:
        rating = "Không có dữ liệu"
    elif car >= 0.12:
        rating = "Tốt"
    elif car >= 0.10:
        rating = "Khá"
    elif car >= 0.08:
        rating = "Trung bình"
    else:
        rating = "Rủi ro"

    return BankingMetric(
        value=car,
        rating=rating,
        label="CAR (Tỷ lệ an toàn vốn)",
        description="Vốn tự có / Tổng tài sản có rủi ro. Quy định NHNN ≥ 8%.",
        benchmark="≥ 10% theo Basel III",
    )


def calculate_ldr(financial_data: dict[str, Any]) -> BankingMetric:
    """Loan-to-Deposit Ratio (LDR) — Tỷ lệ cho vay/huy động.

    LDR = Tổng dư nợ / Tổng tiền gửi
    Quy định NHNN: ≤ 85%
    """
    total_loans = _get(financial_data, "total_loans")
    total_deposits = _get(financial_data, "total_deposits")
    ldr = _safe_divide(total_loans, total_deposits)

    if ldr is None:
        rating = "Không có dữ liệu"
    elif ldr <= 0.75:
        rating = "Tốt"
    elif ldr <= 0.85:
        rating = "Khá"
    elif ldr <= 0.90:
        rating = "Trung bình"
    else:
        rating = "Rủi ro"

    return BankingMetric(
        value=ldr,
        rating=rating,
        label="LDR (Cho vay/Huy động)",
        description="Tổng dư nợ / Tổng tiền gửi. Quy định NHNN ≤ 85%.",
        benchmark="≤ 85% theo quy định NHNN",
    )


def calculate_cost_to_income(financial_data: dict[str, Any]) -> BankingMetric:
    """Cost-to-Income Ratio (CIR) — Tỷ lệ chi phí/thu nhập.

    CIR = Chi phí hoạt động / Thu nhập hoạt động
    Benchmark: < 40% là tốt
    """
    operating_expenses = _get(financial_data, "operating_expenses")
    operating_income = _get(financial_data, "operating_income") or _get(financial_data, "total_operating_income")
    cir = _safe_divide(operating_expenses, operating_income)

    if cir is None:
        rating = "Không có dữ liệu"
    elif cir <= 0.35:
        rating = "Tốt"
    elif cir <= 0.45:
        rating = "Khá"
    elif cir <= 0.55:
        rating = "Trung bình"
    else:
        rating = "Cần xem xét"

    return BankingMetric(
        value=cir,
        rating=rating,
        label="CIR (Chi phí/Thu nhập)",
        description="Chi phí hoạt động / Thu nhập hoạt động. Thấp hơn = hiệu quả hơn.",
        benchmark="< 40% là tốt",
    )


def analyze_banking(financial_data: dict[str, Any]) -> dict[str, BankingMetric]:
    """Phân tích toàn diện ngành ngân hàng."""
    return {
        "nim": calculate_nim(financial_data),
        "npl": calculate_npl(financial_data),
        "car": calculate_car(financial_data),
        "ldr": calculate_ldr(financial_data),
        "cir": calculate_cost_to_income(financial_data),
    }


def get_banking_summary(financial_data: dict[str, Any]) -> str:
    """Tóm tắt phân tích ngân hàng bằng tiếng Việt."""
    metrics = analyze_banking(financial_data)
    lines = []
    for key, metric in metrics.items():
        if metric.value is not None:
            value_str = f"{metric.value * 100:.1f}%" if metric.value < 1 else f"{metric.value:.2f}"
            lines.append(f"- {metric.label}: {value_str} ({metric.rating})")
    return "\n".join(lines) if lines else "Không đủ dữ liệu để phân tích ngân hàng."
