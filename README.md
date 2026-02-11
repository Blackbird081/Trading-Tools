# Enterprise Algo-Trading Platform on Hybrid AI

**Phase 1 — Foundation & Core Domain** ✅ **COMPLETED**

## Tổng quan

Hệ thống giao dịch thuật toán doanh nghiệp với AI lai (Hybrid AI) kết hợp:
- **Backend**: Python 3.12+ monorepo với Clean Architecture
- **Database**: DuckDB (in-process OLAP) với Parquet partitioning
- **AI/ML**: LangGraph multi-agent + OpenVINO NPU (Intel Core Ultra)
- **Frontend**: Next.js 15 + React 19 (Phase 4)

## Cấu trúc dự án

```
algo-trading/
├── packages/
│   ├── core/          # Domain layer — entities, ports, use cases (ZERO deps)
│   ├── adapters/      # Infrastructure — DuckDB, SSI, Vnstock, OpenVINO
│   ├── agents/        # LangGraph multi-agent orchestration
│   └── interface/     # FastAPI + WebSocket API
├── tests/
│   ├── unit/          # Pure logic tests (96 tests)
│   └── integration/   # DuckDB integration tests (10 tests)
├── data/              # Runtime data (gitignored)
├── scripts/           # CI/CD scripts
└── .github/           # GitHub Actions CI
```

## Cài đặt nhanh (< 2 phút)

### Yêu cầu hệ thống
- **Python**: 3.12+
- **uv**: Package manager (nhanh hơn pip 10-100x)
- **OS**: Windows 10/11, macOS, Linux

### Bước 1: Clone và cài đặt

```powershell
# Clone repository
cd Z:\CODE\AI_Stock_Cursor\algo-trading

# Cài đặt dependencies (< 30s)
uv sync

# Verify installation
uv run python -c "import core; import adapters; print('OK')"
```

### Bước 2: Chạy tests

```powershell
# Chạy tất cả tests
uv run pytest tests/ -v

# Chạy với coverage
uv run pytest tests/ --cov=packages --cov-report=term-missing

# Chỉ chạy unit tests (nhanh)
uv run pytest tests/unit/ -v
```

### Bước 3: Quality checks

```powershell
# Lint
uv run ruff check packages/ tests/

# Type check
uv run mypy packages/ --strict

# Format
uv run ruff format packages/ tests/

# Chạy toàn bộ CI pipeline
.\scripts\ci.ps1
```

## Phase 1 — Kết quả đạt được ✅

### ✅ Definition of Done — Đã hoàn thành

- [x] `uv sync` installs all 4 packages with correct dependency graph
- [x] `uv run mypy packages/ --strict` passes with zero errors
- [x] `uv run ruff check packages/ tests/` passes with zero warnings
- [x] `uv run pytest tests/unit/ -v` runs **96 tests**, all pass
- [x] `uv run pytest tests/integration/ -v` runs **10 DuckDB tests**, all pass
- [x] Order FSM rejects all invalid transitions (tested)
- [x] Price band validates ceiling/floor for HOSE/HNX/UPCOM (tested)
- [x] T+2.5 settlement logic handles holidays + weekends (tested)
- [x] ASOF JOIN query returns correct nearest tick (tested)
- [x] Parquet write + read round-trip preserves data (tested)
- [x] .gitignore blocks .env, *.pem, data/ from being committed
- [x] Dependency direction enforced: core has ZERO external imports

### 📊 Metrics

| Metric | Target | Achieved |
|:---|:---:|:---:|
| **Tests** | ≥ 30 | **106 tests** ✅ |
| **Coverage** | ≥ 90% core, ≥ 80% adapters | **96% overall** ✅ |
| **Linter** | Zero warnings | **All checks passed** ✅ |
| **Type Safety** | mypy --strict | **No issues found** ✅ |
| **CI Time** | < 60s | **~15s** (uv is fast!) ✅ |

### 🏗️ Architecture hoàn thành

**Clean Architecture — 4 layers:**

```
Interface (FastAPI)  ──► Agents (LangGraph)  ──► Adapters (DuckDB, SSI)  ──► Core (Entities, Ports, Use Cases)
     ▲                       ▲                        ▲                           │
     │                       │                        │                           │
     └───────────────────────┴────────────────────────┴───────────────────────────┘
                      Dependency Inversion: Core defines interfaces,
                      outer layers implement them
```

**Domain Entities (Immutable, Type-Safe):**
- ✅ `Tick`, `OHLCV` — Market data
- ✅ `Order` — State machine with FSM validation
- ✅ `Position`, `CashBalance`, `PortfolioState` — T+2.5 aware
- ✅ `TradingSignal`, `AIInsight` — Agent outputs
- ✅ `RiskLimit`, `RiskMetrics`, `VaRResult` — Risk management

**Core Use Cases (Pure Functions):**
- ✅ `validate_order()` — 7-check risk validation
- ✅ `calculate_price_band()` — Ceiling/floor/tick size (HOSE/HNX/UPCOM)
- ✅ `calculate_settlement_date()`, `can_sell_now()` — T+2.5 logic
- ✅ `compute_technical_score()` — TA scoring (stub for Phase 3)
- ✅ `run_screening()` — Watchlist filtering
- ✅ `compute_rebalance()` — Portfolio rebalance (stub for Phase 3)
- ✅ `format_insight()` — AI insight formatting

**DuckDB Adapters:**
- ✅ `TickRepository` — Batch insert, OHLCV aggregation, ASOF JOIN
- ✅ `OrderRepository` — Order CRUD với idempotency
- ✅ `ParquetPartitionManager` — Hive-style partitioning (year/month/day)
- ✅ SQL queries — ASOF JOIN PnL, screening indicators, Historical VaR

**Ports (Protocol-based):**
- ✅ `MarketDataPort`, `BrokerPort`, `TickRepository`, `OrderRepository`, `AIEnginePort`, `NotifierPort`

## Tiếp theo: Phase 2

**Phase 2 — Market Connectivity & Data Pipeline** (Weeks 3-5)

Sẽ triển khai:
- SSI RSA authentication (3-tier credential storage)
- Resilient WebSocket client (infinite reconnect + circuit breaker)
- Data Agent ingestion loop (buffer + batch flush)
- FastAPI shell + WebSocket server
- Vnstock historical data adapter

## Tài liệu tham khảo

- [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) — Master implementation plan
- [02_Backend_Engineering.md](../02_Backend_Engineering.md) — Backend architecture
- [05_Integration_Security.md](../05_Integration_Security.md) — Security & OMS
- [06_Development_Standards_Rules.md](../06_Development_Standards_Rules.md) — Coding standards

## License

Proprietary — Enterprise Internal Use Only

---

**Phase 1 Status**: ✅ **COMPLETED** — All tests passing, 96% coverage, zero linter/type errors.
**Ready for Phase 2**: ✅ Rock-solid foundation with Clean Architecture.
