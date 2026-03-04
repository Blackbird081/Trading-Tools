from __future__ import annotations

import asyncio
import json
import sys
import types
from datetime import UTC, date, datetime
from pathlib import Path

import duckdb
import pytest

import interface.rest.data_loader as data_loader
from interface.redaction import REDACTED


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


def test_build_insight_engine_from_env_provider_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_AI_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-12345678901234567890")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")
    engine, provider, remote_enabled, model_name = data_loader._build_insight_engine_from_env()  # noqa: SLF001
    assert provider == "openai"
    assert remote_enabled is True
    assert "router(" in model_name
    assert isinstance(engine, data_loader._OpenAIInsightEngine)  # noqa: SLF001
    assert engine._model_reasoning == "gpt-4o-mini"  # noqa: SLF001
    assert "gpt-4o-mini" in {  # noqa: SLF001
        engine._select_model("Need deep plan and risk reasoning"),  # noqa: SLF001
        engine._select_model("Write docs and UI style notes"),  # noqa: SLF001
        engine._select_model("Refactor API function with unit tests"),  # noqa: SLF001
    }

    monkeypatch.setenv("AGENT_AI_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-12345678901234567890")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
    engine, provider, remote_enabled, model_name = data_loader._build_insight_engine_from_env()  # noqa: SLF001
    assert provider == "anthropic"
    assert remote_enabled is True
    assert "router(" in model_name
    assert isinstance(engine, data_loader._AnthropicInsightEngine)  # noqa: SLF001

    monkeypatch.setenv("AGENT_AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "AIza12345678901234567890")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-1.5-flash")
    engine, provider, remote_enabled, model_name = data_loader._build_insight_engine_from_env()  # noqa: SLF001
    assert provider == "gemini"
    assert remote_enabled is True
    assert "router(" in model_name
    assert isinstance(engine, data_loader._GeminiInsightEngine)  # noqa: SLF001

    monkeypatch.setenv("AGENT_AI_PROVIDER", "alibaba")
    monkeypatch.setenv("ALIBABA_API_KEY", "sk-alibaba-12345678901234567890")
    monkeypatch.setenv("ALIBABA_MODEL_CODER", "qwen2.5-coder-32b-instruct")
    monkeypatch.setenv("ALIBABA_MODEL_REASONING", "kimi-k2.5")
    monkeypatch.setenv("ALIBABA_MODEL_WRITING", "minimax-m2.5")
    engine, provider, remote_enabled, model_name = data_loader._build_insight_engine_from_env()  # noqa: SLF001
    assert provider == "alibaba"
    assert remote_enabled is True
    assert "router(" in model_name
    assert isinstance(engine, data_loader._AlibabaTaskRouterInsightEngine)  # noqa: SLF001
    assert engine._select_model("Please refactor this function to improve performance") == "qwen2.5-coder-32b-instruct"  # noqa: SLF001
    assert engine._select_model("Need deep logic plan with clear workflow and trade-off") == "kimi-k2.5"  # noqa: SLF001
    assert engine._select_model("Write CSS layout and docs with better UI text") == "minimax-m2.5"  # noqa: SLF001

    monkeypatch.setenv("AGENT_AI_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    engine, provider, remote_enabled, model_name = data_loader._build_insight_engine_from_env()  # noqa: SLF001
    assert provider == "deterministic"
    assert remote_enabled is False
    assert model_name == "deterministic-v1"
    assert isinstance(engine, data_loader._DeterministicInsightEngine)  # noqa: SLF001


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


def test_db_candidates_dedup_and_get_conn_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUCKDB_PATH", "/app/data/trading.duckdb")
    candidates = data_loader._db_path_candidates()  # noqa: SLF001
    assert candidates[0].as_posix().endswith("/app/data/trading.duckdb")
    assert len({str(item) for item in candidates}) == len(candidates)

    if data_loader._conn is not None:  # noqa: SLF001
        data_loader._conn.close()  # noqa: SLF001
    data_loader._conn = None  # noqa: SLF001

    monkeypatch.setattr(data_loader, "_db_path_candidates", lambda: [Path("broken.duckdb")])

    def _raise_connect(_: str) -> duckdb.DuckDBPyConnection:
        raise RuntimeError("connect failed")

    monkeypatch.setattr(data_loader.duckdb, "connect", _raise_connect)
    with pytest.raises(RuntimeError, match="Unable to initialize data loader DB"):
        data_loader._get_conn()  # noqa: SLF001


def test_cast_helpers_datetime_and_save_candles_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    assert data_loader._as_float("bad", default=1.23) == pytest.approx(1.23)  # noqa: SLF001
    assert data_loader._as_int("bad", default=7) == 7  # noqa: SLF001
    assert data_loader._detect_task_type("plain text without keywords") == "reasoning"  # noqa: SLF001

    naive_dt = datetime(2026, 3, 4, 10, 30)
    out_dt = data_loader._as_datetime(naive_dt)  # noqa: SLF001
    assert out_dt is not None and out_dt.tzinfo is not None
    out_date = data_loader._as_datetime(date(2026, 3, 4))  # noqa: SLF001
    assert out_date is not None and out_date.tzinfo is not None
    assert data_loader._as_datetime("not-a-date") is None  # noqa: SLF001

    class _TsObj:
        @staticmethod
        def to_pydatetime() -> datetime:
            return datetime(2026, 3, 4, 9, 0)

    assert data_loader._as_datetime(_TsObj()) is not None  # noqa: SLF001

    conn = duckdb.connect(":memory:")
    monkeypatch.setattr(data_loader, "_get_conn", lambda: conn)
    data_loader._save_candles_to_db([])  # noqa: SLF001


def _install_vnstock_module(stock_obj: object, monkeypatch: pytest.MonkeyPatch) -> None:
    class _Vnstock:
        def stock(self, symbol: str, source: str) -> object:
            assert symbol
            assert source
            return stock_obj

    monkeypatch.setitem(sys.modules, "vnstock", types.SimpleNamespace(Vnstock=lambda: _Vnstock()))


def test_load_symbol_live_data_success_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class _HistoryQuote:
        def __init__(self, rows: list[dict[str, object]]) -> None:
            self._rows = rows

        def history(self, start: str, end: str) -> object:
            assert start
            assert end
            rows = self._rows

            class _Df:
                def __init__(self, items: list[dict[str, object]]) -> None:
                    self._items = items

                @property
                def empty(self) -> bool:
                    return len(self._items) == 0

                def iterrows(self):
                    for idx, item in enumerate(self._items):
                        yield idx, item

            return _Df(rows)

    class _Stock:
        def __init__(self, rows: list[dict[str, object]]) -> None:
            self.quote = _HistoryQuote(rows)

    rows = [
        {"time": "2026-03-01T00:00:00Z", "open": 100, "high": 102, "low": 98, "close": 101, "volume": 1_000_000},
        {"time": "invalid", "open": 101, "high": 103, "low": 99, "close": 102, "volume": 1_100_000},
        {"time": "2026-03-02T00:00:00Z", "open": 101, "high": 104, "low": 100, "close": 103, "volume": 1_200_000},
    ]
    _install_vnstock_module(_Stock(rows), monkeypatch)
    tick, candles = data_loader._load_symbol_live_data("FPT", date(2026, 1, 1), date(2026, 3, 4))  # noqa: SLF001
    assert tick["symbol"] == "FPT"
    assert len(candles) == 2

    class _BrokenQuote:
        @staticmethod
        def history(start: str, end: str) -> object:
            raise RuntimeError("history boom")

    class _BrokenStock:
        quote = _BrokenQuote()

    _install_vnstock_module(_BrokenStock(), monkeypatch)
    with pytest.raises(RuntimeError, match="failed to fetch history"):
        data_loader._load_symbol_live_data("FPT", date(2026, 1, 1), date(2026, 3, 4))  # noqa: SLF001

    _install_vnstock_module(_Stock([]), monkeypatch)
    with pytest.raises(RuntimeError, match="returned no history"):
        data_loader._load_symbol_live_data("FPT", date(2026, 1, 1), date(2026, 3, 4))  # noqa: SLF001

    bad_rows = [{"time": "invalid", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]
    _install_vnstock_module(_Stock(bad_rows), monkeypatch)
    with pytest.raises(RuntimeError, match="empty candle set"):
        data_loader._load_symbol_live_data("FPT", date(2026, 1, 1), date(2026, 3, 4))  # noqa: SLF001


def test_load_symbol_live_tick_persists_latest(monkeypatch: pytest.MonkeyPatch) -> None:
    saved: dict[str, object] = {}

    def _fake_load(symbol: str, start_date: date, end_date: date) -> tuple[dict[str, object], list[dict[str, object]]]:
        assert symbol == "FPT"
        assert start_date <= end_date
        tick = {"symbol": "FPT", "price": 100.0}
        candles = [{"symbol": "FPT", "ts": 1, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}] * 60
        return tick, candles

    monkeypatch.setattr(data_loader, "_load_symbol_live_data", _fake_load)
    monkeypatch.setattr(data_loader, "_save_candles_to_db", lambda candles: saved.setdefault("candles", len(candles)))
    monkeypatch.setattr(data_loader, "_save_tick_to_db", lambda tick, preset: saved.setdefault("tick", (tick, preset)))

    tick = data_loader._load_symbol_live_tick("FPT", "VN30")  # noqa: SLF001
    assert tick["symbol"] == "FPT"
    assert saved["candles"] == 45
    assert saved["tick"] == ({"symbol": "FPT", "price": 100.0}, "VN30")


class _MockResponse:
    def __init__(self, status_code: int, payload: dict[str, object], text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> dict[str, object]:
        return self._payload


def _patch_httpx_client(monkeypatch: pytest.MonkeyPatch, response: _MockResponse) -> None:
    class _Client:
        def __init__(self, timeout: float = 20.0) -> None:
            self.timeout = timeout

        async def __aenter__(self) -> "_Client":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

        async def post(self, *args: object, **kwargs: object) -> _MockResponse:
            return response

    monkeypatch.setattr(data_loader.httpx, "AsyncClient", _Client)


@pytest.mark.asyncio
async def test_remote_engines_openai_anthropic_gemini_alibaba(monkeypatch: pytest.MonkeyPatch) -> None:
    openai = data_loader._OpenAIInsightEngine("sk-demo", "gpt-r", "gpt-c", "gpt-w")  # noqa: SLF001
    _patch_httpx_client(
        monkeypatch,
        _MockResponse(200, {"choices": [{"message": {"content": "  openai ok  "}}]}),
    )
    assert await openai.generate("Need deep risk analysis") == "openai ok"

    _patch_httpx_client(monkeypatch, _MockResponse(500, {}, "openai api_key=sk-sensitive-token"))
    with pytest.raises(RuntimeError, match="OpenAI API error") as openai_exc:
        await openai.generate("plan")
    assert "sk-sensitive-token" not in str(openai_exc.value)
    assert REDACTED in str(openai_exc.value)

    _patch_httpx_client(monkeypatch, _MockResponse(200, {"choices": []}))
    with pytest.raises(RuntimeError, match="empty choices"):
        await openai.generate("plan")

    _patch_httpx_client(monkeypatch, _MockResponse(200, {"choices": [{"message": {"content": "   "}}]}))
    with pytest.raises(RuntimeError, match="empty content"):
        await openai.generate("plan")

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY is missing"):
        await data_loader._OpenAIInsightEngine("", "a", "b", "c").generate("plan")  # noqa: SLF001

    anthropic = data_loader._AnthropicInsightEngine("ak-demo", "claude-r", "claude-c", "claude-w")  # noqa: SLF001
    _patch_httpx_client(
        monkeypatch,
        _MockResponse(200, {"content": [{"type": "text", "text": "A"}, {"type": "text", "text": "B"}]}),
    )
    assert await anthropic.generate("reasoning") == "A\nB"

    _patch_httpx_client(monkeypatch, _MockResponse(200, {"completion": " final text "}))
    assert await anthropic.generate("reasoning") == "final text"

    _patch_httpx_client(monkeypatch, _MockResponse(200, {}))
    with pytest.raises(RuntimeError, match="empty content"):
        await anthropic.generate("reasoning")

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY is missing"):
        await data_loader._AnthropicInsightEngine("", "a", "b", "c").generate("reasoning")  # noqa: SLF001

    gemini = data_loader._GeminiInsightEngine("gk-demo", "gem-r", "gem-c", "gem-w")  # noqa: SLF001
    _patch_httpx_client(
        monkeypatch,
        _MockResponse(200, {"candidates": [{"content": {"parts": [{"text": "G1"}, {"text": "G2"}]}}]}),
    )
    assert await gemini.generate("reasoning") == "G1\nG2"

    _patch_httpx_client(monkeypatch, _MockResponse(500, {}, "gemini token=AIzaSensitiveToken"))
    with pytest.raises(RuntimeError, match="Gemini API error") as gemini_exc:
        await gemini.generate("reasoning")
    assert "AIzaSensitiveToken" not in str(gemini_exc.value)
    assert REDACTED in str(gemini_exc.value)

    _patch_httpx_client(monkeypatch, _MockResponse(200, {}))
    with pytest.raises(RuntimeError, match="empty content"):
        await gemini.generate("reasoning")

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is missing"):
        await data_loader._GeminiInsightEngine("", "a", "b", "c").generate("reasoning")  # noqa: SLF001

    alibaba = data_loader._AlibabaTaskRouterInsightEngine("ali-demo", "https://example", "coder", "reasoning", "writing")  # noqa: SLF001
    _patch_httpx_client(
        monkeypatch,
        _MockResponse(200, {"choices": [{"message": {"content": " ali ok "}}]}),
    )
    assert await alibaba.generate("need plan") == "ali ok"

    _patch_httpx_client(monkeypatch, _MockResponse(500, {}, "alibaba secret=abc"))
    with pytest.raises(RuntimeError, match="Alibaba-compatible API error") as alibaba_exc:
        await alibaba.generate("need plan")
    assert "secret=abc" not in str(alibaba_exc.value)
    assert REDACTED in str(alibaba_exc.value)

    _patch_httpx_client(monkeypatch, _MockResponse(200, {"choices": []}))
    with pytest.raises(RuntimeError, match="empty choices"):
        await alibaba.generate("need plan")

    _patch_httpx_client(monkeypatch, _MockResponse(200, {"choices": [{"message": {"content": ""}}]}))
    with pytest.raises(RuntimeError, match="empty content"):
        await alibaba.generate("need plan")

    with pytest.raises(RuntimeError, match="ALIBABA_API_KEY is missing"):
        await data_loader._AlibabaTaskRouterInsightEngine("", "https://example", "a", "b", "c").generate("plan")  # noqa: SLF001


def test_build_insight_engine_missing_keys_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_AI_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    _, provider, remote_enabled, model_name = data_loader._build_insight_engine_from_env()  # noqa: SLF001
    assert provider == "deterministic"
    assert remote_enabled is False
    assert model_name == "deterministic-v1"

    monkeypatch.setenv("AGENT_AI_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    _, provider, remote_enabled, model_name = data_loader._build_insight_engine_from_env()  # noqa: SLF001
    assert provider == "deterministic"
    assert remote_enabled is False
    assert model_name == "deterministic-v1"

    monkeypatch.setenv("AGENT_AI_PROVIDER", "alibaba")
    monkeypatch.delenv("ALIBABA_API_KEY", raising=False)
    _, provider, remote_enabled, model_name = data_loader._build_insight_engine_from_env()  # noqa: SLF001
    assert provider == "deterministic"
    assert remote_enabled is False
    assert model_name == "deterministic-v1"


def test_build_insight_engine_with_explicit_fallback_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_AI_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AGENT_AI_FALLBACK_ORDER", "anthropic,deterministic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-12345678901234567890")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
    engine, provider, remote_enabled, model_name = data_loader._build_insight_engine_from_env()  # noqa: SLF001
    assert provider == "anthropic"
    assert remote_enabled is True
    assert "router(" in model_name
    assert isinstance(engine, data_loader._FailoverBudgetEngine)  # noqa: SLF001


@pytest.mark.asyncio
async def test_failover_budget_engine_budget_skip_to_deterministic() -> None:
    class _ShouldNotCallRemote:
        async def generate(self, prompt: str) -> str:
            raise RuntimeError("remote should be skipped by budget")

    class _Deterministic:
        async def generate(self, prompt: str) -> str:
            return "deterministic-ok"

    engine = data_loader._FailoverBudgetEngine(  # noqa: SLF001
        [
            data_loader._EngineCandidate(  # noqa: SLF001
                provider="openai",
                model_banner="router(coder=x,reasoning=y,writing=z)",
                engine=_ShouldNotCallRemote(),
                remote=True,
            ),
            data_loader._EngineCandidate(  # noqa: SLF001
                provider="deterministic",
                model_banner="deterministic-v1",
                engine=_Deterministic(),
                remote=False,
            ),
        ],
        budget_usd_per_run=0.00001,
        max_remote_calls=2,
    )
    out = await engine.generate("Need deep reasoning for portfolio strategy and risk analysis.")
    assert out == "deterministic-ok"
    assert engine.last_provider == "deterministic"


def test_local_financial_port_to_dict_branch_and_screener_candidate_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = duckdb.connect(":memory:")
    conn.execute(data_loader._CACHE_DDL)  # noqa: SLF001
    conn.execute(
        """
        INSERT INTO market_cache(symbol,preset,price,change_val,change_pct,volume,high,low,open_price,ceiling,floor,reference,updated_at)
        VALUES ('AAA','VN30',10,0.2,20.0,9000000,11,9,9.8,10.7,9.3,9.8,now())
        """
    )

    class _OverviewFrame:
        @staticmethod
        def to_dict(mode: str) -> list[dict[str, float]]:
            assert mode == "records"
            return [{"pe": 10.0, "roe": 12.0, "debt_to_equity": 0.5}]

    class _Company:
        @staticmethod
        def overview() -> _OverviewFrame:
            return _OverviewFrame()

    class _Stock:
        company = _Company()

    _install_vnstock_module(_Stock(), monkeypatch)
    port = data_loader._LocalFinancialDataPort(conn, preset="VN30", use_external=True)  # noqa: SLF001
    payload = port.get_financial_data("AAA")
    assert payload["source"] in {"vnstock+cache", "cache-derived"}
    assert payload["financial_ratios"]["pe_ratio"] == pytest.approx(10.0)

    screener = data_loader._CacheScreenerPort(conn, preset="VN30", symbols=["AAA"])  # noqa: SLF001
    candidates = asyncio.run(screener.screen())
    assert candidates
    assert candidates[0]["symbol"] == "AAA"


def test_var_historical_low_history_and_empty_returns() -> None:
    conn = duckdb.connect(":memory:")
    conn.execute(data_loader._CACHE_DDL)  # noqa: SLF001
    repo = data_loader._CacheTickRepo(conn, preset="VN30")  # noqa: SLF001

    # < 20 closes => immediate 0
    for idx in range(10):
        conn.execute(
            "INSERT INTO market_candles(symbol,ts,open_price,high,low,close_price,volume) VALUES ('X', ?, 1,1,1,1,100)",
            [idx + 1],
        )
    assert repo.calculate_var_historical("X") == 0.0

    # enough rows but invalid prev<=0 => empty returns => 0
    conn.execute("DELETE FROM market_candles WHERE symbol='Y'")
    for idx in range(30):
        conn.execute(
            "INSERT INTO market_candles(symbol,ts,open_price,high,low,close_price,volume) VALUES ('Y', ?, 0,0,0,0,100)",
            [idx + 100],
        )
    assert repo.calculate_var_historical("Y") == 0.0


@pytest.mark.asyncio
async def test_cached_and_candles_and_update_endpoints_error_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(data_loader, "_get_conn", lambda: (_ for _ in ()).throw(RuntimeError("db down")))

    cached = await data_loader.get_cached_data("VN30")
    assert cached["error"] == "db down"
    assert cached["symbol_count"] == 0

    candles = await data_loader.get_candles("FPT", limit=100)
    assert candles["error"] == "db down"
    assert candles["count"] == 0

    updates = await data_loader.check_updates("VN30")
    assert updates["reason"] == "db_error"
    assert updates["needs_update"] is True


def test_cache_runtime_health_with_schema_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = duckdb.connect(":memory:")
    data_loader._ensure_cache_schema(conn)  # noqa: SLF001
    monkeypatch.setattr(data_loader, "_get_conn", lambda: conn)
    health = data_loader.get_cache_runtime_health()
    assert health["ok"] is True
    assert health["schema_version"] == "2026.03.04-e2"
    assert health["migration_marker"] == "data-loader-cache-migration-e2"
