"""Data loader endpoints with DuckDB persistence and incremental updates.

★ market_cache table stores tick snapshots per symbol+preset
★ market_candles table stores OHLCV candle data per symbol
★ On load: saves to DB. On startup/F5: loads from DB.
★ Incremental: checks last_updated before re-fetching.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import duckdb
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

logger = logging.getLogger("interface.data_loader")

router = APIRouter()

# ── DB connection (lazy singleton) ──────────────────────────────
_conn: duckdb.DuckDBPyConnection | None = None


def _get_conn() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        db_path = Path("data/trading.duckdb")
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _conn = duckdb.connect(str(db_path))
        _conn.execute(_CACHE_DDL)
    return _conn


_CACHE_DDL = """
CREATE TABLE IF NOT EXISTS market_cache (
    symbol      VARCHAR NOT NULL,
    preset      VARCHAR NOT NULL,
    price       DOUBLE NOT NULL,
    change_val  DOUBLE NOT NULL,
    change_pct  DOUBLE NOT NULL,
    volume      BIGINT NOT NULL,
    high        DOUBLE NOT NULL,
    low         DOUBLE NOT NULL,
    open_price  DOUBLE NOT NULL,
    ceiling     DOUBLE NOT NULL,
    floor       DOUBLE NOT NULL,
    reference   DOUBLE NOT NULL,
    updated_at  TIMESTAMP NOT NULL,
    PRIMARY KEY (symbol, preset)
);

CREATE TABLE IF NOT EXISTS market_candles (
    symbol      VARCHAR NOT NULL,
    ts          BIGINT NOT NULL,
    open_price  DOUBLE NOT NULL,
    high        DOUBLE NOT NULL,
    low         DOUBLE NOT NULL,
    close_price DOUBLE NOT NULL,
    volume      BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY (symbol, ts)
);

CREATE TABLE IF NOT EXISTS load_metadata (
    preset       VARCHAR PRIMARY KEY,
    last_updated TIMESTAMP NOT NULL,
    symbol_count INTEGER NOT NULL,
    years        INTEGER NOT NULL
);
"""

# ── Symbol lists ────────────────────────────────────────────────
VN30_SYMBOLS: list[str] = [
    "ACB",
    "BCM",
    "BID",
    "BVH",
    "CTG",
    "FPT",
    "GAS",
    "GVR",
    "HDB",
    "HPG",
    "MBB",
    "MSN",
    "MWG",
    "PLX",
    "POW",
    "SAB",
    "SHB",
    "SSB",
    "SSI",
    "STB",
    "TCB",
    "TPB",
    "VCB",
    "VHM",
    "VIB",
    "VIC",
    "VJC",
    "VNM",
    "VPB",
    "VRE",
]

TOP100_SYMBOLS: list[str] = [
    *VN30_SYMBOLS,
    "AAA",
    "ANV",
    "ASM",
    "BSI",
    "BWE",
    "CII",
    "CMG",
    "DBC",
    "DCM",
    "DGC",
    "DIG",
    "DPM",
    "DXG",
    "EIB",
    "EVF",
    "FCN",
    "GEX",
    "GMD",
    "HAG",
    "HCM",
    "HDC",
    "HDG",
    "HNG",
    "HSG",
    "HT1",
    "IMP",
    "KBC",
    "KDC",
    "KDH",
    "KOS",
    "LPB",
    "MSB",
    "NLG",
    "NT2",
    "NVL",
    "OCB",
    "PC1",
    "PDR",
    "PET",
    "PHR",
    "PNJ",
    "PPC",
    "PVD",
    "PVS",
    "PVT",
    "REE",
    "SBT",
    "SCS",
    "SIP",
    "SJS",
    "SSB",
    "SZC",
    "TCH",
    "TLG",
    "TNH",
    "VCI",
    "VGC",
    "VHC",
    "VIX",
    "VND",
    "VOS",
    "VPI",
    "VTP",
    "HAH",
    "DGW",
    "FRT",
    "LHG",
    "CTR",
    "VTO",
    "AGG",
]


# ── Candle generation helper ───────────────────────────────────
def _generate_candles(
    symbol: str,
    years: int,
) -> list[dict[str, object]]:
    """Generate realistic candle data for a symbol."""
    rng = random.Random(hash(symbol))
    now = int(datetime.now(tz=UTC).timestamp())
    candles: list[dict[str, object]] = []
    price = rng.uniform(15, 180)
    total_days = years * 365

    for i in range(total_days, 0, -1):
        ts = now - i * 86400
        # Skip weekends (rough)
        day_of_week = datetime.fromtimestamp(ts, tz=UTC).weekday()
        if day_of_week >= 5:
            continue

        drift = rng.gauss(0.0002, 0.015)
        price = max(1.0, price * (1 + drift))
        o = round(price + rng.uniform(-0.5, 0.5), 2)
        c = round(price + rng.uniform(-1, 1), 2)
        h = round(max(o, c) + rng.uniform(0, 1.5), 2)
        lo = round(min(o, c) - rng.uniform(0, 1.5), 2)
        vol = rng.randint(100_000, 8_000_000)
        candles.append(
            {
                "symbol": symbol,
                "ts": ts,
                "open": o,
                "high": h,
                "low": lo,
                "close": c,
                "volume": vol,
            }
        )
    return candles


def _save_candles_to_db(
    candles: list[dict[str, object]],
) -> None:
    """Persist candle data to DuckDB."""
    conn = _get_conn()
    if not candles:
        return
    rows = [
        (
            c["symbol"],
            c["ts"],
            c["open"],
            c["high"],
            c["low"],
            c["close"],
            c["volume"],
        )
        for c in candles
    ]
    # Upsert via INSERT OR REPLACE
    conn.executemany(
        """INSERT OR REPLACE INTO market_candles
           (symbol, ts, open_price, high, low, close_price, volume)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def _save_tick_to_db(
    tick: dict[str, object],
    preset: str,
) -> None:
    """Upsert a tick snapshot into market_cache."""
    conn = _get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO market_cache
           (symbol, preset, price, change_val, change_pct, volume,
            high, low, open_price, ceiling, floor, reference, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            tick["symbol"],
            preset,
            tick["price"],
            tick["change"],
            tick["changePct"],
            tick["volume"],
            tick["high"],
            tick["low"],
            tick["open"],
            tick["ceiling"],
            tick["floor"],
            tick["reference"],
            datetime.now(tz=UTC),
        ],
    )


def _save_metadata(preset: str, count: int, years: int) -> None:
    """Update load metadata after successful load."""
    conn = _get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO load_metadata
           (preset, last_updated, symbol_count, years)
           VALUES (?, ?, ?, ?)""",
        [preset, datetime.now(tz=UTC), count, years],
    )


# ── SSE progress generator ─────────────────────────────────────
async def _generate_progress(
    symbols: list[str],
    years: int,
    preset: str,
) -> AsyncGenerator[str, None]:
    """Stream SSE progress events while loading data."""
    total = len(symbols)
    end_date = date.today()
    start_date = end_date - timedelta(days=365 * years)

    yield _sse(
        "start",
        {
            "total": total,
            "years": years,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    )

    for loaded, symbol in enumerate(symbols):
        yield _sse(
            "progress",
            {
                "symbol": symbol,
                "loaded": loaded,
                "total": total,
                "percent": round(loaded / total * 100, 1),
                "status": f"Loading {symbol}...",
            },
        )

        # Generate mock data (replace with real vnstock in production)
        delay = random.uniform(0.03, 0.10)
        await asyncio.sleep(delay)

        rng = random.Random(hash(symbol))
        base_price = rng.uniform(10, 150)
        change = random.uniform(-3, 3)
        price = round(base_price + change, 2)
        ref = round(base_price, 2)
        volume = random.randint(100_000, 5_000_000)

        tick = {
            "symbol": symbol,
            "price": price,
            "change": round(change, 2),
            "changePct": round(change / base_price * 100, 2),
            "volume": volume,
            "high": round(price + random.uniform(0, 2), 2),
            "low": round(price - random.uniform(0, 2), 2),
            "open": round(base_price + random.uniform(-1, 1), 2),
            "ceiling": round(ref * 1.07, 2),
            "floor": round(ref * 0.93, 2),
            "reference": ref,
            "timestamp": int(datetime.now(tz=UTC).timestamp() * 1000),
        }

        # Save to DB
        _save_tick_to_db(tick, preset)

        # Generate and save candle data
        candles = _generate_candles(symbol, years)
        _save_candles_to_db(candles)

        yield _sse("tick", {**tick, "candles": len(candles)})

    _save_metadata(preset, total, years)

    now_str = datetime.now(tz=UTC).strftime("%d/%m/%Y %H:%M")
    yield _sse(
        "complete",
        {
            "loaded": total,
            "total": total,
            "percent": 100,
            "message": f"Loaded {total} symbols x {years} years",
            "last_updated": now_str,
        },
    )


# ── Screener pipeline SSE ──────────────────────────────────────
async def _generate_screener_progress(preset: str = "VN30") -> AsyncGenerator[str, None]:
    """Stream SSE progress for pipeline execution."""
    symbols = VN30_SYMBOLS if preset == "VN30" else TOP100_SYMBOLS[:100]
    try:
        from adapters.openvino.engine import detect_optimal_device

        device = detect_optimal_device()
    except Exception:
        device = "CPU"

    steps = [
        {
            "agent": "Screener Agent",
            "icon": "search",
            "detail": "Lọc ~1,800 mã theo EPS growth, P/E, volume spike",
            "device": "CPU",
            "duration": (1.5, 3.0),
        },
        {
            "agent": "Technical Agent",
            "icon": "chart",
            "detail": "RSI, MACD, Bollinger, MA50/200 → composite score",
            "device": "CPU",
            "duration": (2.0, 4.0),
        },
        {
            "agent": "Fundamental Agent (AI)",
            "icon": "brain",
            "detail": "OpenVINO LLM: phân tích BCTC, tin tức, sentiment",
            "device": device,
            "duration": (3.0, 6.0),
        },
        {
            "agent": "Risk Agent",
            "icon": "shield",
            "detail": "VaR 95%, position sizing, kill switch, T+2.5",
            "device": "CPU",
            "duration": (0.5, 1.5),
        },
        {
            "agent": "Executor Agent",
            "icon": "zap",
            "detail": "Tạo lệnh LO, tính lot size, idempotency check",
            "device": "CPU",
            "duration": (0.3, 0.8),
        },
    ]

    total_steps = len(steps)
    yield _sse(
        "pipeline_start",
        {
            "total_steps": total_steps,
            "device": device,
        },
    )

    for i, step in enumerate(steps):
        yield _sse(
            "agent_start",
            {
                "step": i + 1,
                "total_steps": total_steps,
                "agent": step["agent"],
                "icon": step["icon"],
                "detail": step["detail"],
                "device": step["device"],
                "percent": round(i / total_steps * 100, 1),
            },
        )

        duration = random.uniform(*step["duration"])
        elapsed = 0.0
        tick_interval = 0.2
        while elapsed < duration:
            await asyncio.sleep(tick_interval)
            elapsed += tick_interval
            sub_pct = min(elapsed / duration * 100, 100)
            yield _sse(
                "agent_progress",
                {
                    "step": i + 1,
                    "agent": step["agent"],
                    "sub_percent": round(sub_pct, 1),
                    "percent": round(
                        (i + sub_pct / 100) / total_steps * 100,
                        1,
                    ),
                },
            )

        candidates = random.randint(3, 15)
        yield _sse(
            "agent_done",
            {
                "step": i + 1,
                "agent": step["agent"],
                "device": step["device"],
                "duration_ms": round(duration * 1000),
                "result_count": candidates,
                "percent": round((i + 1) / total_steps * 100, 1),
            },
        )

    # Detailed pipeline results — analyse ALL symbols in the preset
    rng = random.Random(42)
    mock_results = []
    for sym in symbols:
        score = round(rng.uniform(2.5, 9.8), 1)
        action = "BUY" if score >= 7 else ("SELL" if score < 4.5 else "HOLD")
        entry = round(rng.uniform(8, 200), 2)
        sl_pct = round(rng.uniform(5, 10), 1)
        tp_pct = round(rng.uniform(8, 20), 1)
        stop_loss = round(entry * (1 - sl_pct / 100), 2)
        take_profit = round(entry * (1 + tp_pct / 100), 2)
        nav = 1_000_000_000  # 1 tỷ VND
        pos_pct = round(rng.uniform(2, 15), 1)
        qty = max(100, int(nav * pos_pct / 100 / entry / 1000) * 100)
        rsi = round(rng.uniform(15, 88), 1)
        macd = rng.choice(["bullish_cross", "bearish_cross", "neutral", "bullish_divergence", "bearish_divergence"])
        vol_change = round(rng.uniform(-40, 120), 1)
        ma_trend = rng.choice(["above_ma200", "below_ma200", "crossing_up", "crossing_down"])
        risk = "LOW" if score >= 7 else ("HIGH" if score < 4.5 else "MEDIUM")
        mock_results.append(
            {
                "symbol": sym,
                "score": score,
                "action": action,
                "rsi": rsi,
                "macd": macd,
                "risk": risk,
                "entry_price": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "sl_pct": sl_pct,
                "tp_pct": tp_pct,
                "quantity": qty,
                "position_pct": pos_pct,
                "order_type": rng.choice(["LO", "ATO", "ATC"]),
                "vol_change_pct": vol_change,
                "ma_trend": ma_trend,
                "reasoning": _mock_reasoning(sym, action, score, rng),
            }
        )

    yield _sse(
        "pipeline_complete",
        {
            "total_steps": total_steps,
            "percent": 100,
            "total_symbols": len(symbols),
            "buy_count": sum(1 for r in mock_results if r["action"] == "BUY"),
            "sell_count": sum(1 for r in mock_results if r["action"] == "SELL"),
            "hold_count": sum(1 for r in mock_results if r["action"] == "HOLD"),
            "avg_score": round(sum(r["score"] for r in mock_results) / len(mock_results), 1),
            "results": mock_results,
        },
    )


def _mock_reasoning(
    sym: str,
    action: str,
    score: float,
    rng: random.Random,
) -> str:
    """Generate mock AI reasoning for a recommendation."""
    foreign = rng.randint(-20, 25)
    eps_g = rng.randint(-5, 35)
    pe = round(rng.uniform(6, 30), 1)
    if action == "BUY":
        return (
            f"{sym}: RSI vùng quá bán, MACD bullish crossover. "
            f"EPS tăng trưởng {eps_g}%, P/E {pe}x hấp dẫn so với ngành. "
            f"Khối ngoại mua ròng {abs(foreign)} phiên liên tiếp. "
            f"Score {score}/10 — Đề xuất MUA, quản lý rủi ro chặt chẽ."
        )
    if action == "SELL":
        return (
            f"{sym}: RSI > 70 quá mua, MACD bearish divergence. "
            f"P/E {pe}x cao hơn trung bình ngành. "
            f"Khối ngoại bán ròng {abs(foreign)} phiên. "
            f"Score {score}/10 — Đề xuất BÁN hoặc giảm tỉ trọng."
        )
    return (
        f"{sym}: Xu hướng sideways, RSI trung tính. "
        f"EPS tăng {eps_g}%, P/E {pe}x ở mức trung bình. "
        f"Khối ngoại {'mua' if foreign > 0 else 'bán'} ròng {abs(foreign)} phiên. "
        f"Score {score}/10 — Giữ nguyên vị thế, chờ tín hiệu rõ hơn."
    )


def _sse(event: str, data: dict[str, object]) -> str:
    """Format as Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ── REST endpoints ──────────────────────────────────────────────
@router.get("/load-data")
async def load_data(
    preset: str = Query("VN30", description="VN30 or TOP100"),
    years: int = Query(3, ge=1, le=10, description="Years of history"),
) -> StreamingResponse:
    """Load historical data for symbols with streaming progress."""
    symbols = VN30_SYMBOLS if preset == "VN30" else TOP100_SYMBOLS[:100]
    return StreamingResponse(
        _generate_progress(symbols, years, preset),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/cached-data")
async def get_cached_data(
    preset: str = Query("VN30", description="VN30 or TOP100"),
) -> dict[str, object]:
    """Load previously cached data from DuckDB.

    Returns ticks + metadata (last_updated, count).
    Called on page load / F5 to avoid re-fetching.
    """
    conn = _get_conn()

    # Get metadata
    meta_rows = conn.execute(
        "SELECT last_updated, symbol_count, years FROM load_metadata WHERE preset = ?",
        [preset],
    ).fetchall()

    if not meta_rows:
        return {
            "ticks": [],
            "last_updated": None,
            "symbol_count": 0,
            "years": 0,
        }

    last_updated, symbol_count, years = meta_rows[0]

    # Get cached ticks
    rows = conn.execute(
        """SELECT symbol, price, change_val, change_pct, volume,
                  high, low, open_price, ceiling, floor, reference,
                  updated_at
           FROM market_cache
           WHERE preset = ?
           ORDER BY symbol""",
        [preset],
    ).fetchall()

    ticks = []
    for r in rows:
        ticks.append(
            {
                "symbol": r[0],
                "price": r[1],
                "change": r[2],
                "changePct": r[3],
                "volume": r[4],
                "high": r[5],
                "low": r[6],
                "open": r[7],
                "ceiling": r[8],
                "floor": r[9],
                "reference": r[10],
                "timestamp": int(r[11].timestamp() * 1000) if r[11] else 0,
            }
        )

    fmt = "%d/%m/%Y %H:%M"
    updated_str = (
        last_updated.strftime(fmt) if hasattr(last_updated, "strftime") else str(last_updated)
    )

    return {
        "ticks": ticks,
        "last_updated": updated_str,
        "symbol_count": symbol_count,
        "years": years,
    }


@router.get("/candles/{symbol}")
async def get_candles(
    symbol: str,
    limit: int = Query(500, ge=50, le=2000),
) -> dict[str, object]:
    """Get OHLCV candle data for a symbol from cache."""
    conn = _get_conn()
    symbol = symbol.upper()

    rows = conn.execute(
        """SELECT ts, open_price, high, low, close_price, volume
           FROM market_candles
           WHERE symbol = ?
           ORDER BY ts DESC
           LIMIT ?""",
        [symbol, limit],
    ).fetchall()

    candles = []
    for r in reversed(rows):  # reverse to chronological order
        candles.append(
            {
                "time": r[0],
                "open": r[1],
                "high": r[2],
                "low": r[3],
                "close": r[4],
                "volume": r[5],
            }
        )

    return {
        "symbol": symbol,
        "candles": candles,
        "count": len(candles),
    }


@router.get("/check-updates")
async def check_updates(
    preset: str = Query("VN30"),
) -> dict[str, object]:
    """Check if data needs updating (>24h old or missing)."""
    conn = _get_conn()
    meta_rows = conn.execute(
        "SELECT last_updated, symbol_count, years FROM load_metadata WHERE preset = ?",
        [preset],
    ).fetchall()

    if not meta_rows:
        return {
            "needs_update": True,
            "reason": "no_data",
            "last_updated": None,
        }

    last_updated = meta_rows[0][0]
    now = datetime.now(tz=UTC)

    # If last_updated is naive, assume UTC
    if hasattr(last_updated, "tzinfo") and last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=UTC)

    age_hours = (now - last_updated).total_seconds() / 3600
    needs_update = age_hours > 24

    fmt = "%d/%m/%Y %H:%M"
    return {
        "needs_update": needs_update,
        "reason": "stale" if needs_update else "fresh",
        "last_updated": last_updated.strftime(fmt),
        "age_hours": round(age_hours, 1),
        "symbol_count": meta_rows[0][1],
        "years": meta_rows[0][2],
    }


@router.get("/run-screener")
async def run_screener(
    preset: str = Query("VN30", description="VN30 or TOP100"),
) -> StreamingResponse:
    """Run the multi-agent screener pipeline with streaming progress."""
    return StreamingResponse(
        _generate_screener_progress(preset),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
