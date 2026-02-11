from __future__ import annotations

import logging
import random
from datetime import date, timedelta

from fastapi import APIRouter, Path

logger = logging.getLogger("interface.company")

router = APIRouter()


# ── Company static database (mock) ──────────────────────────────
_COMPANY_DB: dict[str, dict[str, object]] = {
    "ACB": {
        "name": "Ngân hàng TMCP Á Châu",
        "english_name": "Asia Commercial Joint Stock Bank",
        "exchange": "HOSE",
        "industry": "Ngân hàng",
        "sector": "Tài chính",
        "founded": "1993-06-04",
        "listed_date": "2006-11-21",
        "address": "442 Nguyễn Thị Minh Khai, P.5, Q.3, TP.HCM",
        "website": "https://acb.com.vn",
        "employees": 14500,
        "outstanding_shares": 3_869_000_000,
        "market_cap": 142_500_000_000_000,
    },
    "FPT": {
        "name": "CTCP FPT",
        "english_name": "FPT Corporation",
        "exchange": "HOSE",
        "industry": "Công nghệ thông tin",
        "sector": "Công nghệ",
        "founded": "1988-09-13",
        "listed_date": "2006-12-13",
        "address": "Tòa nhà FPT Cầu Giấy, 10 Phạm Văn Bạch, Cầu Giấy, Hà Nội",
        "website": "https://fpt.com.vn",
        "employees": 72000,
        "outstanding_shares": 1_370_000_000,
        "market_cap": 189_000_000_000_000,
    },
    "VNM": {
        "name": "CTCP Sữa Việt Nam",
        "english_name": "Vietnam Dairy Products JSC",
        "exchange": "HOSE",
        "industry": "Thực phẩm & Đồ uống",
        "sector": "Tiêu dùng",
        "founded": "1976-08-20",
        "listed_date": "2006-01-19",
        "address": "10 Tân Trào, Q.7, TP.HCM",
        "website": "https://vinamilk.com.vn",
        "employees": 9800,
        "outstanding_shares": 2_089_000_000,
        "market_cap": 145_000_000_000_000,
    },
    "VCB": {
        "name": "Ngân hàng TMCP Ngoại thương Việt Nam",
        "english_name": "Joint Stock Commercial Bank for Foreign Trade of Vietnam",
        "exchange": "HOSE",
        "industry": "Ngân hàng",
        "sector": "Tài chính",
        "founded": "1963-04-01",
        "listed_date": "2009-06-30",
        "address": "198 Trần Quang Khải, Q.1, TP.HCM",
        "website": "https://vietcombank.com.vn",
        "employees": 22000,
        "outstanding_shares": 5_348_000_000,
        "market_cap": 490_000_000_000_000,
    },
    "HPG": {
        "name": "CTCP Tập đoàn Hòa Phát",
        "english_name": "Hoa Phat Group JSC",
        "exchange": "HOSE",
        "industry": "Thép & Vật liệu",
        "sector": "Công nghiệp",
        "founded": "1992-08-15",
        "listed_date": "2007-11-15",
        "address": "66 Nguyễn Du, Q. Hai Bà Trưng, Hà Nội",
        "website": "https://hoaphat.com.vn",
        "employees": 34000,
        "outstanding_shares": 5_856_000_000,
        "market_cap": 160_000_000_000_000,
    },
    "MBB": {
        "name": "Ngân hàng TMCP Quân đội",
        "english_name": "Military Commercial Joint Stock Bank",
        "exchange": "HOSE",
        "industry": "Ngân hàng",
        "sector": "Tài chính",
        "founded": "1994-11-04",
        "listed_date": "2011-11-01",
        "address": "21 Cát Linh, Đống Đa, Hà Nội",
        "website": "https://mbbank.com.vn",
        "employees": 16000,
        "outstanding_shares": 5_246_000_000,
        "market_cap": 130_000_000_000_000,
    },
    "MSN": {
        "name": "CTCP Tập đoàn Masan",
        "english_name": "Masan Group Corporation",
        "exchange": "HOSE",
        "industry": "Tiêu dùng đa ngành",
        "sector": "Tiêu dùng",
        "founded": "2004-11-18",
        "listed_date": "2009-11-05",
        "address": "Suite 802, Central Plaza, 17 Lê Duẩn, Q.1, TP.HCM",
        "website": "https://masangroup.com",
        "employees": 40000,
        "outstanding_shares": 1_490_000_000,
        "market_cap": 95_000_000_000_000,
    },
    "VIC": {
        "name": "Tập đoàn Vingroup",
        "english_name": "Vingroup Joint Stock Company",
        "exchange": "HOSE",
        "industry": "Bất động sản",
        "sector": "Bất động sản",
        "founded": "1993-08-08",
        "listed_date": "2007-09-28",
        "address": "7 Bùi Thị Xuân, Hai Bà Trưng, Hà Nội",
        "website": "https://vingroup.net",
        "employees": 58000,
        "outstanding_shares": 3_890_000_000,
        "market_cap": 165_000_000_000_000,
    },
}

_INDUSTRIES = [
    "Ngân hàng",
    "Công nghệ thông tin",
    "Thực phẩm & Đồ uống",
    "Thép & Vật liệu",
    "Bất động sản",
    "Tiêu dùng đa ngành",
    "Năng lượng",
    "Bảo hiểm",
    "Chứng khoán",
    "Dầu khí",
    "Vận tải",
    "Dược phẩm",
    "Dệt may",
    "Hóa chất",
]


def _generate_profile(symbol: str) -> dict[str, object]:
    """Generate or return company profile data."""
    if symbol in _COMPANY_DB:
        return _COMPANY_DB[symbol]

    # Auto-generate for unknown symbols
    rng = random.Random(hash(symbol))
    industry = rng.choice(_INDUSTRIES)
    return {
        "name": f"CTCP {symbol}",
        "english_name": f"{symbol} Corporation",
        "exchange": rng.choice(["HOSE", "HNX", "UPCOM"]),
        "industry": industry,
        "sector": industry.split(" ")[0],
        "founded": f"{rng.randint(1990, 2020)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
        "listed_date": (
            f"{rng.randint(2005, 2023)}-{rng.randint(1, 12):02d}"
            f"-{rng.randint(1, 28):02d}"
        ),
        "address": "Việt Nam",
        "website": f"https://{symbol.lower()}.com.vn",
        "employees": rng.randint(200, 50000),
        "outstanding_shares": rng.randint(50_000_000, 6_000_000_000),
        "market_cap": rng.randint(1_000_000_000_000, 500_000_000_000_000),
    }


def _generate_financials(symbol: str) -> dict[str, object]:
    """Generate mock financial data."""
    rng = random.Random(hash(symbol + "fin"))

    # Quarterly revenue & profit
    quarters: list[dict[str, object]] = []
    base_rev = rng.uniform(500, 50000)
    for year in range(2022, 2026):
        for q in range(1, 5):
            rev = round(base_rev * rng.uniform(0.85, 1.25), 1)
            profit = round(rev * rng.uniform(0.05, 0.35), 1)
            quarters.append(
                {
                    "period": f"Q{q}/{year}",
                    "revenue": rev,
                    "net_profit": profit,
                    "eps": round(profit / rng.uniform(1, 6), 0),
                    "roe": round(rng.uniform(5, 30), 1),
                }
            )
        base_rev *= rng.uniform(1.0, 1.15)

    return {
        "pe_ratio": round(rng.uniform(5, 35), 1),
        "pb_ratio": round(rng.uniform(0.5, 5.0), 2),
        "eps_ttm": round(rng.uniform(500, 8000), 0),
        "roe_ttm": round(rng.uniform(5, 35), 1),
        "roa_ttm": round(rng.uniform(0.5, 15), 1),
        "debt_to_equity": round(rng.uniform(0.1, 8.0), 2),
        "current_ratio": round(rng.uniform(0.5, 3.0), 2),
        "dividend_yield": round(rng.uniform(0, 8), 1),
        "beta": round(rng.uniform(0.3, 1.8), 2),
        "revenue_ttm": round(base_rev * 4 * rng.uniform(0.9, 1.1), 1),
        "profit_ttm": round(
            base_rev * 4 * rng.uniform(0.05, 0.25),
            1,
        ),
        "quarterly": quarters[-8:],  # last 8 quarters
    }


def _generate_technicals(symbol: str) -> dict[str, object]:
    """Generate mock technical indicators."""
    rng = random.Random(hash(symbol + "tech"))
    price = rng.uniform(10, 180)
    return {
        "rsi_14": round(rng.uniform(20, 80), 1),
        "macd": round(rng.uniform(-3, 3), 2),
        "macd_signal": round(rng.uniform(-2, 2), 2),
        "ma_20": round(price * rng.uniform(0.95, 1.05), 2),
        "ma_50": round(price * rng.uniform(0.90, 1.10), 2),
        "ma_200": round(price * rng.uniform(0.80, 1.20), 2),
        "bollinger_upper": round(price * 1.05, 2),
        "bollinger_lower": round(price * 0.95, 2),
        "atr_14": round(rng.uniform(0.5, 5.0), 2),
        "adx": round(rng.uniform(10, 60), 1),
        "cci": round(rng.uniform(-200, 200), 0),
        "stochastic_k": round(rng.uniform(10, 90), 1),
        "stochastic_d": round(rng.uniform(15, 85), 1),
        "obv_trend": rng.choice(["bullish", "bearish", "neutral"]),
        "support": round(price * 0.93, 2),
        "resistance": round(price * 1.07, 2),
    }


def _generate_ownership(symbol: str) -> dict[str, object]:
    """Generate mock ownership breakdown."""
    rng = random.Random(hash(symbol + "own"))
    foreign = round(rng.uniform(5, 49), 1)
    insider = round(rng.uniform(10, 60), 1)
    state = round(rng.uniform(0, 30), 1)
    free_float = round(max(100 - foreign - insider - state, 5), 1)

    top_holders: list[dict[str, object]] = []
    holder_names = [
        "SCIC",
        "Dragon Capital",
        "VinaCapital",
        "Samsung Fund",
        "Korea Investment",
        "Chủ tịch HĐQT",
        "PYN Elite Fund",
        "Norges Bank",
        "JP Morgan",
        "Templeton",
    ]
    for name in rng.sample(holder_names, 5):
        top_holders.append(
            {
                "name": name,
                "shares": rng.randint(1_000_000, 200_000_000),
                "pct": round(rng.uniform(0.5, 15), 2),
            }
        )
    top_holders.sort(key=lambda x: float(str(x["pct"])), reverse=True)

    return {
        "foreign_pct": foreign,
        "insider_pct": insider,
        "state_pct": state,
        "free_float_pct": free_float,
        "foreign_room_remaining": round(rng.uniform(0, 30), 1),
        "top_holders": top_holders,
    }


def _generate_news(symbol: str) -> list[dict[str, object]]:
    """Generate mock news items."""
    rng = random.Random(hash(symbol + "news"))
    templates = [
        "{sym}: Doanh thu quý tăng {pct}% so với cùng kỳ",
        "{sym} công bố kế hoạch phát hành thêm cổ phiếu",
        "Khối ngoại mua ròng {sym} phiên thứ {n}",
        "{sym}: Lợi nhuận vượt kỳ vọng, cổ phiếu tăng mạnh",
        "HĐQT {sym} thông qua kế hoạch cổ tức {pct}%",
        "{sym} ký hợp đồng lớn trị giá {val} tỷ đồng",
        "Phân tích kỹ thuật {sym}: Tín hiệu tích cực trung hạn",
        "{sym} mở rộng thị trường sang {market}",
        "CEO {sym} trả lời về chiến lược tăng trưởng 2026",
        "{sym}: Dự phóng EPS 2026 đạt {val} đồng",
    ]
    markets = ["Nhật Bản", "Hàn Quốc", "Mỹ", "Châu Âu", "Đông Nam Á"]
    news: list[dict[str, object]] = []
    for i in range(8):
        tpl = rng.choice(templates)
        d = date.today() - timedelta(days=i * rng.randint(1, 5))
        news.append(
            {
                "title": tpl.format(
                    sym=symbol,
                    pct=rng.randint(5, 45),
                    n=rng.randint(3, 15),
                    val=rng.randint(100, 5000),
                    market=rng.choice(markets),
                ),
                "date": d.isoformat(),
                "source": rng.choice(
                    [
                        "CafeF",
                        "VnExpress",
                        "VietStock",
                        "TCBS",
                        "SSI Research",
                        "VNDS",
                    ]
                ),
                "sentiment": rng.choice(["positive", "negative", "neutral"]),
            }
        )
    return news


@router.get("/company/{symbol}")
async def get_company_profile(
    symbol: str = Path(..., description="Stock symbol"),
) -> dict[str, object]:
    """Get comprehensive company profile."""
    symbol = symbol.upper()
    return {
        "symbol": symbol,
        "profile": _generate_profile(symbol),
        "financials": _generate_financials(symbol),
        "technicals": _generate_technicals(symbol),
        "ownership": _generate_ownership(symbol),
        "news": _generate_news(symbol),
    }
