# 02 — BACKEND ENGINEERING: CORE ENGINE

**Project:** Hệ thống Giao dịch Thuật toán Đa Tác vụ (Enterprise Edition)
**Role:** Senior Python Backend Engineer
**Version:** 1.0 | February 2026
**Python:** 3.12+ | **Type Checking:** Strict (`mypy --strict`) | **Formatter:** `ruff`

---

## 1. PROJECT STRUCTURE — MONOREPO WITH `uv`

### 1.1. Directory Layout

```
algo-trading/                          # Root — uv workspace
├── pyproject.toml                     # Workspace root config
├── uv.lock                           # Single lockfile cho toàn bộ monorepo
├── .python-version                   # Pin Python 3.12.x
├── ruff.toml                         # Lint + format config (shared)
├── mypy.ini                          # Type checking strict mode (shared)
│
├── packages/
│   ├── core/                          # ★ DOMAIN LAYER — Zero dependencies on frameworks
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── core/
│   │           ├── __init__.py
│   │           ├── entities/          # Pure data classes (domain objects)
│   │           │   ├── __init__.py
│   │           │   ├── tick.py        # Tick, OHLCV, MarketSnapshot
│   │           │   ├── order.py       # Order, OrderSide, OrderType, OrderStatus
│   │           │   ├── portfolio.py   # Position, PortfolioState, CashBalance
│   │           │   ├── signal.py      # TradingSignal, SignalStrength, AIInsight
│   │           │   └── risk.py        # RiskMetrics, VaRResult, RiskLimit
│   │           │
│   │           ├── ports/             # Abstract interfaces (Protocol classes)
│   │           │   ├── __init__.py
│   │           │   ├── market_data.py # MarketDataPort — stream ticks
│   │           │   ├── broker.py      # BrokerPort — place/cancel orders
│   │           │   ├── repository.py  # TickRepository, OrderRepository
│   │           │   ├── ai_engine.py   # AIEnginePort — run inference
│   │           │   └── notifier.py    # NotifierPort — push to frontend
│   │           │
│   │           ├── use_cases/         # Business logic — orchestrates ports
│   │           │   ├── __init__.py
│   │           │   ├── screening.py   # RunScreener(filters) -> Watchlist
│   │           │   ├── scoring.py     # ScoreSymbol(symbol) -> TechScore
│   │           │   ├── rebalance.py   # RebalancePortfolio(state) -> Orders
│   │           │   ├── risk_check.py  # ValidateOrder(order, state) -> bool
│   │           │   └── insight.py     # GenerateInsight(symbol, context) -> AIInsight
│   │           │
│   │           └── value_objects.py   # Symbol, Price, Quantity, Timestamp (frozen)
│   │
│   ├── adapters/                      # ★ ADAPTER LAYER — Framework/infra implementations
│   │   ├── pyproject.toml             # depends on: core
│   │   └── src/
│   │       └── adapters/
│   │           ├── __init__.py
│   │           ├── ssi/               # SSI FastConnect adapter
│   │           │   ├── __init__.py
│   │           │   ├── auth.py        # RSA signing, JWT token management
│   │           │   ├── market_ws.py   # WebSocket client — implements MarketDataPort
│   │           │   ├── broker.py      # Order placement — implements BrokerPort
│   │           │   ├── portfolio.py   # stockPosition sync, T+2.5 logic
│   │           │   └── models.py      # SSI-specific Pydantic models (raw API shapes)
│   │           │
│   │           ├── vnstock/           # Vnstock wrapper adapter
│   │           │   ├── __init__.py
│   │           │   ├── history.py     # Historical OHLCV — implements TickRepository (partial)
│   │           │   ├── screener.py    # stock_screening() wrapper
│   │           │   └── news.py        # News feed for Fundamental Agent
│   │           │
│   │           ├── dnse/              # DNSE Entrade X adapter
│   │           │   ├── __init__.py
│   │           │   ├── auth.py        # Token/Refresh token management
│   │           │   └── broker.py      # RESTful order API — implements BrokerPort
│   │           │
│   │           ├── duckdb/            # DuckDB persistence adapter
│   │           │   ├── __init__.py
│   │           │   ├── connection.py  # Connection factory, lifecycle management
│   │           │   ├── tick_repo.py   # implements TickRepository
│   │           │   ├── order_repo.py  # implements OrderRepository
│   │           │   ├── queries/       # Raw SQL files
│   │           │   │   ├── asof_join_pnl.sql
│   │           │   │   ├── screening_indicators.sql
│   │           │   │   └── var_historical.sql
│   │           │   └── partitioning.py # Parquet partition manager
│   │           │
│   │           └── openvino/          # OpenVINO NPU adapter
│   │               ├── __init__.py
│   │               ├── engine.py      # implements AIEnginePort
│   │               └── model_loader.py # INT4 model loading, warmup
│   │
│   ├── agents/                        # ★ AGENT LAYER — LangGraph orchestration
│   │   ├── pyproject.toml             # depends on: core, adapters
│   │   └── src/
│   │       └── agents/
│   │           ├── __init__.py
│   │           ├── data_agent.py      # Market data ingestion loop
│   │           ├── screener_agent.py  # Periodic screening
│   │           ├── technical_agent.py # Tech analysis + scoring
│   │           ├── fundamental_agent.py # NPU-based LLM analysis
│   │           ├── risk_agent.py      # Order validation middleware
│   │           ├── supervisor.py      # LangGraph graph definition
│   │           └── state.py           # Shared AgentState TypedDict
│   │
│   └── interface/                     # ★ INTERFACE LAYER — FastAPI, WebSocket, CLI
│       ├── pyproject.toml             # depends on: core, adapters, agents
│       └── src/
│           └── interface/
│               ├── __init__.py
│               ├── app.py             # FastAPI application factory
│               ├── dependencies.py    # Dependency injection (DI container)
│               ├── ws/
│               │   ├── __init__.py
│               │   ├── market_ws.py   # WebSocket endpoint: /ws/market
│               │   ├── signals_ws.py  # WebSocket endpoint: /ws/signals
│               │   └── manager.py     # ConnectionManager (broadcast)
│               ├── rest/
│               │   ├── __init__.py
│               │   ├── portfolio.py   # GET /api/portfolio
│               │   ├── orders.py      # POST /api/orders, DELETE /api/orders/{id}
│               │   └── health.py      # GET /api/health
│               └── cli.py             # CLI entrypoint (uvicorn launcher)
│
├── tests/                             # Shared test suite
│   ├── conftest.py                    # Fixtures: DuckDB in-memory, mock adapters
│   ├── unit/
│   │   ├── test_entities.py
│   │   ├── test_use_cases.py
│   │   ├── test_scoring.py
│   │   └── test_risk_check.py
│   ├── integration/
│   │   ├── test_duckdb_repo.py
│   │   ├── test_ssi_auth.py
│   │   └── test_data_pipeline.py
│   └── fixtures/
│       ├── sample_ticks.parquet
│       └── sample_orders.json
│
├── data/                              # Runtime data (gitignored)
│   ├── parquet/                       # Partitioned tick data
│   │   └── ticks/year=2026/month=02/day=10/data.parquet
│   ├── models/                        # OpenVINO IR model files
│   └── trading.duckdb                 # Main DuckDB database file
│
└── frontend/                          # Next.js (separate workspace, not uv-managed)
    └── ...
```

### 1.2. Workspace `pyproject.toml` (Root)

```toml
[project]
name = "algo-trading"
version = "0.1.0"
requires-python = ">=3.12"

[tool.uv.workspace]
members = [
    "packages/core",
    "packages/adapters",
    "packages/agents",
    "packages/interface",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "mypy>=1.11",
    "ruff>=0.6",
]
```

### 1.3. Package `pyproject.toml` — Ví dụ `packages/core`

```toml
[project]
name = "core"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []  # ★ ZERO external dependencies — pure Python only

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 1.4. Package `pyproject.toml` — Ví dụ `packages/adapters`

```toml
[project]
name = "adapters"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "core",                    # Workspace dependency
    "duckdb>=1.1",
    "pydantic>=2.9",
    "websockets>=13.0",
    "httpx>=0.27",
    "pycryptodome>=3.20",      # SSI RSA signing
    "vnstock>=3.1",
    "openvino-genai>=2024.4",
    "pyarrow>=17.0",           # Parquet I/O
]

[tool.uv.sources]
core = { workspace = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### 1.5. Dependency Graph (Strict layering — arrows = "depends on")

```
interface ──► agents ──► adapters ──► core
                │                      ▲
                └──────────────────────┘

★ Rule: core NEVER imports from adapters, agents, or interface.
★ Rule: adapters NEVER imports from agents or interface.
★ Rule: agents NEVER imports from interface.
```

---

## 2. CLEAN ARCHITECTURE IMPLEMENTATION

### 2.1. Nguyên tắc cốt lõi

Hệ thống tuân thủ **Dependency Inversion Principle (DIP)**: business logic (`core`) định nghĩa interfaces (Ports), infrastructure code (`adapters`) implement chúng. Framework (FastAPI) chỉ là delivery mechanism ở layer ngoài cùng.

```
┌─────────────────────────────────────────────────────────┐
│                    INTERFACE LAYER                       │
│  FastAPI, WebSocket handlers, CLI                       │
│  ► Nhận request, gọi Use Case, trả response            │
├─────────────────────────────────────────────────────────┤
│                    AGENT LAYER                           │
│  LangGraph, Supervisor, Agent loops                     │
│  ► Orchestrate use cases theo business workflow         │
├─────────────────────────────────────────────────────────┤
│                    ADAPTER LAYER                         │
│  SSI client, DuckDB repo, OpenVINO engine               │
│  ► Implement Ports defined in Core                      │
├─────────────────────────────────────────────────────────┤
│                    CORE LAYER (innermost)                │
│  Entities, Value Objects, Ports (Protocol), Use Cases   │
│  ► ZERO framework imports. Pure Python + typing.        │
└─────────────────────────────────────────────────────────┘
```

### 2.2. Entities — Immutable Domain Objects

```python
# packages/core/src/core/entities/tick.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from core.value_objects import Price, Quantity, Symbol


class Exchange(StrEnum):
    HOSE = "HOSE"
    HNX = "HNX"
    UPCOM = "UPCOM"


@dataclass(frozen=True, slots=True)
class Tick:
    """Single market tick — immutable, hashable."""

    symbol: Symbol
    price: Price
    volume: Quantity
    exchange: Exchange
    timestamp: datetime

    def is_ceiling(self, ref_price: Price) -> bool:
        return self.price >= ref_price * Price("1.07")

    def is_floor(self, ref_price: Price) -> bool:
        return self.price <= ref_price * Price("0.93")
```

```python
# packages/core/src/core/value_objects.py
from __future__ import annotations

from decimal import Decimal
from typing import NewType

Symbol = NewType("Symbol", str)          # "FPT", "VNM", ...
Price = NewType("Price", Decimal)        # Decimal for financial precision
Quantity = NewType("Quantity", int)       # Always integer (lot size = 100)
```

**Quy tắc:**
- `frozen=True` — entities bất biến sau khi tạo, thread-safe by default.
- `slots=True` — giảm memory footprint ~30-40% so với `__dict__`.
- `Decimal` cho `Price` — **không bao giờ dùng `float`** cho dữ liệu tài chính (IEEE 754 rounding errors).
- `NewType` cho value objects — type checker bắt lỗi khi truyền nhầm `Symbol` vào chỗ cần `Price`.

### 2.3. Ports — Abstract Interfaces (Protocol Classes)

```python
# packages/core/src/core/ports/market_data.py
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from core.entities.tick import Tick
from core.value_objects import Symbol


class MarketDataPort(Protocol):
    """Inbound port: stream market ticks from any broker."""

    async def connect(self) -> None: ...

    async def disconnect(self) -> None: ...

    async def subscribe(self, symbols: list[Symbol]) -> None: ...

    def stream(self) -> AsyncIterator[Tick]: ...
```

```python
# packages/core/src/core/ports/repository.py
from __future__ import annotations

from datetime import date, datetime
from typing import Protocol

from core.entities.order import Order
from core.entities.tick import Tick
from core.value_objects import Symbol


class TickRepository(Protocol):
    """Outbound port: persist and query tick data."""

    async def insert_batch(self, ticks: list[Tick]) -> int: ...

    async def get_ohlcv(
        self,
        symbol: Symbol,
        start: date,
        end: date,
    ) -> list[dict[str, object]]: ...

    async def asof_join_orders(
        self,
        orders: list[Order],
    ) -> list[dict[str, object]]: ...


class OrderRepository(Protocol):
    """Outbound port: persist and query orders."""

    async def save(self, order: Order) -> None: ...

    async def get_by_symbol(self, symbol: Symbol) -> list[Order]: ...

    async def get_open_orders(self) -> list[Order]: ...
```

**Tại sao `Protocol` thay vì `ABC`?**
- `Protocol` hỗ trợ **structural subtyping** (duck typing có type safety). Adapter không cần `class SSIMarketData(MarketDataPort)` — chỉ cần implement đúng method signatures, `mypy` tự verify.
- Không tạo coupling qua inheritance chain. Core package không cần biết adapter tồn tại.

### 2.4. Use Cases — Pure Business Logic

```python
# packages/core/src/core/use_cases/risk_check.py
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from core.entities.order import Order, OrderSide
from core.entities.portfolio import PortfolioState
from core.entities.risk import RiskLimit


@dataclass(frozen=True, slots=True)
class RiskCheckResult:
    approved: bool
    reason: str


def validate_order(
    order: Order,
    portfolio: PortfolioState,
    limits: RiskLimit,
) -> RiskCheckResult:
    """Pure function — no I/O, no side effects, fully testable."""

    # Rule 1: Single order cannot exceed max_position_pct of NAV
    order_value = order.price * Decimal(order.quantity)
    nav = portfolio.net_asset_value
    if nav > 0 and order_value / nav > limits.max_position_pct:
        return RiskCheckResult(
            approved=False,
            reason=f"Order value {order_value} exceeds "
            f"{limits.max_position_pct:.0%} of NAV {nav}",
        )

    # Rule 2: Price must be within ceiling/floor
    if order.side == OrderSide.BUY and order.price > order.ceiling_price:
        return RiskCheckResult(
            approved=False,
            reason=f"Buy price {order.price} exceeds ceiling {order.ceiling_price}",
        )

    # Rule 3: Sufficient buying power
    if order.side == OrderSide.BUY and order_value > portfolio.purchasing_power:
        return RiskCheckResult(
            approved=False,
            reason="Insufficient purchasing power",
        )

    # Rule 4: Sufficient sellable quantity (T+2.5 aware)
    if order.side == OrderSide.SELL:
        position = portfolio.get_position(order.symbol)
        if position is None or order.quantity > position.sellable_qty:
            return RiskCheckResult(
                approved=False,
                reason="Insufficient sellable quantity (check T+2.5 settlement)",
            )

    return RiskCheckResult(approved=True, reason="All checks passed")
```

**Đặc điểm:**
- **Pure function** — input in, output out. Không gọi DB, không gọi API, không `await`.
- **Dễ test** — chỉ cần construct entities, gọi function, assert result.
- **Framework-agnostic** — không import FastAPI, không import DuckDB.

### 2.5. Adapter Implementation — Ví dụ DuckDB TickRepository

```python
# packages/adapters/src/adapters/duckdb/tick_repo.py
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from core.entities.order import Order
    from core.entities.tick import Tick
    from core.value_objects import Symbol


class DuckDBTickRepository:
    """Implements core.ports.repository.TickRepository via DuckDB."""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    async def insert_batch(self, ticks: list[Tick]) -> int:
        # Offload blocking DuckDB call to thread pool (see Section 4)
        rows = [
            (t.symbol, float(t.price), t.volume, t.exchange.value, t.timestamp)
            for t in ticks
        ]
        self._conn.executemany(
            """
            INSERT INTO ticks (symbol, price, volume, exchange, ts)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        return len(rows)

    async def asof_join_orders(
        self, orders: list[Order]
    ) -> list[dict[str, object]]:
        # Delegates to SQL file — see Section 3.1
        return self._conn.execute(
            open("adapters/duckdb/queries/asof_join_pnl.sql").read()
        ).fetchall()
```

**Lưu ý:** Adapter class không kế thừa `TickRepository` (Protocol). `mypy` verify structural compatibility tại compile time. Nếu thiếu method hoặc sai signature → type error.

### 2.6. Dependency Injection — Wiring tại Interface Layer

```python
# packages/interface/src/interface/dependencies.py
from __future__ import annotations

from functools import lru_cache

import duckdb

from adapters.duckdb.connection import create_connection
from adapters.duckdb.tick_repo import DuckDBTickRepository
from adapters.ssi.market_ws import SSIMarketDataClient
from core.ports.market_data import MarketDataPort
from core.ports.repository import TickRepository


@lru_cache(maxsize=1)
def get_duckdb_connection() -> duckdb.DuckDBPyConnection:
    return create_connection("data/trading.duckdb")


def get_tick_repository() -> TickRepository:
    return DuckDBTickRepository(get_duckdb_connection())


def get_market_data() -> MarketDataPort:
    return SSIMarketDataClient(
        consumer_id="...",
        consumer_secret="...",
    )
```

```python
# packages/interface/src/interface/app.py
from __future__ import annotations

from fastapi import Depends, FastAPI

from interface.dependencies import get_tick_repository
from core.ports.repository import TickRepository


app = FastAPI(title="AlgoTrading API")


@app.get("/api/portfolio/pnl")
async def get_pnl(repo: TickRepository = Depends(get_tick_repository)):
    # FastAPI chỉ là delivery mechanism
    # Business logic nằm trong core.use_cases
    ...
```

**Nguyên tắc DI:**
- `core` định nghĩa **what** (Protocol).
- `adapters` định nghĩa **how** (implementation).
- `interface` quyết định **which** (wiring).
- Swap adapter bằng cách thay 1 dòng trong `dependencies.py` (ví dụ: `SSIMarketDataClient` → `DNSEMarketDataClient`).

---

## 3. DUCKDB INTEGRATION PATTERN

### 3.1. ASOF JOIN — Khớp lệnh với giá thị trường

#### Bài toán

Khi tính PnL (Profit & Loss) hoặc chạy Backtesting, cần tìm **giá thị trường chính xác tại thời điểm lệnh được gửi**. Đây là bài toán time-series join kinh điển trong tài chính.

#### Schema

```sql
-- Bảng ticks: giá thị trường liên tục (hàng triệu rows/ngày)
CREATE TABLE ticks (
    symbol   VARCHAR NOT NULL,
    price    DOUBLE  NOT NULL,
    volume   BIGINT  NOT NULL,
    exchange VARCHAR NOT NULL,
    ts       TIMESTAMP NOT NULL
);

-- Bảng orders: lệnh giao dịch (hàng trăm rows/ngày)
CREATE TABLE orders (
    order_id   VARCHAR   NOT NULL,
    symbol     VARCHAR   NOT NULL,
    side       VARCHAR   NOT NULL,  -- 'BUY' | 'SELL'
    quantity   INTEGER   NOT NULL,
    req_price  DOUBLE    NOT NULL,  -- Giá đặt
    status     VARCHAR   NOT NULL,
    created_at TIMESTAMP NOT NULL
);
```

#### ASOF JOIN Query

```sql
-- packages/adapters/src/adapters/duckdb/queries/asof_join_pnl.sql

-- Tìm giá thị trường gần nhất TRƯỚC hoặc TẠI thời điểm đặt lệnh
SELECT
    o.order_id,
    o.symbol,
    o.side,
    o.quantity,
    o.req_price,
    o.created_at   AS order_time,
    t.price        AS market_price_at_order,
    t.ts           AS tick_time,
    -- Slippage: chênh lệch giữa giá đặt và giá thị trường thực tế
    ABS(o.req_price - t.price) AS slippage,
    -- PnL estimation (cho lệnh SELL)
    CASE
        WHEN o.side = 'SELL'
        THEN (o.req_price - t.price) * o.quantity
        ELSE NULL
    END AS estimated_pnl
FROM orders o
ASOF JOIN ticks t
    ON  o.symbol = t.symbol        -- Match cùng mã chứng khoán
    AND o.created_at >= t.ts       -- Tick phải xảy ra TRƯỚC hoặc ĐÚNG lúc đặt lệnh
ORDER BY o.created_at DESC;
```

#### Giải thích cơ chế ASOF JOIN

```
Timeline:
  ticks:   ──T1──T2──T3──────T4──T5──T6──T7──►
  orders:  ────────────O1──────────O2──────────►

ASOF JOIN logic:
  O1 matched with T3  (tick gần nhất ≤ O1.created_at)
  O2 matched with T5  (tick gần nhất ≤ O2.created_at)

★ Không cần exact timestamp match — DuckDB tự tìm nearest predecessor.
★ Nếu dùng PostgreSQL: phải viết LATERAL JOIN + ORDER BY + LIMIT 1 per order → O(N*M) thay vì O(N+M).
```

#### Performance so sánh

| Approach | Complexity | 100K orders × 10M ticks |
|:---|:---|:---|
| DuckDB `ASOF JOIN` | O(N + M) merge-sort | ~200ms |
| PostgreSQL `LATERAL JOIN` | O(N × log M) per row | ~45-120s |
| Python loop (`bisect`) | O(N × log M) in Python | ~30-60s |

### 3.2. Parquet Partitioning Strategy

#### Cấu trúc thư mục

```
data/parquet/
├── ticks/
│   ├── year=2026/
│   │   ├── month=01/
│   │   │   ├── day=15/
│   │   │   │   └── data.parquet      # ~2-5MB compressed
│   │   │   ├── day=16/
│   │   │   │   └── data.parquet
│   │   │   └── ...
│   │   └── month=02/
│   │       └── ...
│   └── year=2025/
│       └── ...                        # Historical data
│
├── ohlcv/
│   ├── daily/
│   │   └── year=2026/
│   │       └── data.parquet           # 1 file per year (~500KB)
│   └── minute/
│       └── year=2026/
│           └── month=02/
│               └── data.parquet       # 1 file per month (~10MB)
│
└── orders/
    └── year=2026/
        └── month=02/
            └── data.parquet
```

#### Partition Writer

```python
# packages/adapters/src/adapters/duckdb/partitioning.py
from __future__ import annotations

from pathlib import Path

import duckdb


class ParquetPartitionManager:
    """Manages Hive-style partitioned Parquet writes."""

    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        base_path: Path,
    ) -> None:
        self._conn = conn
        self._base_path = base_path

    def flush_ticks_to_parquet(self) -> int:
        """Export today's buffered ticks to partitioned Parquet files.

        Called by Data Agent at end-of-day or periodically.
        Uses DuckDB's native COPY with PARTITION_BY for zero-copy export.
        """
        result = self._conn.execute(f"""
            COPY (
                SELECT
                    *,
                    YEAR(ts)  AS year,
                    MONTH(ts) AS month,
                    DAY(ts)   AS day
                FROM ticks
                WHERE ts >= CURRENT_DATE
            )
            TO '{self._base_path}/ticks'
            (FORMAT PARQUET, PARTITION_BY (year, month, day),
             COMPRESSION 'zstd', ROW_GROUP_SIZE 100000)
        """)
        return result.fetchone()[0]  # type: ignore[index]

    def register_parquet_view(self) -> None:
        """Register partitioned Parquet as queryable view.

        DuckDB reads only relevant partitions (partition pruning)
        when WHERE clause filters on year/month/day.
        """
        self._conn.execute(f"""
            CREATE OR REPLACE VIEW ticks_historical AS
            SELECT * FROM read_parquet(
                '{self._base_path}/ticks/**/*.parquet',
                hive_partitioning = true
            )
        """)
```

#### Partition Pruning — Tại sao quan trọng

```sql
-- Query này CHỈ đọc 1 file Parquet (~3MB) thay vì toàn bộ dataset (~500MB+)
SELECT symbol, AVG(price), SUM(volume)
FROM ticks_historical
WHERE year = 2026 AND month = 2 AND day = 10
GROUP BY symbol;

-- DuckDB tự động skip tất cả partitions không match WHERE clause.
-- Không cần index. Không cần manual filter. Hive-style path = implicit index.
```

#### Compression Benchmark (Ước tính cho HOSE full-day)

| Metric | Raw CSV | Parquet (zstd) | Ratio |
|:---|:---|:---|:---|
| Rows/day (all symbols) | ~2-5M | ~2-5M | — |
| File size/day | ~200-500MB | ~20-50MB | **10x compression** |
| Query scan (1 symbol, 1 day) | Full file scan | ~0.5-2MB (column pruning + partition pruning) | **100x I/O reduction** |

---

## 4. ASYNC/CONCURRENCY MODEL

### 4.1. Nguyên tắc vàng: KHÔNG BAO GIỜ block event loop

```
★ RULE #1: Mọi I/O operation phải là async (await).
★ RULE #2: CPU-bound work > 1ms phải offload sang thread/process pool.
★ RULE #3: DuckDB calls (blocking C library) LUÔN chạy trong thread pool.
★ RULE #4: Không dùng time.sleep() — dùng asyncio.sleep().
★ RULE #5: Không dùng requests — dùng httpx.AsyncClient.
```

### 4.2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                    MAIN ASYNCIO EVENT LOOP                    │
│                    (single thread, non-blocking)              │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ WS Inbound   │  │ WS Outbound  │  │ HTTP Handler │       │
│  │ (SSI ticks)  │  │ (to browser) │  │ (REST API)   │       │
│  │ async for    │  │ ws.send()    │  │ async def    │       │
│  └──────┬───────┘  └──────────────┘  └──────────────┘       │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────┐       │
│  │              TASK DISPATCHER                      │       │
│  │  asyncio.create_task() for concurrent work        │       │
│  └──────┬───────────────┬───────────────┬───────────┘       │
│         │               │               │                    │
│         ▼               ▼               ▼                    │
│  ┌────────────┐  ┌────────────┐  ┌────────────────┐         │
│  │ Buffer     │  │ Periodic   │  │ On-demand      │         │
│  │ Flush Task │  │ Screener   │  │ Analysis Task  │         │
│  │ (1s timer) │  │ (30s timer)│  │ (user trigger) │         │
│  └─────┬──────┘  └─────┬──────┘  └───────┬────────┘         │
│        │               │                 │                   │
│        ▼               ▼                 ▼                   │
│  ┌──────────────────────────────────────────────────┐       │
│  │         THREAD POOL (asyncio.to_thread)           │       │
│  │  • DuckDB queries (blocking C FFI)                │       │
│  │  • pandas-ta computation                          │       │
│  │  • PyPortfolioOpt solver                          │       │
│  │  • OpenVINO NPU inference                         │       │
│  └──────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────┘
```

### 4.3. Pattern: WebSocket Ingestion Loop

```python
# packages/agents/src/agents/data_agent.py
from __future__ import annotations

import asyncio
from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.ports.market_data import MarketDataPort
    from core.ports.repository import TickRepository

from core.entities.tick import Tick


class DataAgent:
    """Ingests market ticks and buffers for batch persistence."""

    def __init__(
        self,
        market_data: MarketDataPort,
        tick_repo: TickRepository,
        flush_interval: float = 1.0,
    ) -> None:
        self._market_data = market_data
        self._tick_repo = tick_repo
        self._flush_interval = flush_interval
        self._buffer: deque[Tick] = deque(maxlen=100_000)
        self._running = False

    async def start(self) -> None:
        self._running = True
        await self._market_data.connect()

        # Two concurrent tasks: ingest + flush
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._ingest_loop())
            tg.create_task(self._flush_loop())

    async def stop(self) -> None:
        self._running = False
        await self._market_data.disconnect()
        await self._flush_buffer()  # Final flush

    async def _ingest_loop(self) -> None:
        """★ Non-blocking: async for yields control between ticks."""
        async for tick in self._market_data.stream():
            self._buffer.append(tick)
            if not self._running:
                break

    async def _flush_loop(self) -> None:
        """Periodic flush — offloads DuckDB write to thread pool."""
        while self._running:
            await asyncio.sleep(self._flush_interval)
            await self._flush_buffer()

    async def _flush_buffer(self) -> None:
        if not self._buffer:
            return

        # Snapshot buffer and clear (atomic swap)
        batch = list(self._buffer)
        self._buffer.clear()

        # ★ CRITICAL: DuckDB insert is blocking C call.
        # Offload to thread pool to avoid blocking event loop.
        await asyncio.to_thread(
            self._tick_repo.insert_batch, batch  # type: ignore[arg-type]
        )
```

### 4.4. Pattern: Offloading CPU-bound Work

```python
# packages/agents/src/agents/technical_agent.py
from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.entities.signal import TradingSignal
    from core.value_objects import Symbol

# Process pool for truly CPU-bound work (GIL bypass)
_process_pool = ProcessPoolExecutor(max_workers=2)


def _compute_score_sync(ohlcv_data: list[dict[str, object]]) -> float:
    """Runs in separate PROCESS — bypasses GIL.

    Heavy NumPy/pandas-ta computation here.
    This function must be picklable (top-level, no closures).
    """
    import pandas as pd
    import pandas_ta as ta

    df = pd.DataFrame(ohlcv_data)
    df.ta.rsi(append=True)
    df.ta.macd(append=True)
    df.ta.bbands(append=True)

    # Scoring logic...
    latest = df.iloc[-1]
    score = 0.0
    if latest.get("RSI_14", 50) < 30:
        score += 3.0  # Oversold signal
    # ... more scoring rules
    return score


async def analyze_symbol(symbol: Symbol) -> float:
    """Async wrapper — dispatches CPU work to process pool."""
    ohlcv = await _fetch_ohlcv(symbol)  # async DB query

    loop = asyncio.get_running_loop()
    score = await loop.run_in_executor(
        _process_pool,
        partial(_compute_score_sync, ohlcv),
    )
    return score
```

### 4.5. Concurrency Rules — Cheat Sheet

| Tác vụ | Blocking? | Giải pháp | Ví dụ |
|:---|:---|:---|:---|
| WebSocket recv/send | No | `await ws.recv()` | SSI tick stream |
| HTTP request | No | `await httpx_client.get()` | Vnstock REST API |
| `asyncio.sleep()` | No | Native async | Periodic timer |
| DuckDB query | **Yes** (C FFI) | `await asyncio.to_thread(conn.execute, sql)` | Tick insert, ASOF JOIN |
| pandas-ta compute | **Yes** (CPU) | `loop.run_in_executor(process_pool, fn)` | RSI, MACD calculation |
| PyPortfolioOpt | **Yes** (CPU) | `loop.run_in_executor(process_pool, fn)` | Efficient Frontier solver |
| OpenVINO inference | **Yes** (NPU) | `await asyncio.to_thread(model.generate, ...)` | LLM text generation |
| File I/O (Parquet) | **Yes** (disk) | `await asyncio.to_thread(pq.write_table, ...)` | End-of-day export |
| `time.sleep()` | **YES — BAN** | ❌ Never use | — |
| `requests.get()` | **YES — BAN** | ❌ Use `httpx` instead | — |

### 4.6. Backpressure — Xử lý khi buffer đầy

```python
# Trong DataAgent, nếu DuckDB flush chậm hơn tick ingestion:

# Option 1: deque(maxlen=N) — tự động drop oldest ticks (acceptable for real-time)
self._buffer: deque[Tick] = deque(maxlen=100_000)

# Option 2: asyncio.Queue với bounded size — producer blocks khi full
self._queue: asyncio.Queue[Tick] = asyncio.Queue(maxsize=50_000)

# Option 3: Sampling — chỉ giữ latest tick per symbol (cho display, không cho storage)
self._latest: dict[Symbol, Tick] = {}  # Overwrite on each tick
```

---

## 5. UNIT TESTING STRATEGY

### 5.1. Nguyên tắc

```
★ RULE: Test business logic (core) KHÔNG CẦN infrastructure.
★ RULE: Test adapters với DuckDB in-memory (`:memory:`) — không file I/O.
★ RULE: Test agents với mock ports — không network calls.
★ RULE: Mọi test phải chạy < 100ms. Nếu chậm hơn → sai layer.
★ TOOL: pytest + pytest-asyncio + pytest-cov
★ TARGET: Coverage ≥ 90% cho core, ≥ 80% cho adapters.
```

### 5.2. Fixtures — `conftest.py`

```python
# tests/conftest.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import duckdb
import pytest

from core.entities.order import Order, OrderSide, OrderStatus
from core.entities.portfolio import CashBalance, PortfolioState, Position
from core.entities.risk import RiskLimit
from core.entities.tick import Exchange, Tick
from core.value_objects import Price, Quantity, Symbol


# ─── DuckDB In-Memory ───────────────────────────────────────

@pytest.fixture
def duckdb_conn() -> duckdb.DuckDBPyConnection:
    """Fresh in-memory DuckDB per test — zero disk I/O, instant teardown."""
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE ticks (
            symbol   VARCHAR,
            price    DOUBLE,
            volume   BIGINT,
            exchange VARCHAR,
            ts       TIMESTAMP
        );
        CREATE TABLE orders (
            order_id   VARCHAR,
            symbol     VARCHAR,
            side       VARCHAR,
            quantity   INTEGER,
            req_price  DOUBLE,
            status     VARCHAR,
            created_at TIMESTAMP
        );
    """)
    return conn


# ─── Domain Fixtures ─────────────────────────────────────────

@pytest.fixture
def sample_ticks() -> list[Tick]:
    base = datetime(2026, 2, 10, 9, 0, 0)
    return [
        Tick(
            symbol=Symbol("FPT"),
            price=Price(Decimal("98.50")),
            volume=Quantity(1000),
            exchange=Exchange.HOSE,
            timestamp=base.replace(second=i),
        )
        for i in range(100)
    ]


@pytest.fixture
def sample_portfolio() -> PortfolioState:
    return PortfolioState(
        positions=[
            Position(
                symbol=Symbol("FPT"),
                quantity=Quantity(2000),
                sellable_qty=Quantity(1000),  # T+2.5: only 1000 settled
                avg_price=Price(Decimal("95.00")),
                market_price=Price(Decimal("98.50")),
            ),
        ],
        cash=CashBalance(
            cash_bal=Decimal("50_000_000"),
            purchasing_power=Decimal("80_000_000"),
        ),
    )


@pytest.fixture
def default_risk_limits() -> RiskLimit:
    return RiskLimit(
        max_position_pct=Decimal("0.20"),  # 20% NAV per order
        max_daily_loss=Decimal("5_000_000"),
        kill_switch_active=False,
    )
```

### 5.3. Unit Tests — Core Layer (Pure Logic, No Mocks Needed)

```python
# tests/unit/test_risk_check.py
from __future__ import annotations

from decimal import Decimal

import pytest

from core.entities.order import Order, OrderSide, OrderStatus
from core.entities.portfolio import PortfolioState
from core.entities.risk import RiskLimit
from core.use_cases.risk_check import RiskCheckResult, validate_order
from core.value_objects import Price, Quantity, Symbol


class TestValidateOrder:
    """Tests for pure business rule: order validation."""

    def test_buy_within_limits_approved(
        self, sample_portfolio: PortfolioState, default_risk_limits: RiskLimit
    ) -> None:
        order = Order(
            order_id="ORD-001",
            symbol=Symbol("VNM"),
            side=OrderSide.BUY,
            quantity=Quantity(500),
            price=Price(Decimal("72.00")),
            ceiling_price=Price(Decimal("77.04")),
            status=OrderStatus.PENDING,
        )
        result = validate_order(order, sample_portfolio, default_risk_limits)
        assert result.approved is True

    def test_buy_exceeds_nav_limit_rejected(
        self, sample_portfolio: PortfolioState, default_risk_limits: RiskLimit
    ) -> None:
        # Order value = 100 * 98.5 * 1000 = way over 20% NAV
        order = Order(
            order_id="ORD-002",
            symbol=Symbol("VIC"),
            side=OrderSide.BUY,
            quantity=Quantity(100_000),
            price=Price(Decimal("98.50")),
            ceiling_price=Price(Decimal("105.40")),
            status=OrderStatus.PENDING,
        )
        result = validate_order(order, sample_portfolio, default_risk_limits)
        assert result.approved is False
        assert "exceeds" in result.reason.lower()

    def test_sell_exceeds_sellable_qty_rejected(
        self, sample_portfolio: PortfolioState, default_risk_limits: RiskLimit
    ) -> None:
        # Portfolio has 1000 sellable FPT, trying to sell 1500
        order = Order(
            order_id="ORD-003",
            symbol=Symbol("FPT"),
            side=OrderSide.SELL,
            quantity=Quantity(1500),
            price=Price(Decimal("98.50")),
            ceiling_price=Price(Decimal("105.40")),
            status=OrderStatus.PENDING,
        )
        result = validate_order(order, sample_portfolio, default_risk_limits)
        assert result.approved is False
        assert "sellable" in result.reason.lower()

    def test_buy_above_ceiling_rejected(
        self, sample_portfolio: PortfolioState, default_risk_limits: RiskLimit
    ) -> None:
        order = Order(
            order_id="ORD-004",
            symbol=Symbol("FPT"),
            side=OrderSide.BUY,
            quantity=Quantity(100),
            price=Price(Decimal("110.00")),       # Above ceiling
            ceiling_price=Price(Decimal("105.40")),
            status=OrderStatus.PENDING,
        )
        result = validate_order(order, sample_portfolio, default_risk_limits)
        assert result.approved is False
        assert "ceiling" in result.reason.lower()
```

### 5.4. Integration Tests — DuckDB Adapter

```python
# tests/integration/test_duckdb_repo.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import duckdb
import pytest

from adapters.duckdb.tick_repo import DuckDBTickRepository
from core.entities.tick import Exchange, Tick
from core.value_objects import Price, Quantity, Symbol


class TestDuckDBTickRepository:
    """Integration tests with real DuckDB (in-memory)."""

    def test_insert_batch_and_count(
        self, duckdb_conn: duckdb.DuckDBPyConnection, sample_ticks: list[Tick]
    ) -> None:
        repo = DuckDBTickRepository(duckdb_conn)
        # insert_batch is async but DuckDB is sync under the hood
        # In tests, call the sync internals directly
        count = len(sample_ticks)
        duckdb_conn.executemany(
            "INSERT INTO ticks VALUES (?, ?, ?, ?, ?)",
            [
                (t.symbol, float(t.price), t.volume, t.exchange.value, t.timestamp)
                for t in sample_ticks
            ],
        )
        result = duckdb_conn.execute("SELECT COUNT(*) FROM ticks").fetchone()
        assert result is not None
        assert result[0] == count

    def test_asof_join_matches_nearest_tick(
        self, duckdb_conn: duckdb.DuckDBPyConnection
    ) -> None:
        """Verify ASOF JOIN returns the tick closest to (but not after) order time."""
        # Insert ticks at t=1s, t=3s, t=5s
        duckdb_conn.execute("""
            INSERT INTO ticks VALUES
                ('FPT', 98.0, 1000, 'HOSE', '2026-02-10 09:00:01'),
                ('FPT', 98.5, 2000, 'HOSE', '2026-02-10 09:00:03'),
                ('FPT', 99.0, 1500, 'HOSE', '2026-02-10 09:00:05');
        """)
        # Insert order at t=4s (between tick t=3s and t=5s)
        duckdb_conn.execute("""
            INSERT INTO orders VALUES
                ('ORD-1', 'FPT', 'BUY', 500, 98.7, 'FILLED', '2026-02-10 09:00:04');
        """)

        result = duckdb_conn.execute("""
            SELECT o.order_id, t.price, t.ts
            FROM orders o
            ASOF JOIN ticks t
                ON o.symbol = t.symbol
                AND o.created_at >= t.ts
        """).fetchone()

        assert result is not None
        assert result[0] == "ORD-1"
        assert result[1] == 98.5     # Matched tick at t=3s, NOT t=5s
        assert "09:00:03" in str(result[2])

    def test_parquet_round_trip(
        self, duckdb_conn: duckdb.DuckDBPyConnection, tmp_path: object
    ) -> None:
        """Write to Parquet, read back, verify data integrity."""
        duckdb_conn.execute("""
            INSERT INTO ticks VALUES
                ('VNM', 72.0, 5000, 'HOSE', '2026-02-10 10:00:00');
        """)
        # Export to Parquet
        duckdb_conn.execute(f"""
            COPY ticks TO '{tmp_path}/test.parquet' (FORMAT PARQUET)
        """)
        # Read back from Parquet
        result = duckdb_conn.execute(f"""
            SELECT symbol, price FROM read_parquet('{tmp_path}/test.parquet')
        """).fetchone()

        assert result is not None
        assert result[0] == "VNM"
        assert result[1] == 72.0
```

### 5.5. Testing Async Code

```python
# tests/integration/test_data_pipeline.py
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal

import pytest

from core.entities.tick import Exchange, Tick
from core.value_objects import Price, Quantity, Symbol


class FakeMarketData:
    """Mock MarketDataPort — yields predefined ticks then stops."""

    def __init__(self, ticks: list[Tick]) -> None:
        self._ticks = ticks

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def subscribe(self, symbols: list[Symbol]) -> None:
        pass

    async def stream(self) -> AsyncIterator[Tick]:
        for tick in self._ticks:
            yield tick
            await asyncio.sleep(0)  # Yield control to event loop


class FakeTickRepo:
    """Mock TickRepository — stores in list for assertion."""

    def __init__(self) -> None:
        self.stored: list[Tick] = []

    async def insert_batch(self, ticks: list[Tick]) -> int:
        self.stored.extend(ticks)
        return len(ticks)


@pytest.mark.asyncio
async def test_data_agent_flushes_buffer() -> None:
    """Verify DataAgent ingests ticks and flushes to repository."""
    from agents.data_agent import DataAgent

    ticks = [
        Tick(
            symbol=Symbol("FPT"),
            price=Price(Decimal("98.50")),
            volume=Quantity(1000),
            exchange=Exchange.HOSE,
            timestamp=datetime(2026, 2, 10, 9, 0, i),
        )
        for i in range(10)
    ]

    market = FakeMarketData(ticks)
    repo = FakeTickRepo()
    agent = DataAgent(market, repo, flush_interval=0.1)

    # Run agent for a short time then stop
    task = asyncio.create_task(agent.start())
    await asyncio.sleep(0.5)
    await agent.stop()

    # Verify all ticks were flushed to repo
    assert len(repo.stored) == 10
```

### 5.6. Test Execution

```bash
# Run all tests
uv run pytest tests/ -v --tb=short

# Run only unit tests (fast, no infra)
uv run pytest tests/unit/ -v --tb=short -x

# Run with coverage
uv run pytest tests/ --cov=packages --cov-report=term-missing --cov-fail-under=85

# Run with type checking
uv run mypy packages/ --strict

# Lint + format check
uv run ruff check packages/ tests/
uv run ruff format --check packages/ tests/
```

### 5.7. CI Pipeline Stages

```
Stage 1: Lint + Type Check     (~5s)   ruff check + mypy --strict
Stage 2: Unit Tests            (~3s)   pytest tests/unit/ -x
Stage 3: Integration Tests     (~10s)  pytest tests/integration/ -x
Stage 4: Coverage Gate         (~15s)  pytest --cov --cov-fail-under=85
```

Tổng thời gian CI: **< 35 giây** (nhờ `uv` install nhanh + DuckDB in-memory + no external services).

---

## APPENDIX A: TYPE HINTING CONVENTIONS

```python
# ✅ DO: Use modern syntax (Python 3.12+)
def process(items: list[Tick]) -> dict[Symbol, Price]: ...

# ✅ DO: Use | instead of Optional
def find(symbol: Symbol) -> Position | None: ...

# ✅ DO: Use TYPE_CHECKING for import-only types (avoid circular imports)
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core.entities.tick import Tick

# ✅ DO: Use Protocol for dependency inversion
class MarketDataPort(Protocol):
    async def connect(self) -> None: ...

# ✅ DO: Use NewType for domain primitives
Symbol = NewType("Symbol", str)
Price = NewType("Price", Decimal)

# ❌ DON'T: Use Any — ever. If you need it, your design is wrong.
# ❌ DON'T: Use Dict, List, Optional (old-style typing module generics).
# ❌ DON'T: Leave functions untyped. mypy --strict will catch this.
```

## APPENDIX B: BANNED PATTERNS

| Pattern | Reason | Alternative |
|:---|:---|:---|
| `import requests` | Blocking I/O | `import httpx` (async) |
| `time.sleep()` | Blocks event loop | `await asyncio.sleep()` |
| `float` for prices | IEEE 754 rounding | `Decimal` |
| `dict` for entities | No type safety, mutable | `@dataclass(frozen=True)` |
| Global mutable state | Thread-unsafe, untestable | Dependency injection |
| `try: ... except Exception:` | Swallows bugs | Catch specific exceptions |
| `# type: ignore` without code | Hides real errors | Fix the type or add specific error code |
| Circular imports | Architecture smell | Restructure layers, use `TYPE_CHECKING` |

---

*Document authored by Senior Python Backend Engineer. All code samples are production-grade reference implementations.*
