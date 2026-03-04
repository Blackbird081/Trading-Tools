from __future__ import annotations

import asyncio
import builtins
import sys
import types
from typing import Any

import pytest

from adapters.vnstock.news import VnstockNewsAdapter


class _FakeDataFrame:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def to_dict(self, orient: str) -> list[dict[str, Any]]:
        if orient != "records":
            return []
        return self._rows


def test_normalize_news_accepts_list_dict_and_dataframe() -> None:
    adapter = VnstockNewsAdapter()
    normalized = adapter._normalize_news(  # noqa: SLF001 - internal helper test
        [
            {"title": "A", "source": "s1"},
            {"headline": "B", "publisher": "s2"},
            {"news_title": "C"},
            {"tieu_de": "D"},
        ],
        limit=10,
    )
    assert [item["title"] for item in normalized] == ["A", "B", "C", "D"]

    wrapped = adapter._normalize_news({"data": [{"title": "X"}]}, limit=5)  # noqa: SLF001
    assert wrapped[0]["title"] == "X"

    frame = _FakeDataFrame([{"title": "Y"}])
    framed = adapter._normalize_news(frame, limit=5)  # noqa: SLF001
    assert framed[0]["title"] == "Y"

    wrapped_dict = adapter._normalize_news({"title": "Z", "publisher": "pub"}, limit=5)  # noqa: SLF001
    assert wrapped_dict[0]["title"] == "Z"

    skipped_empty = adapter._normalize_news([{"title": "   "}], limit=5)  # noqa: SLF001
    assert skipped_empty == []


def test_get_headlines_returns_empty_when_source_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = VnstockNewsAdapter()

    class BrokenVnstock:
        def __call__(self) -> Any:
            raise RuntimeError("vnstock unavailable")

    fake_module = types.SimpleNamespace(Vnstock=BrokenVnstock())
    monkeypatch.setitem(sys.modules, "vnstock", fake_module)

    assert adapter.get_headlines("FPT", limit=3) == []


def test_get_headlines_handles_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = VnstockNewsAdapter()
    original_import = builtins.__import__

    def _fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "vnstock":
            raise ImportError("vnstock missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)
    assert adapter.get_headlines("HPG", limit=2) == []


def test_get_headlines_from_news_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = VnstockNewsAdapter()

    class Stock:
        def news(self) -> list[dict[str, str]]:
            return [{"title": "FPT tang truong manh", "source": "mock"}]

    class Vnstock:
        def stock(self, symbol: str, source: str) -> Stock:
            return Stock()

    monkeypatch.setitem(sys.modules, "vnstock", types.SimpleNamespace(Vnstock=lambda: Vnstock()))

    headlines = adapter.get_headlines("FPT", limit=5)
    assert headlines and headlines[0]["title"] == "FPT tang truong manh"


def test_get_headlines_from_news_object_and_company_news(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = VnstockNewsAdapter()

    class NewsObj:
        @staticmethod
        def headlines() -> list[dict[str, str]]:
            return []

        @staticmethod
        def latest() -> list[dict[str, str]]:
            return []

    class CompanyObj:
        @staticmethod
        def news() -> list[dict[str, str]]:
            return [{"title": "Company feed headline"}]

    class Stock:
        news = NewsObj()
        company = CompanyObj()

    class Vnstock:
        def stock(self, symbol: str, source: str) -> Stock:
            return Stock()

    monkeypatch.setitem(sys.modules, "vnstock", types.SimpleNamespace(Vnstock=lambda: Vnstock()))
    headlines = adapter.get_headlines("VCB", limit=3)
    assert headlines[0]["title"] == "Company feed headline"


def test_get_news_async_delegates_to_get_headlines(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = VnstockNewsAdapter()
    monkeypatch.setattr(
        adapter,
        "get_headlines",
        lambda symbol, limit=20: [{"title": f"{symbol}-headline", "source": "unit"}],
    )

    result = asyncio.run(adapter.get_news("VCB", limit=2))
    assert result[0]["title"] == "VCB-headline"
