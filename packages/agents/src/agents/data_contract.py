"""Data Contract — chuẩn hóa tên cột từ nhiều nguồn dữ liệu.

★ Inspired by baocaotaichinh-/webapp/analysis/data_contract.py.
★ COLUMN_ALIASES: map tên cột chuẩn → các tên thay thế từ vnstock/SSI/DNSE.
★ Dùng trong ScreenerAgent và FundamentalAgent để normalize dữ liệu.
"""

from __future__ import annotations

from typing import Any

# ── Column Aliases ────────────────────────────────────────────────────────────
# Map: tên chuẩn → [các tên thay thế theo thứ tự ưu tiên]
# Nguồn: vnstock, SSI API, DNSE API, báo cáo tài chính VN

COLUMN_ALIASES: dict[str, list[str]] = {
    # Revenue
    "revenue": ["net_revenue", "revenue", "total_revenue", "sales", "doanh_thu_thuan", "net_sales"],
    "gross_revenue": ["gross_revenue", "total_revenue_gross", "doanh_thu"],

    # Profit
    "net_income": ["net_profit", "net_income", "profit_after_tax", "net_profit_parent_company",
                   "loi_nhuan_sau_thue", "profit_after_tax_parent"],
    "operating_profit": ["operating_profit", "operating_income", "ebit", "loi_nhuan_hoat_dong"],
    "gross_profit": ["gross_profit", "loi_nhuan_gop"],
    "profit_before_tax": ["profit_before_tax", "ebt", "pre_tax_profit", "loi_nhuan_truoc_thue"],

    # Expenses
    "cost_of_goods_sold": ["cost_of_goods_sold", "cogs", "cost_of_revenue", "gia_von_hang_ban"],
    "operating_expenses": ["operating_expenses", "selling_general_admin", "sga", "chi_phi_hoat_dong"],
    "financial_expense": ["financial_expense", "interest_expense", "chi_phi_tai_chinh"],
    "research_and_development": ["research_and_development", "rd_expense", "r_and_d", "chi_phi_nghien_cuu"],

    # Balance Sheet - Assets
    "total_assets": ["total_assets", "tong_tai_san", "assets_total"],
    "current_assets": ["current_assets", "asset_current", "assets_current", "tai_san_ngan_han"],
    "cash": ["cash", "cash_and_equivalents", "cash_and_cash_equivalents", "tien_va_tuong_duong_tien"],
    "inventory": ["inventory", "hang_ton_kho", "inventories"],
    "accounts_receivable": ["accounts_receivable", "receivables", "phai_thu_ngan_han"],
    "intangible_assets": ["intangible_assets", "goodwill_and_intangibles", "tai_san_vo_hinh"],

    # Balance Sheet - Liabilities
    "total_liabilities": ["total_liabilities", "liabilities_total", "tong_no_phai_tra"],
    "current_liabilities": ["current_liabilities", "liabilities_current", "no_ngan_han"],
    "short_term_debt": ["short_term_debt", "debt_current", "current_debt", "vay_ngan_han"],
    "long_term_debt": ["long_term_debt", "debt_non_current", "non_current_debt", "vay_dai_han"],
    "accounts_payable": ["accounts_payable", "payables", "phai_tra_ngan_han"],

    # Balance Sheet - Equity
    "total_equity": ["total_equity", "equity_total", "shareholders_equity", "von_chu_so_huu"],
    "retained_earnings": ["retained_earnings", "retained_profit", "loi_nhuan_giu_lai"],

    # Cash Flow
    "operating_cash_flow": ["operating_cash_flow", "net_cash_from_operations", "cash_from_operations",
                             "lctt_hoat_dong_kinh_doanh"],
    "investing_cash_flow": ["investing_cash_flow", "net_cash_from_investing", "lctt_dau_tu"],
    "financing_cash_flow": ["financing_cash_flow", "net_cash_from_financing", "lctt_tai_chinh"],
    "capital_expenditure": ["capital_expenditure", "capex", "purchases_of_ppe", "dau_tu_tai_san_co_dinh"],

    # Financial Ratios
    "roe": ["roe", "return_on_equity", "ty_suat_loi_nhuan_von_chu"],
    "roa": ["roa", "return_on_assets", "ty_suat_loi_nhuan_tai_san"],
    "pe": ["pe", "price_to_earnings", "p_e_ratio", "he_so_gia_loi_nhuan"],
    "pb": ["pb", "price_to_book", "p_b_ratio", "he_so_gia_so_sach"],
    "eps": ["eps", "earnings_per_share", "loi_nhuan_co_phieu"],
    "dividend_yield": ["dividend_yield", "ty_suat_co_tuc"],
    "current_ratio": ["current_ratio", "ty_so_thanh_toan_hien_hanh"],
    "debt_to_equity": ["debt_to_equity", "d_e_ratio", "ty_le_no_von_chu"],

    # Banking-specific
    "net_interest_income": ["net_interest_income", "thu_nhap_lai_thuan"],
    "total_loans": ["total_loans", "du_no_cho_vay", "loans_and_advances"],
    "total_deposits": ["total_deposits", "tien_gui_khach_hang"],
    "npl_ratio": ["npl_ratio", "bad_debt_ratio", "ty_le_no_xau"],
    "car": ["car", "capital_adequacy_ratio", "ty_le_an_toan_von"],
}


def get_value(data: dict[str, Any], key: str, default: float | None = None) -> float | None:
    """Lấy giá trị từ dict với column alias resolution.

    Thử tên chuẩn trước, sau đó thử các alias theo thứ tự ưu tiên.

    Args:
        data: Dict chứa dữ liệu tài chính
        key: Tên cột chuẩn
        default: Giá trị mặc định nếu không tìm thấy

    Returns:
        Giá trị float hoặc default
    """
    # Try exact key first
    val = data.get(key)
    if val is not None:
        try:
            return float(val)
        except (TypeError, ValueError):
            pass

    # Try aliases
    aliases = COLUMN_ALIASES.get(key, [])
    for alias in aliases:
        val = data.get(alias)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                continue

    return default


def safe_divide(
    numerator: float | None,
    denominator: float | None,
    default: float | None = None,
) -> float | None:
    """Chia an toàn, xử lý None và division by zero."""
    if numerator is None or denominator is None:
        return default
    if denominator == 0:
        return default
    return numerator / denominator


def normalize_financial_data(data: dict[str, Any]) -> dict[str, float | None]:
    """Normalize financial data dict using column aliases.

    Returns a new dict with standardized column names.
    """
    normalized: dict[str, float | None] = {}
    for standard_key in COLUMN_ALIASES:
        normalized[standard_key] = get_value(data, standard_key)
    return normalized


def calculate_free_cash_flow(cash_flow: dict[str, Any]) -> float | None:
    """Tính Free Cash Flow = OCF - |CapEx|."""
    ocf = get_value(cash_flow, "operating_cash_flow")
    capex = get_value(cash_flow, "capital_expenditure")
    if ocf is None:
        return None
    if capex is None:
        return ocf
    return ocf - abs(capex)
