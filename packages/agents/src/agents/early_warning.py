"""Early Warning System — Hệ thống cảnh báo tài chính sớm.

★ Inspired by baocaotaichinh-/webapp/analysis/early_warning.py.
★ Risk Score 0-100 (thấp hơn = an toàn hơn).
★ Phát hiện: xu hướng suy giảm, nợ gia tăng, dòng tiền âm, Altman Z-Score nguy hiểm.
★ Tích hợp vào RiskAgent để cảnh báo trước khi đặt lệnh.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("agents.early_warning")


@dataclass
class EarlyWarningResult:
    """Kết quả đánh giá cảnh báo sớm."""

    risk_score: float  # 0-100, thấp hơn = an toàn hơn
    risk_level: str    # "low", "medium", "high", "critical"
    alerts: list[str] = field(default_factory=list)
    positive_signals: list[str] = field(default_factory=list)
    recommendation: str = ""

    @property
    def is_safe(self) -> bool:
        return self.risk_level in ("low", "medium")

    @property
    def summary(self) -> str:
        lines = [f"Risk Score: {self.risk_score:.0f}/100 ({self.risk_level.upper()})"]
        if self.alerts:
            lines.append("\n⚠️ Cảnh báo:")
            lines.extend(f"  - {a}" for a in self.alerts)
        if self.positive_signals:
            lines.append("\n✅ Tín hiệu tích cực:")
            lines.extend(f"  - {p}" for p in self.positive_signals)
        if self.recommendation:
            lines.append(f"\n📋 Khuyến nghị: {self.recommendation}")
        return "\n".join(lines)


def _get(data: dict[str, Any], key: str) -> float | None:
    val = data.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def calculate_early_warning(
    financial_ratios: dict[str, Any],
    balance_sheet: dict[str, Any] | None = None,
    income_statement: dict[str, Any] | None = None,
    cash_flow: dict[str, Any] | None = None,
    previous_financial_ratios: dict[str, Any] | None = None,
    altman_z_score: float | None = None,
    piotroski_f_score: int | None = None,
) -> EarlyWarningResult:
    """Tính toán cảnh báo sớm cho một công ty.

    Args:
        financial_ratios: Chỉ số tài chính hiện tại
        balance_sheet: Bảng cân đối kế toán
        income_statement: Báo cáo kết quả kinh doanh
        cash_flow: Báo cáo dòng tiền
        previous_financial_ratios: Chỉ số tài chính năm trước (để so sánh)
        altman_z_score: Điểm Altman Z-Score (nếu đã tính)
        piotroski_f_score: Điểm Piotroski F-Score (nếu đã tính)

    Returns:
        EarlyWarningResult với risk_score, risk_level, alerts, positive_signals
    """
    alerts: list[str] = []
    positive_signals: list[str] = []
    risk_score = 0.0

    balance_sheet = balance_sheet or {}
    income_statement = income_statement or {}
    cash_flow = cash_flow or {}
    previous_financial_ratios = previous_financial_ratios or {}

    # ── Check 1: Altman Z-Score ───────────────────────────────────────────────
    if altman_z_score is not None:
        if altman_z_score < 1.81:
            alerts.append(f"Altman Z-Score = {altman_z_score:.2f} (< 1.81) — Vùng nguy hiểm, nguy cơ phá sản cao")
            risk_score += 25
        elif altman_z_score < 2.99:
            alerts.append(f"Altman Z-Score = {altman_z_score:.2f} (1.81-2.99) — Vùng xám, cần theo dõi")
            risk_score += 10
        else:
            positive_signals.append(f"Altman Z-Score = {altman_z_score:.2f} (> 2.99) — An toàn")

    # ── Check 2: Piotroski F-Score ────────────────────────────────────────────
    if piotroski_f_score is not None:
        if piotroski_f_score <= 2:
            alerts.append(f"Piotroski F-Score = {piotroski_f_score}/9 — Chất lượng tài chính rất yếu")
            risk_score += 20
        elif piotroski_f_score <= 4:
            alerts.append(f"Piotroski F-Score = {piotroski_f_score}/9 — Chất lượng tài chính yếu")
            risk_score += 10
        elif piotroski_f_score >= 7:
            positive_signals.append(f"Piotroski F-Score = {piotroski_f_score}/9 — Chất lượng tài chính tốt")

    # ── Check 3: ROE suy giảm ─────────────────────────────────────────────────
    roe_current = _get(financial_ratios, "roe")
    roe_previous = _get(previous_financial_ratios, "roe")
    if roe_current is not None:
        if roe_current < 0:
            alerts.append(f"ROE âm ({roe_current * 100:.1f}%) — Doanh nghiệp đang thua lỗ")
            risk_score += 20
        elif roe_current < 0.05:
            alerts.append(f"ROE rất thấp ({roe_current * 100:.1f}%) — Hiệu quả sử dụng vốn kém")
            risk_score += 10
        elif roe_current >= 0.15:
            positive_signals.append(f"ROE tốt ({roe_current * 100:.1f}%)")

        if roe_previous is not None and roe_current < roe_previous * 0.7:
            alerts.append(f"ROE giảm mạnh: {roe_previous * 100:.1f}% → {roe_current * 100:.1f}% (giảm > 30%)")
            risk_score += 10

    # ── Check 4: Nợ gia tăng ─────────────────────────────────────────────────
    de_current = _get(financial_ratios, "debt_to_equity")
    de_previous = _get(previous_financial_ratios, "debt_to_equity")
    if de_current is not None:
        if de_current > 3.0:
            alerts.append(f"D/E rất cao ({de_current:.2f}x) — Đòn bẩy tài chính nguy hiểm")
            risk_score += 15
        elif de_current > 2.0:
            alerts.append(f"D/E cao ({de_current:.2f}x) — Cần theo dõi")
            risk_score += 7

        if de_previous is not None and de_current > de_previous * 1.5:
            alerts.append(f"D/E tăng mạnh: {de_previous:.2f}x → {de_current:.2f}x (tăng > 50%)")
            risk_score += 8

    # ── Check 5: Dòng tiền hoạt động âm ──────────────────────────────────────
    ocf = _get(cash_flow, "operating_cash_flow") or _get(cash_flow, "net_cash_from_operations")
    if ocf is not None:
        if ocf < 0:
            alerts.append(f"Dòng tiền hoạt động âm ({ocf:,.0f} VND) — Hoạt động kinh doanh không tạo tiền")
            risk_score += 15
        else:
            positive_signals.append("Dòng tiền hoạt động dương")

    # ── Check 6: Thanh khoản thấp ─────────────────────────────────────────────
    current_ratio = _get(financial_ratios, "current_ratio")
    if current_ratio is not None:
        if current_ratio < 1.0:
            alerts.append(f"Current Ratio < 1 ({current_ratio:.2f}x) — Không đủ tài sản ngắn hạn để trả nợ")
            risk_score += 15
        elif current_ratio < 1.5:
            alerts.append(f"Current Ratio thấp ({current_ratio:.2f}x) — Thanh khoản hạn chế")
            risk_score += 5
        elif current_ratio >= 2.0:
            positive_signals.append(f"Thanh khoản tốt (Current Ratio = {current_ratio:.2f}x)")

    # ── Check 7: Biên lợi nhuận suy giảm ─────────────────────────────────────
    margin_current = _get(financial_ratios, "net_margin") or _get(income_statement, "net_margin")
    margin_previous = _get(previous_financial_ratios, "net_margin")
    if margin_current is not None:
        if margin_current < 0:
            alerts.append(f"Biên lợi nhuận ròng âm ({margin_current * 100:.1f}%) — Thua lỗ")
            risk_score += 15
        elif margin_current < 0.03:
            alerts.append(f"Biên lợi nhuận ròng rất thấp ({margin_current * 100:.1f}%)")
            risk_score += 5

        if margin_previous is not None and margin_current < margin_previous * 0.5:
            alerts.append(f"Biên lợi nhuận giảm mạnh: {margin_previous * 100:.1f}% → {margin_current * 100:.1f}%")
            risk_score += 8

    # ── Tổng hợp ──────────────────────────────────────────────────────────────
    risk_score = min(100.0, risk_score)

    if risk_score >= 60:
        risk_level = "critical"
        recommendation = "Không nên đầu tư. Rủi ro tài chính rất cao."
    elif risk_score >= 40:
        risk_level = "high"
        recommendation = "Thận trọng cao. Cần phân tích sâu hơn trước khi đầu tư."
    elif risk_score >= 20:
        risk_level = "medium"
        recommendation = "Theo dõi chặt chẽ. Có một số tín hiệu cần chú ý."
    else:
        risk_level = "low"
        recommendation = "Sức khỏe tài chính tốt. Tiếp tục theo dõi định kỳ."

    return EarlyWarningResult(
        risk_score=risk_score,
        risk_level=risk_level,
        alerts=alerts,
        positive_signals=positive_signals,
        recommendation=recommendation,
    )
