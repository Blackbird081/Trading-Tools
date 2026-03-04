from __future__ import annotations

import asyncio
import json
import sys
import types

import duckdb
import pytest

import interface.rest.data_loader as data_loader


def test_score_and_risk_helpers() -> None:
    assert data_loader._normalize_score(-100) == 0.0  # noqa: SLF001
    assert data_loader._normalize_score(100) == 10.0  # noqa: SLF001
    assert data_loader._risk_label(False, 9.0) == "HIGH"  # noqa: SLF001
    assert data_loader._risk_label(True, 7.0) == "LOW"  # noqa: SLF001
    assert data_loader._risk_label(True, 5.5) == "MEDIUM"  # noqa: SLF001
    assert data_loader._risk_label(True, 1.0) == "HIGH"  # noqa: SLF001


def test_data_provider_mode_policy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("DATA_PROVIDER_MODE", raising=False)
    assert data_loader._resolve_data_provider_mode() == "mock"  # noqa: SLF001

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATA_PROVIDER_MODE", "live")
    assert data_loader._resolve_data_provider_mode() == "live"  # noqa: SLF001

    monkeypatch.setenv("DATA_PROVIDER_MODE", "mock")
    with pytest.raises(RuntimeError):
        data_loader._resolve_data_provider_mode()  # noqa: SLF001


def test_build_reasoning_and_sse_format() -> None:
    text = data_loader._build_reasoning(  # noqa: SLF001
        symbol="FPT",
        action="BUY",
        score=7.5,
        rsi=60.0,
        macd="bullish",
        risk_reason="ok",
        fundamental_note="co ban tich cuc",
        headline="FPT tang truong",
    )
    assert "Fundamental" in text
    assert "Tin nổi bật" in text

    payload = data_loader._sse("tick", {"symbol": "FPT"})  # noqa: SLF001
    assert payload.startswith("event: tick")
    assert json.loads(payload.split("data: ", 1)[1])["symbol"] == "FPT"

    sell_text = data_loader._build_reasoning(  # noqa: SLF001
        symbol="VCB",
        action="SELL",
        score=3.2,
        rsi=39.5,
        macd="bearish",
        risk_reason=None,
    )
    assert "nghiêng về bán" in sell_text


@pytest.mark.asyncio
async def test_safe_sse_stream_yields_error_event_on_exception() -> None:
    async def broken_stream():
        yield "event: ping\ndata: {}\n\n"
        raise RuntimeError("stream boom")

    chunks = []
    async for chunk in data_loader._safe_sse_stream("load", broken_stream()):  # noqa: SLF001
        chunks.append(chunk)
    joined = "".join(chunks)
    assert "event: ping" in joined
    assert "event: error" in joined
    assert "Load failed" in joined


@pytest.mark.asyncio
async def test_safe_sse_stream_propagates_cancelled_error() -> None:
    async def cancelled_stream():
        if False:
            yield "never"
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        async for _ in data_loader._safe_sse_stream("load", cancelled_stream()):  # noqa: SLF001
            pass


@pytest.mark.asyncio
async def test_deterministic_engine_and_local_news_port(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = data_loader._DeterministicInsightEngine()  # noqa: SLF001
    result = await engine.generate("Phan tich ma: FPT\n- headline")
    assert "FPT" in result
    assert "trung tính" in result

    early_warning_result = await engine.generate("Phan tich ma: FPT\nEarly Warning:\n- headline")
    assert "ưu tiên phòng thủ" in early_warning_result

    eps_result = await engine.generate("Phan tich ma: FPT\nEPS tang truong\n- headline")
    assert "nghiêng tích cực" in eps_result

    local_news = data_loader._LocalNewsPort(use_external=False)  # noqa: SLF001
    headlines = local_news.get_headlines("FPT", limit=2)
    assert len(headlines) == 2
    snap = local_news.snapshot("FPT")
    assert snap["source"] == "local-fallback"

    class Stock:
        def news(self):
            return [{"title": "Tin tu vnstock"}]

    class Vnstock:
        def stock(self, symbol: str, source: str):
            return Stock()

    monkeypatch.setitem(sys.modules, "vnstock", types.SimpleNamespace(Vnstock=lambda: Vnstock()))
    external_news = data_loader._LocalNewsPort(use_external=True)  # noqa: SLF001
    ext_headlines = external_news.get_headlines("VCB", limit=3)
    assert ext_headlines
    assert external_news.snapshot("VCB")["source"] in {"vnstock", "local-fallback"}

    class BrokenAdapter:
        def get_headlines(self, symbol: str, limit: int = 5) -> list[dict[str, str]]:
            raise RuntimeError("adapter error")

    external_news._adapter = BrokenAdapter()  # noqa: SLF001
    fallback_headlines = external_news.get_headlines("HPG", limit=2)
    assert len(fallback_headlines) == 2
    assert external_news.snapshot("HPG")["source"] == "local-fallback"


def test_local_financial_data_port(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = duckdb.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE market_cache (
            symbol VARCHAR, preset VARCHAR, price DOUBLE, change_val DOUBLE, change_pct DOUBLE, volume BIGINT,
            high DOUBLE, low DOUBLE, open_price DOUBLE, ceiling DOUBLE, floor DOUBLE, reference DOUBLE, updated_at TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        INSERT INTO market_cache(symbol,preset,price,change_val,change_pct,volume,high,low,open_price,ceiling,floor,reference,updated_at)
        VALUES ('FPT','VN30',100,1.2,1.2,2000000,101,99,99.5,107,93,100,now())
        """
    )

    port = data_loader._LocalFinancialDataPort(conn, preset="VN30", use_external=False)  # noqa: SLF001
    payload = port.get_financial_data("FPT")
    assert payload["source"] == "cache-derived"
    assert "financial_ratios" in payload
    assert port.snapshot("FPT")["source"] == "cache-derived"

    class Company:
        def overview(self):
            return [{"pe": 11.2, "roe": 18.0, "debt_to_equity": 0.4}]

    class Stock:
        company = Company()

    class Vnstock:
        def stock(self, symbol: str, source: str):
            return Stock()

    monkeypatch.setitem(sys.modules, "vnstock", types.SimpleNamespace(Vnstock=lambda: Vnstock()))
    external_port = data_loader._LocalFinancialDataPort(conn, preset="VN30", use_external=True)  # noqa: SLF001
    payload_ext = external_port.get_financial_data("FPT")
    assert payload_ext["source"] in {"vnstock+cache", "cache-derived"}

    class NoCompanyStock:
        company = None

    class NoOverviewStock:
        company = types.SimpleNamespace()

    class DictCompany:
        @staticmethod
        def overview() -> dict[str, float]:
            return {"pe": 12.5, "roe": 15.0, "debt_to_equity": 0.6}

    class DictStock:
        company = DictCompany()

    class VnstockFactory:
        def __init__(self, stock_obj: object) -> None:
            self._stock_obj = stock_obj

        def stock(self, symbol: str, source: str) -> object:
            return self._stock_obj

    monkeypatch.setitem(sys.modules, "vnstock", types.SimpleNamespace(Vnstock=lambda: VnstockFactory(NoCompanyStock())))
    assert external_port._try_external_ratios("FPT") == {}  # noqa: SLF001

    monkeypatch.setitem(sys.modules, "vnstock", types.SimpleNamespace(Vnstock=lambda: VnstockFactory(NoOverviewStock())))
    assert external_port._try_external_ratios("FPT") == {}  # noqa: SLF001

    monkeypatch.setitem(sys.modules, "vnstock", types.SimpleNamespace(Vnstock=lambda: VnstockFactory(DictStock())))
    mapped = external_port._try_external_ratios("FPT")  # noqa: SLF001
    assert mapped["pe_ratio"] == pytest.approx(12.5)
    assert mapped["debt_to_equity"] == pytest.approx(0.6)

    class ExplosiveVnstock:
        def __call__(self):
            raise RuntimeError("boom")

    monkeypatch.setitem(sys.modules, "vnstock", types.SimpleNamespace(Vnstock=ExplosiveVnstock()))
    assert external_port._try_external_ratios("FPT") == {}  # noqa: SLF001


@pytest.mark.asyncio
async def test_incremental_progress_requires_existing_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = duckdb.connect(":memory:")
    conn.execute(data_loader._CACHE_DDL)  # noqa: SLF001
    monkeypatch.setattr(data_loader, "_get_conn", lambda: conn)
    chunks: list[str] = []
    async for chunk in data_loader._generate_incremental_progress(["FPT"], "VN30"):  # noqa: SLF001
        chunks.append(chunk)
    joined = "".join(chunks)
    assert "event: error" in joined
    assert "No cache available" in joined


@pytest.mark.asyncio
async def test_cache_tick_repo_ohlcv_and_var_paths() -> None:
    conn = duckdb.connect(":memory:")
    conn.execute(data_loader._CACHE_DDL)  # noqa: SLF001
    conn.execute(
        """
        INSERT INTO market_cache(symbol,preset,price,change_val,change_pct,volume,high,low,open_price,ceiling,floor,reference,updated_at)
        VALUES ('FPT','VN30',120,2.0,1.7,2300000,121,118,119,128,112,118,now())
        """
    )

    base_ts = 1_700_000_000
    candle_rows = []
    closes = [0.0] + [100.0 + i for i in range(1, 35)]
    for idx, close in enumerate(closes):
        candle_rows.append(
            (
                "FPT",
                base_ts + idx,
                close - 1.0,
                close + 1.0,
                max(0.1, close - 2.0),
                close,
                500_000 + idx * 1000,
            )
        )
    conn.executemany(
        """
        INSERT INTO market_candles(symbol,ts,open_price,high,low,close_price,volume)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        candle_rows,
    )

    repo = data_loader._CacheTickRepo(conn, preset="VN30")  # noqa: SLF001
    fallback = await repo.get_ohlcv("VCB")
    assert len(fallback) == 2

    ohlcv = await repo.get_ohlcv("FPT")
    assert len(ohlcv) == len(closes)
    assert {"timestamp", "open", "high", "low", "close", "volume"} <= set(ohlcv[0].keys())

    var = repo.calculate_var_historical("FPT")
    assert var >= 0.0
