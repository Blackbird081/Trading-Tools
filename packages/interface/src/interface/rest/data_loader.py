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
import os
import random
import re
import tempfile
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import duckdb
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

logger = logging.getLogger("interface.data_loader")

router = APIRouter()

# ── DB connection (lazy singleton) ──────────────────────────────
_conn: duckdb.DuckDBPyConnection | None = None


def _db_path_candidates() -> list[Path]:
    """Resolve writable DuckDB path candidates in priority order."""
    env_raw = os.getenv("DUCKDB_PATH", "").strip()
    candidates: list[Path] = []
    if env_raw:
        candidates.append(Path(env_raw).expanduser())
    candidates.extend(
        [
            Path("/app/data/trading.duckdb"),
            Path(tempfile.gettempdir()) / "trading.duckdb",
        ]
    )

    # De-duplicate while preserving order.
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _get_conn() -> duckdb.DuckDBPyConnection:
    global _conn
    if _conn is None:
        last_error: Exception | None = None
        for db_path in _db_path_candidates():
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)
                _conn = duckdb.connect(str(db_path))
                _conn.execute(_CACHE_DDL)
                logger.info("Data loader cache DB initialized at %s", db_path)
                break
            except Exception as exc:  # pragma: no cover - environment-specific fallback
                last_error = exc
                logger.warning("Failed to initialize data loader DB at %s: %s", db_path, exc)
                _conn = None

        if _conn is None:
            raise RuntimeError(
                f"Unable to initialize data loader DB at candidates={_db_path_candidates()}: {last_error}"
            )
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
            "mode": "load",
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
            "mode": "load",
            "message": f"Loaded {total} symbols x {years} years",
            "last_updated": now_str,
        },
    )


async def _generate_incremental_progress(
    symbols: list[str],
    preset: str,
) -> AsyncGenerator[str, None]:
    """Stream SSE progress for incremental update using existing cached universe."""
    conn = _get_conn()
    meta_rows = conn.execute(
        "SELECT years FROM load_metadata WHERE preset = ?",
        [preset],
    ).fetchall()

    if not meta_rows:
        yield _sse(
            "error",
            {
                "mode": "update",
                "message": "No cache available. Run full Load first.",
            },
        )
        return

    years = int(meta_rows[0][0])
    total = len(symbols)
    yield _sse(
        "start",
        {
            "total": total,
            "years": years,
            "mode": "update",
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
                "status": f"Updating {symbol}...",
                "mode": "update",
            },
        )

        # Incremental update: refresh latest tick snapshot only (no full candle regeneration).
        await asyncio.sleep(random.uniform(0.01, 0.03))
        row = conn.execute(
            """SELECT price, reference
               FROM market_cache
               WHERE symbol = ? AND preset = ?""",
            [symbol, preset],
        ).fetchone()

        rng = random.Random(f"{symbol}-{int(datetime.now(tz=UTC).timestamp())}")
        prev_price = float(row[0]) if row else rng.uniform(10, 150)
        reference = float(row[1]) if row else prev_price
        change = rng.uniform(-2, 2)
        price = round(max(1.0, prev_price + change), 2)
        high = round(max(price, prev_price) + rng.uniform(0, 1.5), 2)
        low = round(max(0.5, min(price, prev_price) - rng.uniform(0, 1.5)), 2)
        volume = rng.randint(100_000, 5_000_000)

        tick = {
            "symbol": symbol,
            "price": price,
            "change": round(price - reference, 2),
            "changePct": round(((price - reference) / reference * 100) if reference else 0, 2),
            "volume": volume,
            "high": high,
            "low": low,
            "open": round(prev_price, 2),
            "ceiling": round(reference * 1.07, 2),
            "floor": round(reference * 0.93, 2),
            "reference": round(reference, 2),
            "timestamp": int(datetime.now(tz=UTC).timestamp() * 1000),
        }
        _save_tick_to_db(tick, preset)
        yield _sse("tick", {**tick, "mode": "update"})

    _save_metadata(preset, total, years)
    now_str = datetime.now(tz=UTC).strftime("%d/%m/%Y %H:%M")
    yield _sse(
        "complete",
        {
            "loaded": total,
            "total": total,
            "percent": 100,
            "mode": "update",
            "message": f"Updated {total} symbols from cache",
            "last_updated": now_str,
        },
    )


# ── Screener pipeline SSE (real-agent wiring) ──────────────────
_AGENT_STEPS_BASE: list[dict[str, str]] = [
    {"node": "screener", "agent": "Screener Agent", "icon": "search", "detail": "Lọc cơ hội theo data cache + thanh khoản"},
    {"node": "technical", "agent": "Technical Agent", "icon": "chart", "detail": "Tính RSI/MACD/BB/MA trên dữ liệu giá thực tế"},
    {"node": "risk", "agent": "Risk Agent", "icon": "shield", "detail": "Kiểm tra hạn mức rủi ro và điều kiện an toàn"},
    {"node": "executor", "agent": "Executor Agent", "icon": "zap", "detail": "Sinh execution plan dry-run/live theo guardrails"},
]
_AGENT_STEPS_WITH_FUNDAMENTAL: list[dict[str, str]] = [
    {"node": "screener", "agent": "Screener Agent", "icon": "search", "detail": "Lọc cơ hội theo data cache + thanh khoản"},
    {"node": "technical", "agent": "Technical Agent", "icon": "chart", "detail": "Tính RSI/MACD/BB/MA trên dữ liệu giá thực tế"},
    {"node": "fundamental", "agent": "Fundamental Agent", "icon": "brain", "detail": "Bổ sung fundamentals + news để tăng chất lượng rationale"},
    {"node": "risk", "agent": "Risk Agent", "icon": "shield", "detail": "Kiểm tra hạn mức rủi ro và điều kiện an toàn"},
    {"node": "executor", "agent": "Executor Agent", "icon": "zap", "detail": "Sinh execution plan dry-run/live theo guardrails"},
]


class _DeterministicInsightEngine:
    """Lightweight local engine for FundamentalAgent prompt execution."""

    async def generate(self, prompt: str) -> str:
        symbol_match = re.search(r"Phan tich ma:\s*([A-Z0-9]+)", prompt)
        symbol = symbol_match.group(1) if symbol_match else "N/A"
        news_count = prompt.count("- ")
        if "Early Warning:" in prompt:
            risk_bias = "ưu tiên phòng thủ"
        elif "EPS tang truong" in prompt:
            risk_bias = "nghiêng tích cực"
        else:
            risk_bias = "trung tính"
        return (
            f"{symbol}: tổng hợp fundamentals/news cho thấy trạng thái {risk_bias}; "
            f"ưu tiên kiểm soát rủi ro trước khi nâng tỷ trọng. "
            f"Số tín hiệu tin tức tham chiếu: {max(0, news_count - 1)}."
        )


class _LocalNewsPort:
    def __init__(self, use_external: bool) -> None:
        self._use_external = use_external
        self._adapter: Any | None = None
        self._cache: dict[str, dict[str, object]] = {}
        if use_external:
            try:
                from adapters.vnstock.news import VnstockNewsAdapter

                self._adapter = VnstockNewsAdapter()
            except Exception:
                self._adapter = None

    def _fallback_headlines(self, symbol: str, limit: int) -> list[dict[str, object]]:
        rng = random.Random(hash(symbol + "news-fallback"))
        now = datetime.now(UTC).date().isoformat()
        templates = [
            f"{symbol}: thanh khoản cải thiện so với trung bình 20 phiên",
            f"{symbol}: dòng tiền ngành duy trì ổn định",
            f"{symbol}: biến động giá phiên gần nhất cần theo dõi",
            f"{symbol}: triển vọng kết quả kinh doanh quý tới ở mức trung tính",
        ]
        rng.shuffle(templates)
        return [{"title": t, "source": "local-fallback", "date": now} for t in templates[: max(1, limit)]]

    def get_headlines(self, symbol: str, limit: int = 5) -> list[dict[str, object]]:
        headlines: list[dict[str, object]] = []
        source = "local-fallback"
        if self._use_external and self._adapter is not None:
            try:
                headlines = self._adapter.get_headlines(symbol=symbol, limit=limit)
                if headlines:
                    source = "vnstock"
            except Exception:
                headlines = []
        if not headlines:
            headlines = self._fallback_headlines(symbol, limit)

        self._cache[symbol] = {
            "source": source,
            "headlines": [str(item.get("title", "")).strip() for item in headlines if str(item.get("title", "")).strip()],
        }
        return headlines

    def snapshot(self, symbol: str) -> dict[str, object]:
        return self._cache.get(symbol, {"source": "unavailable", "headlines": []})


class _LocalFinancialDataPort:
    def __init__(self, conn: duckdb.DuckDBPyConnection, preset: str, use_external: bool) -> None:
        self._conn = conn
        self._preset = preset
        self._use_external = use_external
        self._cache: dict[str, dict[str, object]] = {}

    def _build_local_payload(self, symbol: str) -> dict[str, Any]:
        row = self._conn.execute(
            """
            SELECT price, change_pct, volume, reference
            FROM market_cache
            WHERE symbol = ? AND preset = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            [symbol, self._preset],
        ).fetchone()
        price = float(row[0]) if row else 10.0
        change_pct = float(row[1]) if row else 0.0
        volume = float(row[2]) if row else 0.0
        eps_growth = max(-0.25, min(0.55, (change_pct / 100.0) + min(0.25, volume / 30_000_000.0)))
        pe_ratio = max(4.0, min(35.0, 18.0 - (eps_growth * 16.0)))
        roe = max(0.03, min(0.35, 0.10 + eps_growth * 0.8))
        debt_equity = max(0.1, min(3.0, 1.8 - eps_growth * 2.5))
        operating_margin = max(0.02, min(0.4, 0.12 + eps_growth * 0.5))
        revenue_growth = max(-0.2, min(0.45, eps_growth * 0.9))
        net_margin = max(0.01, min(0.28, 0.08 + eps_growth * 0.4))

        return {
            "source": "cache-derived",
            "financial_ratios": {
                "eps_growth": round(eps_growth, 4),
                "pe_ratio": round(pe_ratio, 2),
                "roe": round(roe, 4),
                "debt_to_equity": round(debt_equity, 4),
                "operating_margin": round(operating_margin, 4),
                "revenue_growth": round(revenue_growth, 4),
                "net_margin": round(net_margin, 4),
            },
            "balance_sheet": {
                "total_assets": round(price * max(1.0, volume / 15.0), 2),
                "total_liabilities": round(price * max(1.0, volume / 32.0), 2),
                "total_equity": round(price * max(1.0, volume / 28.0), 2),
            },
            "income_statement": {
                "revenue": round(price * max(1.0, volume / 20.0), 2),
                "operating_income": round(price * max(1.0, volume / 42.0), 2),
                "net_income": round(price * max(1.0, volume / 50.0), 2),
            },
            "cash_flow": {
                "operating_cash_flow": round(price * max(1.0, volume / 40.0), 2),
            },
            "previous_financial_ratios": {
                "revenue_growth": round(revenue_growth * 0.85, 4),
                "roe": round(roe * 0.92, 4),
            },
            "icb_name": "General",
            "icb_code": "0000",
        }

    def _try_external_ratios(self, symbol: str) -> dict[str, float]:
        if not self._use_external:
            return {}
        try:
            import vnstock  # type: ignore[import-untyped]

            stock = vnstock.Vnstock().stock(symbol=symbol, source="VCI")
            company = getattr(stock, "company", None)
            if company is None:
                return {}
            if not hasattr(company, "overview"):
                return {}

            raw = company.overview()
            records: list[dict[str, Any]] = []
            if isinstance(raw, list):
                records = [item for item in raw if isinstance(item, dict)]
            elif isinstance(raw, dict):
                records = [raw]
            elif hasattr(raw, "to_dict"):
                try:
                    as_records = raw.to_dict("records")
                except Exception:  # pragma: no cover - library dependent
                    as_records = []
                if isinstance(as_records, list):
                    records = [item for item in as_records if isinstance(item, dict)]
            if not records:
                return {}

            first = records[0]
            mapped: dict[str, float] = {}
            pe = first.get("pe") or first.get("pe_ratio")
            roe = first.get("roe")
            debt = first.get("debt_to_equity") or first.get("de")
            if pe is not None:
                mapped["pe_ratio"] = float(pe)
            if roe is not None:
                mapped["roe"] = float(roe) / (100.0 if float(roe) > 1.0 else 1.0)
            if debt is not None:
                mapped["debt_to_equity"] = float(debt)
            return mapped
        except Exception:
            return {}

    def get_financial_data(self, symbol: str) -> dict[str, Any]:
        payload = self._build_local_payload(symbol)
        external = self._try_external_ratios(symbol)
        if external:
            payload["financial_ratios"].update(external)
            payload["source"] = "vnstock+cache"
        self._cache[symbol] = payload
        return payload

    def snapshot(self, symbol: str) -> dict[str, object]:
        payload = self._cache.get(symbol)
        if payload is None:
            return {"source": "unavailable"}
        return {"source": str(payload.get("source", "cache-derived"))}


class _CacheScreenerPort:
    def __init__(self, conn: duckdb.DuckDBPyConnection, preset: str, symbols: list[str]) -> None:
        self._conn = conn
        self._preset = preset
        self._symbols = symbols

    async def screen(self, min_eps_growth: float = 0.10, max_pe_ratio: float = 15.0) -> list[dict[str, object]]:
        rows = self._conn.execute(
            """
            SELECT symbol, price, change_pct, volume, reference
            FROM market_cache
            WHERE preset = ?
            ORDER BY volume DESC, symbol ASC
            """,
            [self._preset],
        ).fetchall()

        if not rows:
            rows = [(s, 0.0, 0.0, 0, 0.0) for s in self._symbols]

        candidates: list[dict[str, object]] = []
        for row in rows:
            symbol = str(row[0])
            change_pct = float(row[2] or 0.0)
            volume = float(row[3] or 0.0)
            liquidity_bonus = min(0.20, volume / 20_000_000)
            eps_growth = max(-0.25, min(0.50, (change_pct / 100) + liquidity_bonus))
            pe_ratio = max(4.0, min(35.0, 18.0 - (eps_growth * 18)))
            if eps_growth >= min_eps_growth and pe_ratio <= max_pe_ratio:
                candidates.append(
                    {
                        "symbol": symbol,
                        "eps_growth": round(eps_growth, 4),
                        "pe_ratio": round(pe_ratio, 2),
                    }
                )

        if not candidates:
            for row in rows[: min(15, len(rows))]:
                candidates.append(
                    {
                        "symbol": str(row[0]),
                        "eps_growth": 0.11,
                        "pe_ratio": 14.0,
                    }
                )
        return candidates


class _CacheTickRepo:
    def __init__(self, conn: duckdb.DuckDBPyConnection, preset: str) -> None:
        self._conn = conn
        self._preset = preset

    async def query_volume_spikes(self, threshold_multiplier: float = 2.0) -> list[dict[str, object]]:
        rows = self._conn.execute(
            """
            WITH latest AS (
                SELECT
                    symbol,
                    volume,
                    ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY ts DESC) AS rn
                FROM market_candles
            ),
            avg20 AS (
                SELECT symbol, AVG(volume) AS avg_vol
                FROM (
                    SELECT
                        symbol,
                        volume,
                        ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY ts DESC) AS rn
                    FROM market_candles
                ) q
                WHERE rn <= 20
                GROUP BY symbol
            )
            SELECT l.symbol, l.volume, a.avg_vol
            FROM latest l
            JOIN avg20 a ON a.symbol = l.symbol
            JOIN market_cache m ON m.symbol = l.symbol AND m.preset = ?
            WHERE l.rn = 1 AND l.volume >= a.avg_vol * ?
            ORDER BY l.volume DESC
            """,
            [self._preset, threshold_multiplier],
        ).fetchall()
        return [{"symbol": str(r[0]), "volume": int(r[1]), "avg_volume": float(r[2])} for r in rows]

    async def get_ohlcv(self, symbol: str) -> list[dict[str, object]]:
        rows = self._conn.execute(
            """
            SELECT ts, open_price, high, low, close_price, volume
            FROM market_candles
            WHERE symbol = ?
            ORDER BY ts DESC
            LIMIT 260
            """,
            [symbol],
        ).fetchall()
        if not rows:
            fallback = self.get_latest_price(symbol)
            base = fallback if fallback > 0 else 10000.0
            return [{"close": base * 0.98}, {"close": base}]
        out: list[dict[str, object]] = []
        for row in reversed(rows):
            out.append(
                {
                    "timestamp": int(row[0]),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": int(row[5]),
                }
            )
        return out

    def get_latest_price(self, symbol: str) -> float:
        row = self._conn.execute(
            """
            SELECT price
            FROM market_cache
            WHERE symbol = ? AND preset = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            [symbol, self._preset],
        ).fetchone()
        return float(row[0]) if row else 0.0

    def calculate_var_historical(self, symbol: str, confidence: float = 0.95, window_days: int = 252) -> float:
        rows = self._conn.execute(
            """
            SELECT close_price
            FROM market_candles
            WHERE symbol = ?
            ORDER BY ts DESC
            LIMIT ?
            """,
            [symbol, max(window_days, 30)],
        ).fetchall()
        closes = [float(r[0]) for r in reversed(rows)]
        if len(closes) < 20:
            return 0.0
        returns: list[float] = []
        for i in range(1, len(closes)):
            prev = closes[i - 1]
            cur = closes[i]
            if prev <= 0:
                continue
            returns.append((cur - prev) / prev)
        if not returns:
            return 0.0
        returns.sort()
        index = max(0, min(len(returns) - 1, int((1 - confidence) * len(returns))))
        var_fraction = abs(returns[index])
        latest = closes[-1]
        return latest * var_fraction


def _normalize_score(raw: float) -> float:
    clipped = max(-10.0, min(10.0, raw))
    return round((clipped + 10.0) / 2.0, 1)


def _risk_label(approved: bool, score: float) -> str:
    if not approved:
        return "HIGH"
    if score >= 7.0:
        return "LOW"
    if score >= 5.0:
        return "MEDIUM"
    return "HIGH"


def _build_reasoning(
    symbol: str,
    action: str,
    score: float,
    rsi: float,
    macd: str,
    risk_reason: str | None,
    fundamental_note: str | None = None,
    headline: str | None = None,
) -> str:
    if action == "BUY":
        reason = f"{symbol}: tín hiệu kỹ thuật ủng hộ mua (score {score}/10, RSI {rsi:.1f}, MACD {macd})."
    elif action == "SELL":
        reason = f"{symbol}: tín hiệu kỹ thuật nghiêng về bán (score {score}/10, RSI {rsi:.1f}, MACD {macd})."
    else:
        reason = f"{symbol}: tín hiệu chưa đủ mạnh để vào lệnh (score {score}/10, RSI {rsi:.1f}, MACD {macd})."
    if risk_reason:
        reason = f"{reason} RiskAgent: {risk_reason}."
    if fundamental_note:
        reason = f"{reason} Fundamental: {fundamental_note}"
    if headline:
        reason = f"{reason} Tin nổi bật: {headline}."
    return reason


async def _generate_screener_progress(
    preset: str = "VN30",
    mode: str = "dry-run",
) -> AsyncGenerator[str, None]:
    """Stream SSE progress for real agent pipeline execution."""
    from agents.fundamental_agent import FundamentalAgent
    from agents.executor_agent import ExecutorAgent
    from agents.prompt_builder import FinancialPromptBuilder, PromptRegistry
    from agents.risk_agent import RiskAgent
    from agents.screener_agent import ScreenerAgent
    from agents.supervisor import build_trading_graph
    from agents.technical_agent import TechnicalAgent
    from interface.trading_store import (
        compute_portfolio,
        get_safety_state,
        save_screener_run,
    )

    symbols = VN30_SYMBOLS if preset == "VN30" else TOP100_SYMBOLS[:100]
    conn = _get_conn()
    tick_repo = _CacheTickRepo(conn, preset)
    screener_port = _CacheScreenerPort(conn, preset, symbols)
    use_external_sources = mode == "live" or os.getenv("SCREENER_USE_EXTERNAL", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    news_port = _LocalNewsPort(use_external=use_external_sources)
    financial_data_port = _LocalFinancialDataPort(conn, preset, use_external=use_external_sources)
    risk_limits = SimpleNamespace(
        kill_switch_active=bool(get_safety_state("kill_switch", {"active": False}).get("active")),
        max_position_pct=Decimal("0.20"),
        stop_loss_pct=Decimal("0.05"),
        take_profit_pct=Decimal("0.15"),
    )

    screener = ScreenerAgent(screener_port=screener_port, tick_repo=tick_repo)
    technical = TechnicalAgent(tick_repo=tick_repo)
    risk = RiskAgent(tick_repo=tick_repo, risk_limits=risk_limits)
    executor = ExecutorAgent(broker_port=None)
    fundamental: FundamentalAgent | None = None
    steps = _AGENT_STEPS_BASE
    try:
        prompts_dir = Path(os.getenv("PROMPTS_DIR", "data/prompts"))
        registry = PromptRegistry(prompts_dir)
        prompt_builder = FinancialPromptBuilder(registry)
        fundamental = FundamentalAgent(
            engine=_DeterministicInsightEngine(),
            prompt_builder=prompt_builder,
            news_port=news_port,
            financial_data_port=financial_data_port,
        )
        steps = _AGENT_STEPS_WITH_FUNDAMENTAL
    except Exception as exc:
        logger.warning("Fundamental agent disabled for screener run: %s", exc)

    graph = build_trading_graph(
        screener=screener,
        technical=technical,
        risk=risk,
        executor=executor,
        fundamental=fundamental,
    )
    app = graph.compile()

    total_steps = len(steps)
    run_id = str(uuid.uuid4())
    yield _sse(
        "pipeline_start",
        {
            "run_id": run_id,
            "preset": preset,
            "mode": mode,
            "total_steps": total_steps,
            "device": "CPU",
            "fundamental_enabled": fundamental is not None,
            "external_sources": use_external_sources,
        },
    )

    portfolio = compute_portfolio(mode=mode)
    initial_state: dict[str, object] = {
        "run_id": run_id,
        "dry_run": mode != "live",
        "current_nav": Decimal(str(portfolio["nav"])),
        "current_positions": {p["symbol"]: int(p["quantity"]) for p in portfolio["positions"]},
        "purchasing_power": Decimal(str(portfolio["purchasing_power"])),
        "max_candidates": 30 if preset == "VN30" else 80,
        "score_threshold": 2.5,
    }

    aggregated_state: dict[str, object] = dict(initial_state)
    node_to_step = {item["node"]: idx + 1 for idx, item in enumerate(steps)}
    started: set[str] = set()
    started_at: dict[str, datetime] = {}

    async for event in app.astream(initial_state, stream_mode="updates"):
        node = next(iter(event.keys()), "")
        partial = event.get(node, {})
        if isinstance(partial, dict):
            aggregated_state.update(partial)

        if node not in node_to_step:
            continue

        step_idx = node_to_step[node]
        step_cfg = steps[step_idx - 1]
        if node not in started:
            started.add(node)
            started_at[node] = datetime.now(UTC)
            yield _sse(
                "agent_start",
                {
                    "step": step_idx,
                    "total_steps": total_steps,
                    "agent": step_cfg["agent"],
                    "icon": step_cfg["icon"],
                    "detail": step_cfg["detail"],
                    "device": "CPU",
                    "percent": round((step_idx - 1) / total_steps * 100, 1),
                },
            )

        result_count = 0
        if node == "screener":
            result_count = len(aggregated_state.get("watchlist", []))
        elif node == "technical":
            result_count = len(aggregated_state.get("technical_scores", []))
        elif node == "fundamental":
            result_count = len(aggregated_state.get("ai_insights", {}))
        elif node == "risk":
            result_count = len(aggregated_state.get("approved_trades", []))
        elif node == "executor":
            result_count = len(aggregated_state.get("execution_plans", []))

        yield _sse(
            "agent_progress",
            {
                "step": step_idx,
                "agent": step_cfg["agent"],
                "sub_percent": 100.0,
                "percent": round(step_idx / total_steps * 100, 1),
            },
        )
        duration_ms = max(1, int((datetime.now(UTC) - started_at[node]).total_seconds() * 1000))
        yield _sse(
            "agent_done",
            {
                "step": step_idx,
                "agent": step_cfg["agent"],
                "device": "CPU",
                "duration_ms": duration_ms,
                "result_count": result_count,
                "percent": round(step_idx / total_steps * 100, 1),
            },
        )

    watchlist = {str(item.symbol): item for item in aggregated_state.get("watchlist", [])}
    technical_scores = {str(item.symbol): item for item in aggregated_state.get("technical_scores", [])}
    risk_scores = {str(item.symbol): item for item in aggregated_state.get("risk_assessments", [])}
    execution = {str(item.symbol): item for item in aggregated_state.get("execution_plans", [])}
    ai_insights = {str(k): str(v) for k, v in dict(aggregated_state.get("ai_insights", {})).items()}
    early_warning = {str(k): v for k, v in dict(aggregated_state.get("early_warning_results", {})).items()}
    dupont = {str(k): v for k, v in dict(aggregated_state.get("dupont_results", {})).items()}
    universe = list(watchlist.keys()) if watchlist else symbols

    results: list[dict[str, object]] = []
    for symbol in universe:
        tech = technical_scores.get(symbol)
        risk_assess = risk_scores.get(symbol)
        plan = execution.get(symbol)
        raw_score = float(tech.composite_score) if tech else 0.0
        score = _normalize_score(raw_score)
        action = str(tech.recommended_action) if tech else "HOLD"
        if action not in {"BUY", "SELL", "HOLD"}:
            action = "HOLD"
        confidence = round(min(1.0, 0.45 + abs(raw_score) / 15), 2)
        entry_price = float(risk_assess.latest_price) if risk_assess else float(tick_repo.get_latest_price(symbol))
        stop_loss = float(risk_assess.stop_loss_price) if risk_assess else round(entry_price * 0.95, 2)
        take_profit = float(risk_assess.take_profit_price) if risk_assess else round(entry_price * 1.1, 2)
        qty = int(plan.quantity) if plan else 0
        risk_text = _risk_label(bool(risk_assess.approved) if risk_assess else False, score)
        insight = ai_insights.get(symbol, "")
        ew_summary = (
            str(early_warning.get(symbol, {}).get("summary", ""))
            if isinstance(early_warning.get(symbol), dict)
            else ""
        )
        dupont_driver = (
            str(dupont.get(symbol, {}).get("dominant_driver", ""))
            if isinstance(dupont.get(symbol), dict)
            else ""
        )
        fundamental_note = insight or ew_summary or "Chưa có insight fundamental chi tiết."
        news_snapshot = news_port.snapshot(symbol)
        financial_snapshot = financial_data_port.snapshot(symbol)
        headlines = [str(h) for h in news_snapshot.get("headlines", []) if str(h).strip()]
        top_headline = headlines[0] if headlines else None
        results.append(
            {
                "symbol": symbol,
                "score": score,
                "confidence": confidence,
                "action": action,
                "rsi": round(float(tech.rsi_14), 2) if tech else 50.0,
                "macd": str(tech.macd_signal) if tech else "neutral",
                "risk": risk_text,
                "entry_price": round(entry_price, 2),
                "stop_loss": round(stop_loss, 2),
                "take_profit": round(take_profit, 2),
                "sl_pct": 5.0,
                "tp_pct": 10.0,
                "quantity": qty,
                "position_pct": round(float(risk_assess.position_size_pct) * 100, 2) if risk_assess else 0.0,
                "order_type": str(plan.order_type) if plan else "LO",
                "vol_change_pct": 0.0,
                "ma_trend": str(tech.trend_ma) if tech else "neutral",
                "fundamental_summary": fundamental_note,
                "news_headlines": headlines[:3],
                "dupont_driver": dupont_driver,
                "data_sources": {
                    "news": str(news_snapshot.get("source", "unknown")),
                    "fundamentals": str(financial_snapshot.get("source", "unknown")),
                    "insight": "fundamental-agent" if insight else "fallback",
                },
                "reasoning": _build_reasoning(
                    symbol,
                    action,
                    score,
                    round(float(tech.rsi_14), 2) if tech else 50.0,
                    str(tech.macd_signal) if tech else "neutral",
                    str(risk_assess.rejection_reason) if (risk_assess and risk_assess.rejection_reason) else None,
                    fundamental_note,
                    top_headline,
                ),
                "reproducibility": {
                    "model": "technical-fundamental-risk-executor",
                    "model_version": "local-r1",
                    "prompt_version": "financial_analysis@active",
                },
            }
        )

    results.sort(key=lambda x: (str(x["action"]) != "BUY", -float(x["score"])))
    buy_count = sum(1 for r in results if r["action"] == "BUY")
    sell_count = sum(1 for r in results if r["action"] == "SELL")
    hold_count = sum(1 for r in results if r["action"] == "HOLD")
    avg_score = round(sum(float(r["score"]) for r in results) / len(results), 2) if results else 0.0
    news_coverage = sum(1 for r in results if isinstance(r.get("news_headlines"), list) and len(r["news_headlines"]) > 0)
    fundamental_coverage = sum(1 for r in results if str(r.get("fundamental_summary", "")).strip())
    insight_coverage = len([v for v in ai_insights.values() if v.strip()])

    save_screener_run(
        run_id=run_id,
        preset=preset,
        mode=mode,
        results=results,
        metadata={
            "pipeline": "real-agent",
            "symbols_requested": len(symbols),
            "symbols_evaluated": len(results),
            "fundamental_enabled": fundamental is not None,
            "insight_coverage": insight_coverage,
            "fundamental_coverage": fundamental_coverage,
            "news_coverage": news_coverage,
            "external_sources": use_external_sources,
            "executed_at": datetime.now(UTC).isoformat(),
        },
    )

    yield _sse(
        "pipeline_complete",
        {
            "run_id": run_id,
            "preset": preset,
            "mode": mode,
            "total_steps": total_steps,
            "percent": 100,
            "total_symbols": len(results),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
            "avg_score": avg_score,
            "insight_coverage": insight_coverage,
            "fundamental_coverage": fundamental_coverage,
            "news_coverage": news_coverage,
            "results": results,
        },
    )


def _sse(event: str, data: dict[str, object]) -> str:
    """Format as Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _safe_sse_stream(
    mode: str,
    stream: AsyncGenerator[str, None],
) -> AsyncGenerator[str, None]:
    """Ensure stream always terminates with an explicit error event on failure."""
    try:
        async for chunk in stream:
            yield chunk
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("%s stream failed: %s", mode, exc)
        yield _sse(
            "error",
            {
                "mode": mode,
                "message": f"{mode.title()} failed: {exc}",
            },
        )


# ── REST endpoints ──────────────────────────────────────────────
@router.get("/load-data")
async def load_data(
    preset: str = Query("VN30", description="VN30 or TOP100"),
    years: int = Query(3, ge=1, le=10, description="Years of history"),
) -> StreamingResponse:
    """Load historical data for symbols with streaming progress."""
    symbols = VN30_SYMBOLS if preset == "VN30" else TOP100_SYMBOLS[:100]
    return StreamingResponse(
        _safe_sse_stream("load", _generate_progress(symbols, years, preset)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/update-data")
async def update_data(
    preset: str = Query("VN30", description="VN30 or TOP100"),
) -> StreamingResponse:
    """Incremental update for existing cached symbol universe."""
    symbols = VN30_SYMBOLS if preset == "VN30" else TOP100_SYMBOLS[:100]
    return StreamingResponse(
        _safe_sse_stream("update", _generate_incremental_progress(symbols, preset)),
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
    try:
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
    except Exception as exc:
        logger.exception("Failed to read cached data for preset=%s: %s", preset, exc)
        return {
            "ticks": [],
            "last_updated": None,
            "symbol_count": 0,
            "years": 0,
            "error": str(exc),
        }


@router.get("/candles/{symbol}")
async def get_candles(
    symbol: str,
    limit: int = Query(500, ge=50, le=2000),
) -> dict[str, object]:
    """Get OHLCV candle data for a symbol from cache."""
    symbol = symbol.upper()
    try:
        conn = _get_conn()
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
    except Exception as exc:
        logger.exception("Failed to read candles for %s: %s", symbol, exc)
        return {
            "symbol": symbol,
            "candles": [],
            "count": 0,
            "error": str(exc),
        }


@router.get("/check-updates")
async def check_updates(
    preset: str = Query("VN30"),
) -> dict[str, object]:
    """Check if data needs updating (>24h old or missing)."""
    try:
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
    except Exception as exc:
        logger.exception("Failed to check updates for preset=%s: %s", preset, exc)
        return {
            "needs_update": True,
            "reason": "db_error",
            "last_updated": None,
            "error": str(exc),
        }


@router.get("/run-screener")
async def run_screener(
    preset: str = Query("VN30", description="VN30 or TOP100"),
    mode: str = Query("dry-run", description="dry-run or live"),
) -> StreamingResponse:
    """Run the multi-agent screener pipeline with streaming progress."""
    normalized_mode = mode.strip().lower()
    if normalized_mode not in {"dry-run", "live"}:
        normalized_mode = "dry-run"
    return StreamingResponse(
        _safe_sse_stream("screener", _generate_screener_progress(preset, normalized_mode)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/screener/history")
async def get_screener_history(limit: int = Query(default=20, ge=1, le=200)) -> dict[str, object]:
    from interface.trading_store import screener_history

    rows = screener_history(limit=limit)
    return {"runs": rows, "count": len(rows)}
