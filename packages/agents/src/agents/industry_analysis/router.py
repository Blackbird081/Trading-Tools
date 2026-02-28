"""Industry Router — tự động chọn module phân tích theo ngành.

★ Inspired by baocaotaichinh-/webapp/analysis/industry_router.py.
★ Map ICB industry codes/names → analysis module.
★ Dùng trong FundamentalAgent để chọn đúng phân tích theo ngành.
"""

from __future__ import annotations

from typing import Any

# Mapping ICB industry names → analysis type
INDUSTRY_MAPPING: dict[str, str] = {
    # Banking
    "banking": "banking",
    "ngân hàng": "banking",
    "banks": "banking",
    "dịch vụ tài chính": "banking",
    "financial services": "banking",
    "tài chính": "banking",

    # Real Estate
    "bất động sản": "realestate",
    "real estate": "realestate",
    "realty": "realestate",
    "property": "realestate",
    "phát triển bất động sản": "realestate",

    # Technology
    "công nghệ": "technology",
    "technology": "technology",
    "software": "technology",
    "phần mềm": "technology",
    "it services": "technology",
    "dịch vụ công nghệ": "technology",

    # Manufacturing
    "sản xuất": "manufacturing",
    "manufacturing": "manufacturing",
    "công nghiệp": "manufacturing",
    "thép": "manufacturing",
    "steel": "manufacturing",
    "xi măng": "manufacturing",
    "cement": "manufacturing",
    "hóa chất": "manufacturing",
    "chemicals": "manufacturing",

    # Retail
    "bán lẻ": "retail",
    "retail": "retail",
    "thương mại": "retail",
    "trading": "retail",
    "wholesale": "retail",

    # Consumer
    "tiêu dùng": "consumer",
    "consumer": "consumer",
    "thực phẩm": "consumer",
    "food": "consumer",
    "đồ uống": "consumer",
    "beverages": "consumer",

    # Energy
    "năng lượng": "energy",
    "energy": "energy",
    "dầu khí": "oilgas",
    "oil gas": "oilgas",
    "điện": "utilities",
    "utilities": "utilities",
    "tiện ích": "utilities",

    # Healthcare
    "y tế": "healthcare",
    "healthcare": "healthcare",
    "dược phẩm": "pharmaceutical",
    "pharmaceutical": "pharmaceutical",

    # Transportation
    "vận tải": "transportation",
    "transportation": "transportation",
    "hàng không": "aviation",
    "aviation": "aviation",
    "logistics": "transportation",

    # Insurance
    "bảo hiểm": "insurance",
    "insurance": "insurance",
}

# ICB Level 3 code → industry type
ICB_CODE_MAPPING: dict[str, str] = {
    "8300": "banking",      # Banks
    "8350": "banking",      # Financial Services
    "8500": "insurance",    # Insurance
    "8600": "realestate",   # Real Estate
    "9500": "technology",   # Technology
    "2700": "consumer",     # Food & Beverage
    "3700": "healthcare",   # Healthcare
    "5700": "utilities",    # Utilities
    "0500": "oilgas",       # Oil & Gas
    "1300": "manufacturing", # Chemicals
    "1700": "manufacturing", # Construction & Materials
    "2300": "consumer",     # Personal & Household Goods
    "3300": "retail",       # Retail
    "5300": "transportation", # Industrial Transportation
    "5500": "transportation", # Industrial Engineering
}


def route_industry(
    icb_name: str | None = None,
    icb_code: str | None = None,
) -> str:
    """Xác định loại phân tích dựa trên ngành ICB.

    Args:
        icb_name: Tên ngành ICB (tiếng Việt hoặc tiếng Anh)
        icb_code: Mã ngành ICB (4 chữ số)

    Returns:
        Loại phân tích: "banking", "realestate", "technology", "manufacturing",
                        "retail", "consumer", "energy", "healthcare", "general"
    """
    # Try ICB code first
    if icb_code:
        # Try exact match
        if icb_code in ICB_CODE_MAPPING:
            return ICB_CODE_MAPPING[icb_code]
        # Try prefix match (first 2 digits)
        prefix = icb_code[:2]
        for code, industry in ICB_CODE_MAPPING.items():
            if code.startswith(prefix):
                return industry

    # Try name match
    if icb_name:
        name_lower = icb_name.lower().strip()
        # Exact match
        if name_lower in INDUSTRY_MAPPING:
            return INDUSTRY_MAPPING[name_lower]
        # Partial match
        for key, industry in INDUSTRY_MAPPING.items():
            if key in name_lower or name_lower in key:
                return industry

    return "general"


def get_analysis_description(industry_type: str) -> str:
    """Mô tả loại phân tích."""
    descriptions = {
        "banking": "Phân tích ngân hàng: NIM, NPL, CAR, LDR, CIR",
        "realestate": "Phân tích BĐS: Inventory/Assets, D/E, Gross Margin, Thanh khoản",
        "technology": "Phân tích công nghệ: R&D/Revenue, Rule of 40, Recurring Revenue",
        "manufacturing": "Phân tích sản xuất: Asset Utilization, Inventory Turnover, EBITDA Margin",
        "retail": "Phân tích bán lẻ: Same-Store Sales, Inventory Days, Gross Margin",
        "consumer": "Phân tích tiêu dùng: Brand Value, Market Share, Pricing Power",
        "energy": "Phân tích năng lượng: EBITDA/MW, Capacity Factor, Fuel Cost",
        "oilgas": "Phân tích dầu khí: Reserve Replacement, Finding Cost, Lifting Cost",
        "utilities": "Phân tích tiện ích: EBITDA/MW, Capacity Factor, Regulatory Risk",
        "healthcare": "Phân tích y tế: R&D Pipeline, Gross Margin, Regulatory Approval",
        "pharmaceutical": "Phân tích dược phẩm: R&D/Revenue, Patent Cliff, Generic Competition",
        "insurance": "Phân tích bảo hiểm: Combined Ratio, Loss Ratio, Investment Yield",
        "aviation": "Phân tích hàng không: Load Factor, RASK/CASK, Fleet Utilization",
        "transportation": "Phân tích vận tải: Asset Utilization, Revenue/km, Operating Ratio",
        "general": "Phân tích tổng quát: ROE, ROA, P/E, P/B, Debt/Equity",
    }
    return descriptions.get(industry_type, descriptions["general"])
