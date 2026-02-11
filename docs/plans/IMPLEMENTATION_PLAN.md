# MASTER IMPLEMENTATION PLAN

**Project:** Enterprise Algo-Trading Platform on Hybrid AI
**Author:** Lead Solutions Architect & Senior Technical Project Manager
**Version:** 1.0 | February 2026
**Timeline:** 12 Weeks (Aligned with bc1.md roadmap)
**Governing Standard:** `06_Development_Standards_Rules.md` — ALL code MUST comply.

---

> **How to use this document:** This is the single source of truth for *what to build, in what order, and how to verify it*. Each Phase produces a working, testable increment. No Phase depends on future work — the system is usable (in limited form) after each Phase completes.

---

## EXECUTIVE SUMMARY

```
Phase 1 ██████░░░░░░░░░░░░░░  Weeks 1-3    Foundation & Core Domain
Phase 2 ░░░░░░██████░░░░░░░░  Weeks 3-5    Market Connectivity & Data Pipeline
Phase 3 ░░░░░░░░░░░░██████░░  Weeks 5-8    Intelligence Engine (Agents + Quant)
Phase 4 ░░░░░░░░░░░░░░████░░  Weeks 7-10   Frontend & Real-time UI
Phase 5 ░░░░░░░░░░░░░░░░████  Weeks 10-12  AI Edge Inference & Order Execution

★ Phases 3 & 4 overlap intentionally — backend agents and frontend
  can be developed in parallel once the WebSocket contract is defined.
```

### Dependency Chain

```
Phase 1 ──► Phase 2 ──► Phase 3 ──┐
                                    ├──► Phase 5
                         Phase 4 ──┘
                         (parallel with Phase 3)
```

**Tài liệu người dùng:** Sổ tay hướng dẫn từ cơ bản đến nâng cao và chạy chương trình: [`docs/USER_MANUAL.md`](../USER_MANUAL.md).

---

## PHASE 1: FOUNDATION & CORE DOMAIN

**Duration:** Weeks 1-3
**Principle:** "Get the skeleton right. Everything plugs into this structure forever."
**Blueprint References:** Doc 02 (Sections 1-2), Doc 06 (Sections 1, 3, 9, 10)

### 1.1. Objective

Build the monorepo skeleton, domain entities, abstract Ports, DuckDB schema, full CI pipeline, and tooling configuration. At the end of Phase 1, the project has **zero features** but a rock-solid foundation: every file has a home, every type is defined, every quality gate is enforced.

### 1.2. Tasks

#### Task 1.1 — Monorepo Initialization

| Attribute | Detail |
|:---|:---|
| **What** | Initialize `uv` workspace with 4 packages: `core`, `adapters`, `agents`, `interface` |
| **Where** | Root `pyproject.toml`, `packages/*/pyproject.toml` |
| **Tech** | `uv` (Astral), Python 3.12+, `hatchling` build backend |
| **Test** | `uv sync` completes without errors; `uv run python -c "import core"` works |

```bash
# Commands to execute (in order)
uv init algo-trading
cd algo-trading
mkdir -p packages/{core,adapters,agents,interface}/src/{core,adapters,agents,interface}
# Create pyproject.toml for each package (see Doc 02, Section 1.2-1.4)
# Create __init__.py for each package
uv sync
```

**Files to create:**
```
pyproject.toml                          # Workspace root (Doc 02 §1.2)
packages/core/pyproject.toml            # Zero deps (Doc 02 §1.3)
packages/adapters/pyproject.toml        # Depends on: core (Doc 02 §1.4)
packages/agents/pyproject.toml          # Depends on: core, adapters
packages/interface/pyproject.toml       # Depends on: core, adapters, agents
.python-version                         # Pin: 3.12.x
```

#### Task 1.2 — Tooling Configuration

| Attribute | Detail |
|:---|:---|
| **What** | Configure Ruff, mypy, pytest, git hooks, .gitignore |
| **Where** | Root: `ruff.toml`, `mypy.ini`, `pytest.ini`, `.gitignore`, `.env.example` |
| **Tech** | Ruff, mypy, pytest, pytest-asyncio, pytest-cov |
| **Test** | `uv run ruff check .` passes; `uv run mypy packages/ --strict` passes (on empty packages) |

**Files to create:**
```
ruff.toml                               # Doc 06 §1.7 (exact config)
mypy.ini                                # Doc 06 §1.8 (exact config)
.gitignore                              # Doc 05 §1.7 (security-critical entries)
.env.example                            # Doc 05 §1.7 (template, no real values)
tests/conftest.py                       # Doc 02 §5.2 (DuckDB in-memory fixture)
tests/__init__.py
tests/unit/__init__.py
tests/integration/__init__.py
```

#### Task 1.3 — Core Domain Entities

| Attribute | Detail |
|:---|:---|
| **What** | Define all frozen dataclasses: `Tick`, `Order`, `Position`, `PortfolioState`, `RiskLimit`, `TradingSignal`. Define value objects: `Symbol`, `Price`, `Quantity`. Define enums: `Exchange`, `OrderSide`, `OrderStatus`, `OrderType`. |
| **Where** | `packages/core/src/core/entities/`, `packages/core/src/core/value_objects.py` |
| **Tech** | Pure Python 3.12: `dataclasses`, `decimal.Decimal`, `typing.NewType`, `enum.StrEnum` |
| **Test** | `tests/unit/test_entities.py` — immutability, equality, `is_ceiling()`, `is_floor()`, `NewType` enforcement |

**Files to create:**
```
packages/core/src/core/__init__.py
packages/core/src/core/value_objects.py         # Symbol, Price, Quantity (Doc 02 §2.2)
packages/core/src/core/entities/__init__.py
packages/core/src/core/entities/tick.py          # Tick, Exchange (Doc 02 §2.2)
packages/core/src/core/entities/order.py         # Order, OrderStatus FSM (Doc 05 §2.2)
packages/core/src/core/entities/portfolio.py     # Position, CashBalance, PortfolioState (Doc 05 §3.3)
packages/core/src/core/entities/signal.py        # TradingSignal, SignalStrength, AIInsight
packages/core/src/core/entities/risk.py          # RiskMetrics, RiskLimit, VaRResult
tests/unit/test_entities.py                      # Immutability, FSM transitions (Doc 05 §5.2)
```

#### Task 1.4 — Ports (Abstract Interfaces)

| Attribute | Detail |
|:---|:---|
| **What** | Define `Protocol` interfaces for all external dependencies: `MarketDataPort`, `BrokerPort`, `TickRepository`, `OrderRepository`, `AIEnginePort`, `NotifierPort` |
| **Where** | `packages/core/src/core/ports/` |
| **Tech** | `typing.Protocol` (structural subtyping, NOT ABC) |
| **Test** | `mypy --strict` passes — Protocol methods have correct signatures |

**Files to create:**
```
packages/core/src/core/ports/__init__.py
packages/core/src/core/ports/market_data.py      # MarketDataPort (Doc 02 §2.3)
packages/core/src/core/ports/broker.py            # BrokerPort
packages/core/src/core/ports/repository.py        # TickRepository, OrderRepository (Doc 02 §2.3)
packages/core/src/core/ports/ai_engine.py         # AIEnginePort
packages/core/src/core/ports/notifier.py          # NotifierPort
```

#### Task 1.5 — Core Use Cases (Pure Business Logic)

| Attribute | Detail |
|:---|:---|
| **What** | Implement pure functions: `validate_order()`, `validate_lot_size()`, `calculate_price_band()`, `calculate_settlement_date()`, `can_sell_now()` |
| **Where** | `packages/core/src/core/use_cases/` |
| **Tech** | Pure Python — zero external imports, zero I/O |
| **Test** | `tests/unit/test_use_cases.py`, `test_risk_check.py`, `test_price_band.py`, `test_settlement.py` — exhaustive edge cases, NO mocks needed |

**Files to create:**
```
packages/core/src/core/use_cases/__init__.py
packages/core/src/core/use_cases/risk_check.py   # validate_order() with 7 checks (Doc 05 §3.6)
packages/core/src/core/use_cases/price_band.py   # ceiling/floor/tick_size (Doc 05 §3.5)
packages/core/src/core/use_cases/settlement.py   # T+2.5 logic (Doc 05 §3.4)
packages/core/src/core/use_cases/scoring.py      # technical_score() stub (Doc 04 §1.6)
packages/core/src/core/use_cases/screening.py    # Screener filter logic
packages/core/src/core/use_cases/rebalance.py    # Portfolio rebalance stub
packages/core/src/core/use_cases/insight.py      # AI insight formatting
tests/unit/test_risk_check.py                     # Doc 02 §5.3 + Doc 05 §5.2
tests/unit/test_price_band.py                     # Doc 05 §5.3
tests/unit/test_settlement.py                     # T+2.5 edge cases (holidays, weekends)
tests/unit/test_scoring.py                        # Scoring logic
```

#### Task 1.6 — DuckDB Schema & Adapter

| Attribute | Detail |
|:---|:---|
| **What** | Create DuckDB connection factory, tick/order tables, ASOF JOIN query, Parquet partitioning |
| **Where** | `packages/adapters/src/adapters/duckdb/` |
| **Tech** | `duckdb>=1.1`, `pyarrow>=17.0` |
| **Test** | `tests/integration/test_duckdb_repo.py` — insert batch, ASOF JOIN, Parquet round-trip (Doc 02 §5.4) |

**Files to create:**
```
packages/adapters/src/adapters/__init__.py
packages/adapters/src/adapters/duckdb/__init__.py
packages/adapters/src/adapters/duckdb/connection.py    # Factory, lifecycle (Doc 02 §2.5)
packages/adapters/src/adapters/duckdb/tick_repo.py     # Implements TickRepository
packages/adapters/src/adapters/duckdb/order_repo.py    # Implements OrderRepository
packages/adapters/src/adapters/duckdb/partitioning.py  # Parquet partition manager (Doc 02 §3.2)
packages/adapters/src/adapters/duckdb/queries/
    asof_join_pnl.sql                                   # Doc 02 §3.1
    screening_indicators.sql
    var_historical.sql
tests/integration/test_duckdb_repo.py                   # Doc 02 §5.4
```

#### Task 1.7 — CI Pipeline Setup

| Attribute | Detail |
|:---|:---|
| **What** | Local CI script (or GitHub Actions YAML) that runs all 6 stages from Doc 06 §10 |
| **Where** | `.github/workflows/ci.yml` or `scripts/ci.sh` |
| **Tech** | uv, ruff, mypy, pytest, pytest-cov |
| **Test** | Running `./scripts/ci.sh` passes with zero errors on clean foundation |

### 1.3. Definition of Done — Phase 1

```
□ `uv sync` installs all 4 packages with correct dependency graph
□ `uv run mypy packages/ --strict` passes with zero errors
□ `uv run ruff check packages/ tests/` passes with zero warnings
□ `uv run pytest tests/unit/ -v` runs ≥ 30 tests, all pass
□ `uv run pytest tests/integration/ -v` runs ≥ 5 DuckDB tests, all pass
□ Order FSM rejects all invalid transitions (tested)
□ Price band validates ceiling/floor for HOSE/HNX/UPCOM (tested)
□ T+2.5 settlement logic handles holidays + weekends (tested)
□ ASOF JOIN query returns correct nearest tick (tested)
□ Parquet write + read round-trip preserves data (tested)
□ .gitignore blocks .env, *.pem, data/ from being committed
□ Dependency direction enforced: core has ZERO external imports
```

---

## PHASE 2: MARKET CONNECTIVITY & DATA PIPELINE

**Duration:** Weeks 3-5
**Principle:** "Connect to real money. Every network call assumes failure."
**Blueprint References:** Doc 05 (Sections 1-2, 4), Doc 02 (Sections 3-4)

### 2.1. Objective

Connect to SSI FastConnect and Vnstock. Implement RSA authentication, WebSocket market data streaming, tick ingestion into DuckDB, and portfolio synchronization. At the end of Phase 2, the system **receives real-time market data** and stores it locally.

### 2.2. Tasks

#### Task 2.1 — SSI RSA Authentication

| Attribute | Detail |
|:---|:---|
| **What** | `CredentialManager` (3-tier key storage), `SSIAuthClient` (RSA-SHA256 signing, JWT management) |
| **Where** | `packages/adapters/src/adapters/ssi/` |
| **Tech** | `pycryptodome>=3.20`, `httpx>=0.27` |
| **Test** | `tests/integration/test_ssi_auth.py` — sign/verify round-trip, token refresh, invalid key rejection |

**Files to create:**
```
packages/adapters/src/adapters/ssi/__init__.py
packages/adapters/src/adapters/ssi/credential_manager.py  # Doc 05 §1.4 (3-tier storage)
packages/adapters/src/adapters/ssi/auth.py                 # Doc 05 §1.5 (RSA signing + JWT)
packages/adapters/src/adapters/ssi/models.py               # SSI-specific Pydantic models
tests/integration/test_ssi_auth.py
```

#### Task 2.2 — Retry & Circuit Breaker Infrastructure

| Attribute | Detail |
|:---|:---|
| **What** | Generic `retry_async()`, `RetryConfig`, `CircuitBreaker` — shared by ALL adapters |
| **Where** | `packages/adapters/src/adapters/retry.py`, `packages/adapters/src/adapters/circuit_breaker.py` |
| **Tech** | Pure Python asyncio |
| **Test** | `tests/unit/test_retry.py` — backoff timing, max retries, jitter; `test_circuit_breaker.py` — state transitions CLOSED→OPEN→HALF_OPEN |

**Files to create:**
```
packages/adapters/src/adapters/retry.py             # Doc 05 §4.2
packages/adapters/src/adapters/circuit_breaker.py   # Doc 05 §4.6
tests/unit/test_retry.py
tests/unit/test_circuit_breaker.py
```

#### Task 2.3 — SSI WebSocket Market Data Client

| Attribute | Detail |
|:---|:---|
| **What** | `SSIMarketWebSocket` — resilient WebSocket client with infinite reconnect, exponential backoff, health check |
| **Where** | `packages/adapters/src/adapters/ssi/market_ws.py` |
| **Tech** | `websockets>=13.0`, implements `MarketDataPort` |
| **Test** | `tests/integration/test_data_pipeline.py` — `FakeMarketData` yields ticks, `DataAgent` flushes to repo (Doc 02 §5.5) |

**Files to create:**
```
packages/adapters/src/adapters/ssi/market_ws.py     # Doc 05 §4.3 (resilient WS)
packages/adapters/src/adapters/ssi/broker.py        # BrokerPort implementation (stub for Phase 5)
packages/adapters/src/adapters/ssi/portfolio.py     # stockPosition sync + T+2.5 (Doc 05 §3.2)
```

#### Task 2.4 — Vnstock Data Adapter

| Attribute | Detail |
|:---|:---|
| **What** | Vnstock wrappers for historical OHLCV, stock screening, news feed |
| **Where** | `packages/adapters/src/adapters/vnstock/` |
| **Tech** | `vnstock>=3.1` |
| **Test** | Integration test with mock HTTP responses (no live API in CI) |

**Files to create:**
```
packages/adapters/src/adapters/vnstock/__init__.py
packages/adapters/src/adapters/vnstock/history.py    # Historical OHLCV
packages/adapters/src/adapters/vnstock/screener.py   # stock_screening() wrapper
packages/adapters/src/adapters/vnstock/news.py       # News feed for Fundamental Agent
```

#### Task 2.5 — DNSE Auth Adapter

| Attribute | Detail |
|:---|:---|
| **What** | DNSE JWT + Refresh Token management |
| **Where** | `packages/adapters/src/adapters/dnse/` |
| **Tech** | `httpx` |
| **Test** | Token refresh logic, expiry edge cases |

**Files to create:**
```
packages/adapters/src/adapters/dnse/__init__.py
packages/adapters/src/adapters/dnse/auth.py          # Doc 05 §4.5
packages/adapters/src/adapters/dnse/broker.py        # BrokerPort implementation (stub)
```

#### Task 2.6 — Data Agent (Ingestion Loop)

| Attribute | Detail |
|:---|:---|
| **What** | `DataAgent` — async ingestion loop + periodic flush to DuckDB + Parquet export |
| **Where** | `packages/agents/src/agents/data_agent.py` |
| **Tech** | `asyncio.TaskGroup`, `deque` buffer, `asyncio.to_thread` for DuckDB writes |
| **Test** | `tests/integration/test_data_pipeline.py` with `FakeMarketData` + `FakeTickRepo` (Doc 02 §5.5) |

**Files to create:**
```
packages/agents/src/agents/__init__.py
packages/agents/src/agents/data_agent.py             # Doc 02 §4.3
tests/integration/test_data_pipeline.py              # Doc 02 §5.5
```

#### Task 2.7 — FastAPI Application Shell & WebSocket Server

| Attribute | Detail |
|:---|:---|
| **What** | FastAPI app factory, DI wiring (`dependencies.py`), health endpoint, outbound WebSocket endpoint `/ws/market` |
| **Where** | `packages/interface/src/interface/` |
| **Tech** | `fastapi>=0.115`, `uvicorn` |
| **Test** | `GET /api/health` returns 200; WebSocket connects and receives a test message |

**Files to create:**
```
packages/interface/src/interface/__init__.py
packages/interface/src/interface/app.py              # FastAPI factory (Doc 02 §2.6)
packages/interface/src/interface/dependencies.py     # DI wiring (Doc 02 §2.6)
packages/interface/src/interface/cli.py              # uvicorn launcher
packages/interface/src/interface/rest/__init__.py
packages/interface/src/interface/rest/health.py      # GET /api/health
packages/interface/src/interface/rest/portfolio.py   # GET /api/portfolio (stub)
packages/interface/src/interface/ws/__init__.py
packages/interface/src/interface/ws/manager.py       # ConnectionManager (broadcast)
packages/interface/src/interface/ws/market_ws.py     # /ws/market endpoint
```

### 2.3. Definition of Done — Phase 2

```
□ SSI RSA auth: sign → verify → receive JWT token (tested with mock server)
□ Credential Manager loads key from all 3 tiers (tested)
□ WebSocket client connects, receives mock ticks, auto-reconnects on disconnect
□ Exponential backoff: delays follow 1s, 2s, 4s, 8s... 60s cap (tested)
□ Circuit breaker: CLOSED→OPEN after 5 failures, OPEN→HALF_OPEN after timeout (tested)
□ Data Agent ingests 1,000 mock ticks → flushes to DuckDB → count matches (tested)
□ Parquet export: ticks survive DuckDB → Parquet → DuckDB round-trip
□ Vnstock historical data loads into DuckDB (integration test with fixture data)
□ FastAPI /api/health returns 200
□ WebSocket /ws/market broadcasts tick data to connected client
□ All Phase 1 tests still pass (no regressions)
```

---

## PHASE 3: INTELLIGENCE ENGINE — AGENTS & QUANT

**Duration:** Weeks 5-8
**Principle:** "The brain comes online. Every decision is deterministic, testable, auditable."
**Blueprint References:** Doc 04 (Sections 1-3), Doc 02 (Section 4)

### 3.1. Objective

Implement the Multi-Agent pipeline: `Screener → Technical → Risk → Executor`. Wire them into a LangGraph `StateGraph` with deterministic routing. The `Fundamental Agent` (NPU) is deferred to Phase 5 — the pipeline works without it. At the end of Phase 3, the system **generates trading signals** from market data.

### 3.2. Tasks

#### Task 3.1 — Agent State Schema

| Attribute | Detail |
|:---|:---|
| **What** | `AgentState` TypedDict, `AgentPhase` enum, all dataclasses: `ScreenerResult`, `TechnicalScore`, `RiskAssessment`, `ExecutionPlan` |
| **Where** | `packages/agents/src/agents/state.py` |
| **Tech** | `typing.TypedDict`, `dataclasses`, `enum.StrEnum` |
| **Test** | Type check passes; state schema is correctly structured |

**Files to create:**
```
packages/agents/src/agents/state.py                  # Doc 04 §1.2
```

#### Task 3.2 — Screener Agent

| Attribute | Detail |
|:---|:---|
| **What** | `ScreenerAgent.run()` — SQL vectorized screening + vnstock fundamental filter + volume spike detection |
| **Where** | `packages/agents/src/agents/screener_agent.py` |
| **Tech** | DuckDB SQL, vnstock, asyncio |
| **Test** | Mock tick repo returns pre-defined data → agent produces expected watchlist |

**Files to create:**
```
packages/agents/src/agents/screener_agent.py         # Doc 04 §1.5
tests/unit/test_screener_agent.py
```

#### Task 3.3 — Technical Analysis Agent

| Attribute | Detail |
|:---|:---|
| **What** | `TechnicalAgent.run()` — pandas-ta scoring (RSI, MACD, BB, MA50/200), PyPortfolioOpt rebalancing |
| **Where** | `packages/agents/src/agents/technical_agent.py` |
| **Tech** | `pandas-ta`, `PyPortfolioOpt`, `ProcessPoolExecutor` for CPU-bound work |
| **Test** | Feed known OHLCV data → verify scores match expected thresholds |

**Files to create:**
```
packages/agents/src/agents/technical_agent.py        # Doc 04 §1.6
tests/unit/test_technical_agent.py
tests/fixtures/sample_ohlcv.json                     # Known OHLCV for deterministic testing
```

#### Task 3.4 — Risk Agent

| Attribute | Detail |
|:---|:---|
| **What** | `RiskAgent.run()` — VaR, position sizing, kill switch, delegates to `validate_order()` from core |
| **Where** | `packages/agents/src/agents/risk_agent.py` |
| **Tech** | DuckDB for VaR, core use cases for validation |
| **Test** | Kill switch active → all rejected; exceed NAV → rejected; valid signal → approved |

**Files to create:**
```
packages/agents/src/agents/risk_agent.py             # Doc 04 §1.7
tests/unit/test_risk_agent.py
```

#### Task 3.5 — Executor Agent (Stub)

| Attribute | Detail |
|:---|:---|
| **What** | `ExecutorAgent.run()` — stub that creates `ExecutionPlan` with `dry_run=True`. Real broker integration in Phase 5. |
| **Where** | `packages/agents/src/agents/executor_agent.py` |
| **Tech** | core entities |
| **Test** | Dry run mode → plan created but `executed=False`, `order_id=None` |

**Files to create:**
```
packages/agents/src/agents/executor_agent.py
tests/unit/test_executor_agent.py
```

#### Task 3.6 — LangGraph Supervisor (Graph Definition)

| Attribute | Detail |
|:---|:---|
| **What** | `build_trading_graph()` — wires all agents into `StateGraph` with conditional edges. `run_trading_pipeline()` and `run_with_streaming()` execution wrappers. |
| **Where** | `packages/agents/src/agents/supervisor.py`, `packages/agents/src/agents/runner.py` |
| **Tech** | `langgraph>=0.2` |
| **Test** | `tests/unit/test_supervisor_routing.py` — all routing functions tested (Doc 04 §5.2). E2E: run full pipeline with mock data → verify state transitions. |

**Files to create:**
```
packages/agents/src/agents/supervisor.py             # Doc 04 §1.4
packages/agents/src/agents/runner.py                 # Doc 04 §1.8
tests/unit/test_supervisor_routing.py                # Doc 04 §5.2
tests/integration/test_pipeline_e2e.py               # Full graph with mocked adapters
```

#### Task 3.7 — Prompt Engineering System

| Attribute | Detail |
|:---|:---|
| **What** | `PromptRegistry`, `FinancialPromptBuilder`, `manifest.json`, versioned prompt templates |
| **Where** | `packages/agents/src/agents/prompt_builder.py`, `data/prompts/` |
| **Tech** | Pure Python, JSON manifest, Markdown templates |
| **Test** | `tests/unit/test_prompt_builder.py` — prompt assembly, version selection, variable injection (Doc 04 §5.3) |

**Files to create:**
```
packages/agents/src/agents/prompt_builder.py         # Doc 04 §3.5
data/prompts/manifest.json                            # Doc 04 §3.3
data/prompts/financial_analysis/v1.0.0.md             # Doc 04 §3.4
tests/unit/test_prompt_builder.py                     # Doc 04 §5.3
```

#### Task 3.8 — Pipeline Observability (Structured Logging)

| Attribute | Detail |
|:---|:---|
| **What** | `log_agent_step()` — structured JSON logging for every agent execution |
| **Where** | `packages/agents/src/agents/observability.py` |
| **Tech** | Python `logging`, JSON structured output |
| **Test** | Capture log output, verify JSON structure and required fields |

**Files to create:**
```
packages/agents/src/agents/observability.py          # Doc 04 §5.4
```

### 3.3. Definition of Done — Phase 3

```
□ Screener Agent filters mock market → returns ≤ 10 candidates (tested)
□ Technical Agent scores candidates → composite_score is deterministic (tested)
□ Risk Agent blocks orders that exceed NAV limit / price band / lot size (tested)
□ Kill switch halts ALL signals immediately (tested)
□ Executor Agent in dry_run mode creates plan but does NOT call broker (tested)
□ LangGraph routing: empty watchlist → END; no signals → END; none approved → END (tested)
□ Full pipeline: inject mock data → Screener → Technical → Risk → Executor → final state (tested)
□ Prompt builder assembles correct prompt with indicators + news (tested)
□ Structured logs emitted for each agent step with run_id traceability
□ All Phase 1+2 tests still pass (no regressions)
□ Coverage ≥ 85% on packages/core, ≥ 80% on packages/agents
```

---

## PHASE 4: FRONTEND & REAL-TIME UI

**Duration:** Weeks 7-10 (overlaps with Phase 3)
**Principle:** "The terminal comes alive. 60fps, zero jank, real-time data from tick one."
**Blueprint References:** Doc 03 (Full document)

### 4.1. Objective

Build the Next.js trading terminal with AG Grid (price board), TradingView charts, portfolio dashboard, Zustand state management, and WebSocket data bridge. At the end of Phase 4, the UI **displays real-time market data and agent signals**.

### 4.2. Tasks

#### Task 4.1 — Next.js Project Initialization

| Attribute | Detail |
|:---|:---|
| **What** | Next.js 15 App Router project with TypeScript strict, Tailwind CSS 4, Shadcn UI, Dark Mode default |
| **Where** | `frontend/` |
| **Tech** | Next.js 15, React 19, TypeScript 5.6+, Tailwind CSS 4, Shadcn UI |
| **Test** | `pnpm build` succeeds; `pnpm tsc --noEmit` passes |

```bash
cd frontend
pnpm create next-app . --typescript --tailwind --eslint --app --src-dir=false
pnpm add zustand ag-grid-react ag-grid-community lightweight-charts
pnpm add -D vitest @testing-library/react @vitejs/plugin-react
```

**Files to create:**
```
frontend/app/layout.tsx                  # Root layout, Dark Mode, WebSocketProvider (Doc 03 §1.3)
frontend/app/(dashboard)/layout.tsx      # Dashboard sub-layout
frontend/app/(dashboard)/page.tsx        # Main view: Chart + PriceBoard (Doc 03 §1.4)
frontend/app/portfolio/page.tsx
frontend/app/screener/page.tsx
frontend/app/orders/page.tsx
frontend/app/settings/page.tsx
frontend/tsconfig.json                   # Strict settings (Doc 06 §2.2)
```

#### Task 4.2 — Zustand Store Architecture

| Attribute | Detail |
|:---|:---|
| **What** | 5 domain-separated stores: `market-store`, `portfolio-store`, `signal-store`, `order-store`, `ui-store` |
| **Where** | `frontend/stores/` |
| **Tech** | Zustand with `subscribeWithSelector` middleware |
| **Test** | `__tests__/stores/market-store.test.ts` — update, bulk update, immutability (Doc 03 §5.3) |

**Files to create:**
```
frontend/stores/market-store.ts          # Doc 03 §4.2
frontend/stores/portfolio-store.ts
frontend/stores/signal-store.ts
frontend/stores/order-store.ts
frontend/stores/ui-store.ts
frontend/__tests__/stores/market-store.test.ts  # Doc 03 §5.3
```

#### Task 4.3 — WebSocket Provider & Message Router

| Attribute | Detail |
|:---|:---|
| **What** | `WebSocketProvider` — connects to backend, routes messages to correct Zustand store by `msg.type` |
| **Where** | `frontend/providers/ws-provider.tsx` |
| **Tech** | Native `WebSocket`, Zustand `getState()` (NOT `setState` in provider) |
| **Test** | Integration test: simulate WS messages → verify store updates |

**Files to create:**
```
frontend/providers/ws-provider.tsx       # Doc 03 §4.5
frontend/__tests__/integration/ws-provider.test.tsx
```

#### Task 4.4 — AG Grid Price Board

| Attribute | Detail |
|:---|:---|
| **What** | `PriceBoard` component with DOM virtualization, cell-level transaction updates via `requestAnimationFrame` batching |
| **Where** | `frontend/app/(dashboard)/_components/price-board.tsx` |
| **Tech** | AG Grid Enterprise, `applyTransactionAsync`, `requestAnimationFrame` |
| **Test** | Mock store data → verify grid renders rows correctly; check `getRowId` returns stable key |

**Files to create:**
```
frontend/app/(dashboard)/_components/price-board.tsx  # Doc 03 §2.2
frontend/hooks/use-market-stream.ts                    # Doc 03 §2.3 (rAF batching)
frontend/__tests__/components/price-cell.test.tsx      # Doc 03 §5.4
frontend/__tests__/integration/price-board.test.tsx    # Doc 03 §5.5
```

#### Task 4.5 — TradingView Chart

| Attribute | Detail |
|:---|:---|
| **What** | `TradingChart` component — Canvas-based candlestick chart with agent signal overlays |
| **Where** | `frontend/app/(dashboard)/_components/trading-chart.tsx` |
| **Tech** | TradingView Lightweight Charts, `ResizeObserver` |
| **Test** | Storybook story; verify chart creates/destroys without memory leaks |

**Files to create:**
```
frontend/app/(dashboard)/_components/trading-chart.tsx        # Doc 03 §3.4
frontend/app/(dashboard)/_components/chart-overlays/
    signal-markers.ts                                          # Doc 03 §3.5
```

#### Task 4.6 — Portfolio Dashboard & Order Components

| Attribute | Detail |
|:---|:---|
| **What** | Portfolio positions table, PnL chart, order form with validation, order history |
| **Where** | `frontend/app/portfolio/_components/`, `frontend/app/orders/_components/` |
| **Tech** | AG Grid, Shadcn UI form components |
| **Test** | Component tests for form validation (lot size 100, price within band) |

#### Task 4.7 — Command Palette (Ctrl+K)

| Attribute | Detail |
|:---|:---|
| **What** | Command Palette for text-based commands: "Buy FPT 1000 price 98.5", "Show MA 200" |
| **Where** | `frontend/components/command-palette.tsx` |
| **Tech** | Shadcn UI `<Command>`, Zustand `ui-store` |
| **Test** | Parse known commands correctly; reject invalid syntax |

### 4.3. Definition of Done — Phase 4

```
□ `pnpm build` succeeds with zero TypeScript errors
□ `pnpm tsc --noEmit` passes (strict mode, no `any`)
□ Dark Mode renders correctly (Zinc/Slate palette)
□ AG Grid displays 1,800 rows at ≥ 55fps with mock tick updates
□ TradingView chart renders candles + signal markers
□ WebSocket messages route to correct Zustand store (tested)
□ Zustand selector: updating FPT does NOT re-render VNM component (verified)
□ Portfolio page shows positions with PnL calculation
□ Order form validates lot size + price band client-side
□ Command Palette opens on Ctrl+K, parses "Buy FPT 1000" correctly
□ Bundle size < 500 KB gzipped
□ All backend tests still pass (no regressions)
□ Frontend coverage ≥ 80%
```

---

## PHASE 5: AI EDGE INFERENCE & ORDER EXECUTION

**Duration:** Weeks 10-12
**Principle:** "The system becomes autonomous. NPU thinks, broker executes, safety never sleeps."
**Blueprint References:** Doc 04 (Section 2), Doc 05 (Sections 2-3)

### 5.1. Objective

Quantize and deploy LLM on Intel NPU via OpenVINO, implement the `Fundamental Agent`, build the live `Executor Agent` with idempotent order placement, and connect everything to real broker APIs. At the end of Phase 5, the system is **fully operational**.

### 5.2. Tasks

#### Task 5.1 — OpenVINO Model Quantization & Engine

| Attribute | Detail |
|:---|:---|
| **What** | INT4 quantize Phi-3-mini (or Llama-3-8B), build `OpenVINOEngine` adapter, auto-detect NPU/GPU/CPU |
| **Where** | `packages/adapters/src/adapters/openvino/` |
| **Tech** | `optimum[openvino]`, `openvino-genai>=2024.4`, `nncf` |
| **Test** | Engine loads model → generates ≥ 10 tokens → output is non-empty string; CPU fallback works when NPU unavailable |

**Files to create:**
```
packages/adapters/src/adapters/openvino/__init__.py
packages/adapters/src/adapters/openvino/engine.py        # Doc 04 §2.6
packages/adapters/src/adapters/openvino/model_loader.py  # Doc 04 §2.7
scripts/quantize_model.py                                 # Doc 04 §2.5 (one-time)
```

#### Task 5.2 — Fundamental Agent (NPU-powered)

| Attribute | Detail |
|:---|:---|
| **What** | `FundamentalAgent.run()` — retrieves news, assembles versioned prompt, runs NPU inference, returns AI insight |
| **Where** | `packages/agents/src/agents/fundamental_agent.py` |
| **Tech** | OpenVINO Engine, PromptBuilder, Vnstock news adapter |
| **Test** | Mock engine returns canned response → verify insight stored in state correctly |

**Files to create:**
```
packages/agents/src/agents/fundamental_agent.py      # Doc 04 §3.6
tests/unit/test_fundamental_agent.py
```

#### Task 5.3 — OMS: Idempotent Order Placement

| Attribute | Detail |
|:---|:---|
| **What** | `place_order()` use case with full idempotency, `IdempotencyStore`, `OrderStatusSynchronizer`, audit trail |
| **Where** | `packages/core/src/core/use_cases/place_order.py`, `packages/adapters/src/adapters/ssi/order_sync.py` |
| **Tech** | DuckDB for audit log, SSI broker adapter for live orders |
| **Test** | Same idempotency key twice → second call returns cached order (tested); Broker status sync maps SSI statuses correctly (tested) |

**Files to create:**
```
packages/core/src/core/use_cases/place_order.py      # Doc 05 §2.4
packages/adapters/src/adapters/ssi/order_sync.py     # Doc 05 §2.5
tests/unit/test_place_order.py
tests/integration/test_order_sync.py
```

#### Task 5.4 — Live Executor Agent

| Attribute | Detail |
|:---|:---|
| **What** | Upgrade `ExecutorAgent` from dry_run stub to live broker integration via `BrokerPort` |
| **Where** | `packages/agents/src/agents/executor_agent.py` |
| **Tech** | SSI/DNSE broker adapters |
| **Test** | With mock broker: order placed → status transitions correctly; with dry_run flag: no broker call |

#### Task 5.5 — Vector Store (Optional RAG)

| Attribute | Detail |
|:---|:---|
| **What** | DuckDB `vss` extension, `news_embeddings` table, `DuckDBVectorStore`, `RAGFundamentalAgent` |
| **Where** | `packages/adapters/src/adapters/duckdb/vector_store.py` |
| **Tech** | DuckDB vss, `sentence-transformers` |
| **Test** | Insert 100 embeddings → similarity search returns top-k with correct ordering |

**Files to create (if time permits):**
```
packages/adapters/src/adapters/duckdb/vector_store.py   # Doc 04 §4.4
packages/adapters/src/adapters/embedding/model.py       # Doc 04 §4.6
packages/agents/src/agents/fundamental_agent_rag.py     # Doc 04 §4.5
```

#### Task 5.6 — End-to-End Integration

| Attribute | Detail |
|:---|:---|
| **What** | Wire everything: Data Agent → DuckDB → Agents → WebSocket → Frontend. Full system test with mock market data. |
| **Where** | `packages/interface/src/interface/dependencies.py` (final wiring) |
| **Test** | Start system → inject 100 mock ticks → verify Screener triggers → Technical scores → Risk validates → Executor creates plan → Frontend displays signal |

### 5.3. Definition of Done — Phase 5

```
□ Phi-3-mini INT4 loads on NPU (or CPU fallback) and generates coherent text
□ Fundamental Agent produces AI Insight in Vietnamese for given symbol
□ Order placement with idempotency key: duplicate detected and cached (tested)
□ Order status sync: SSI "Fill" → local MATCHED, "Rejected" → BROKER_REJECTED (tested)
□ Executor Agent with dry_run=False places real order via mock broker (tested)
□ Audit trail captures every order state change in DuckDB (tested)
□ Full E2E: mock data → pipeline → signal → WebSocket → frontend display (tested)
□ System starts with single command: `uv run python -m interface.cli`
□ All tests pass. Coverage gates met. Zero type errors. Zero linter warnings.
□ Performance: full pipeline < 5s, AG Grid ≥ 55fps, bundle < 500KB
```

---

## 3. TESTING & QA STRATEGY

### 3.1. Testing Pyramid

```
                        ┌─────────┐
                        │   E2E   │   ~5 tests
                        │ Full    │   Start server, inject data, verify signals
                        │ pipeline│   arrive at WebSocket endpoint
                        ├─────────┤
                    ┌───┴─────────┴───┐
                    │  Integration    │   ~25 tests
                    │  DuckDB + repo  │   Real DuckDB (in-memory), mock network
                    │  Agent + state  │   Agent nodes with mock adapter ports
                    ├─────────────────┤
                ┌───┴─────────────────┴───┐
                │      Unit Tests         │   ~80+ tests
                │  Pure functions:        │   Risk check, price band, settlement
                │  Routing logic:         │   LangGraph conditional edges
                │  State transforms:      │   Agent output formatting
                │  Store logic:           │   Zustand updates (frontend)
                └─────────────────────────┘
```

### 3.2. Mock Data Strategy — Testing When Markets Are Closed

```
┌────────────────────────────────────────────────────────────────────┐
│                   MOCK DATA STRATEGY                                │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  UNIT TESTS — Deterministic fixtures                              │
│  ├── tests/fixtures/sample_ticks.parquet       (100 FPT ticks)   │
│  ├── tests/fixtures/sample_ohlcv.json          (200-day FPT)     │
│  ├── tests/fixtures/sample_orders.json         (10 orders)       │
│  └── tests/conftest.py                         (pytest fixtures) │
│                                                                    │
│  INTEGRATION TESTS — DuckDB in-memory                             │
│  ├── Fresh DuckDB per test: duckdb.connect(":memory:")           │
│  ├── Seed with fixture data in conftest                          │
│  └── No file I/O, no network, instant teardown                   │
│                                                                    │
│  AGENT TESTS — Fake adapters (Protocol implementations)           │
│  ├── FakeMarketData — yields predefined ticks                    │
│  ├── FakeTickRepo — stores in list for assertion                 │
│  ├── FakeBrokerPort — records calls, returns mock order IDs      │
│  └── FakeAIEngine — returns canned AI insights                   │
│                                                                    │
│  FRONTEND TESTS — Mocked stores                                   │
│  ├── useMarketStore.setState({ ticks: {...} })                   │
│  ├── vi.mock("ag-grid-react", ...) for lightweight grid mock     │
│  └── MSW (Mock Service Worker) for WebSocket simulation          │
│                                                                    │
│  DEVELOPMENT — Live data replay                                   │
│  ├── Record real SSI WebSocket session to Parquet file            │
│  ├── Replay from file at configurable speed (1x, 5x, 10x)       │
│  └── Allows full system testing outside market hours              │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### 3.3. Coverage Targets

| Package | Target | Hard Minimum | Enforcement |
|:---|:---|:---|:---|
| `packages/core` | ≥ 90% | ≥ 85% | `pytest-cov --cov-fail-under=85` |
| `packages/adapters` | ≥ 85% | ≥ 80% | `pytest-cov --cov-fail-under=80` |
| `packages/agents` | ≥ 85% | ≥ 80% | `pytest-cov --cov-fail-under=80` |
| `frontend/` | ≥ 85% | ≥ 80% | `vitest --coverage.thresholds.lines=80` |

---

## 4. DEV ENVIRONMENT SETUP

### 4.1. Prerequisites

```
Required:
  - Python 3.12+ (verify: python --version)
  - uv (install: curl -LsSf https://astral.sh/uv/install.sh | sh)
  - Node.js 20+ (verify: node --version)
  - pnpm 9+ (install: npm install -g pnpm)
  - Git 2.40+

Recommended:
  - Intel Core Ultra CPU with NPU (for Phase 5 — CPU fallback available)
  - VS Code / Cursor IDE
  - 16+ GB RAM (DuckDB + NPU model loading)
```

### 4.2. First-Time Setup (< 2 minutes)

```bash
# 1. Clone and enter repo
git clone <repo-url> algo-trading && cd algo-trading

# 2. Install Python dependencies (all 4 packages in workspace)
uv sync

# 3. Verify Python toolchain
uv run ruff check packages/ tests/        # Linter
uv run mypy packages/ --strict             # Type checker
uv run pytest tests/ -v --tb=short         # Tests

# 4. Install Frontend dependencies
cd frontend && pnpm install && cd ..

# 5. Verify Frontend toolchain
cd frontend && pnpm tsc --noEmit && pnpm vitest run && cd ..

# 6. Setup environment variables
cp .env.example .env
# Edit .env with your SSI credentials (NEVER commit this file)

# 7. Create data directories
mkdir -p data/{models,parquet,prompts,secrets}

# 8. Start the system (development mode)
uv run python -m interface.cli             # Backend: http://localhost:8000
cd frontend && pnpm dev                    # Frontend: http://localhost:3000
```

### 4.3. Git Hooks (Pre-commit)

```bash
# Install pre-commit hooks
uv add --dev pre-commit
uv run pre-commit install

# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ruff-check
        name: Ruff Lint
        entry: uv run ruff check --fix
        language: system
        types: [python]
      - id: ruff-format
        name: Ruff Format
        entry: uv run ruff format
        language: system
        types: [python]
      - id: mypy
        name: mypy strict
        entry: uv run mypy packages/ --strict
        language: system
        types: [python]
        pass_filenames: false
      - id: no-credentials
        name: Check no credentials
        entry: bash -c 'git diff --cached --name-only | xargs grep -l "BEGIN RSA\|PRIVATE_KEY\|consumer_secret" && exit 1 || exit 0'
        language: system
```

---

## 5. RISK MANAGEMENT — TECHNICAL RISKS & MITIGATIONS

### Risk 1: WebSocket Connection Loss During Market Hours

```
SEVERITY:    CRITICAL (missing tick data = wrong analysis)
PROBABILITY: HIGH (network instability, SSI server maintenance)

MITIGATION (built into Phase 2):
  ✓ Exponential backoff reconnection (1s → 60s cap, with jitter)
  ✓ Circuit breaker prevents reconnect storm
  ✓ In-memory buffer (deque) retains data during brief outages
  ✓ ConnectionState tracked and exposed to frontend health indicator
  ✓ Parquet historical data fills gaps after reconnection (backfill)

DETECTION:
  ✓ WebSocket state change triggers structured log entry
  ✓ Frontend displays connection status (green/yellow/red)
  ✓ Alert if disconnected > 5 minutes during market hours
```

### Risk 2: Duplicate Order Placement (Race Condition)

```
SEVERITY:    CRITICAL (financial loss — buy/sell 2x intended quantity)
PROBABILITY: MEDIUM (network timeout + retry, agent pipeline re-trigger)

MITIGATION (built into Phase 5):
  ✓ Idempotency key (UUID v4) generated per order intent
  ✓ IdempotencyStore: check → reserve → execute → record (atomic)
  ✓ DuckDB unique index on idempotency_key for persistence
  ✓ Order state machine rejects invalid transitions
  ✓ Executor Agent checks dry_run flag before broker call

DETECTION:
  ✓ Audit trail logs every state change with idempotency_key
  ✓ Duplicate detection returns was_duplicate=True in response
  ✓ Alert on any order_id that appears twice in audit log
```

### Risk 3: T+2.5 Settlement Miscalculation

```
SEVERITY:    HIGH (selling unsettled shares → call margin, regulatory penalty)
PROBABILITY: MEDIUM (holiday calendars change annually, edge cases at date boundaries)

MITIGATION (built into Phase 1):
  ✓ Settlement logic uses sellableQty from broker API (source of truth)
  ✓ Local T+2.5 calculator cross-validates with broker data
  ✓ Holiday calendar (_VN_HOLIDAYS_2026) explicitly maintained and tested
  ✓ Risk Agent blocks SELL if quantity > sellableQty - pending_sells
  ✓ Unit tests cover: Friday→Tuesday, pre-holiday, cross-month

DETECTION:
  ✓ Risk check logs "SELLABLE_QTY" check result for every order
  ✓ Alert on any BROKER_REJECTED with reason containing "settlement"
```

### Risk 4: NPU Unavailability (Model Loading Failure)

```
SEVERITY:    MEDIUM (degraded — no AI insights, but trading still works)
PROBABILITY: LOW-MEDIUM (driver issues, model corruption, non-Intel hardware)

MITIGATION (built into Phase 5):
  ✓ Auto-detect device: NPU → GPU → CPU fallback chain
  ✓ Fundamental Agent is non-blocking parallel branch in LangGraph
  ✓ Pipeline completes without Fundamental Agent output (graceful degradation)
  ✓ Model checksum verified before loading (detect corruption)
  ✓ Health endpoint reports NPU status

DETECTION:
  ✓ Model loading error logged with device info
  ✓ Frontend shows "AI Offline" indicator when fundamental unavailable
```

### Risk 5: DuckDB Data Corruption (Single-Writer Constraint)

```
SEVERITY:    HIGH (loss of historical tick data, PnL miscalculation)
PROBABILITY: LOW (DuckDB is stable, but unexpected process termination possible)

MITIGATION (built into Phase 1):
  ✓ Parquet files are the durable store (immutable after write)
  ✓ DuckDB tables are rebuilt from Parquet on startup if needed
  ✓ Batch writes use WAL (Write-Ahead Log) mode
  ✓ Single-writer enforced by application design (one DataAgent)
  ✓ data/ directory excluded from git but backed up daily

DETECTION:
  ✓ Startup integrity check: row count in DuckDB vs Parquet files
  ✓ Alert if DuckDB file exceeds expected size (possible WAL buildup)
```

---

## 6. WEEKLY TIMELINE (GANTT SUMMARY)

```
Week   Phase 1          Phase 2          Phase 3          Phase 4          Phase 5
──────────────────────────────────────────────────────────────────────────────────────
  1    ████ Monorepo
       ████ Tooling
  2    ████ Entities
       ████ Ports
       ████ Use Cases
  3    ████ DuckDB       ████ SSI Auth
       ████ CI Pipeline  ████ Retry/CB
  4                      ████ WebSocket
                         ████ DataAgent
                         ████ Vnstock
  5                      ████ FastAPI     ████ AgentState
                         ████ WS Server   ████ Screener
  6                                       ████ Technical
                                          ████ Risk Agent
  7                                       ████ Supervisor                   
                                          ████ LangGraph    ████ Next.js Init
  8                                       ████ Prompts      ████ Zustand
                                          ████ Logging      ████ WS Provider
  9                                                         ████ AG Grid
                                                            ████ Chart
 10                                                         ████ Portfolio   ████ OpenVINO
                                                            ████ Orders      ████ Quant Model
 11                                                                          ████ Fundamental
                                                                             ████ OMS
 12                                                                          ████ Executor
                                                                             ████ E2E Test
──────────────────────────────────────────────────────────────────────────────────────
```

---

## 7. SUCCESS CRITERIA — FINAL SYSTEM

When all 5 phases are complete, the system satisfies:

```
FUNCTIONAL
  □ Receives real-time market data from SSI FastConnect via WebSocket
  □ Screens ~1,800 symbols, identifies top candidates
  □ Scores candidates technically (RSI, MACD, BB, MA)
  □ Generates AI Insights on local NPU (Phi-3 / Llama-3 INT4)
  □ Validates orders against 7 risk rules (kill switch, NAV, price band, T+2.5, lot size, buying power, daily loss)
  □ Places orders via SSI/DNSE with idempotency guarantee
  □ Displays everything in real-time Dark Mode trading terminal

NON-FUNCTIONAL
  □ Full pipeline latency < 5s (excluding NPU inference)
  □ AG Grid renders 1,800 rows at ≥ 55fps
  □ JS bundle < 500 KB gzipped
  □ Zero credentials in git history
  □ Zero `any` types in TypeScript
  □ Zero `# type: ignore` without specific error code
  □ Test coverage ≥ 85% (backend), ≥ 80% (frontend)
  □ CI pipeline runs in < 65 seconds
```

---

## APPENDIX: BLUEPRINT CROSS-REFERENCE

| Task | Primary Blueprint | Sections |
|:---|:---|:---|
| Monorepo, Clean Architecture | Doc 02 | §1, §2 |
| DuckDB, ASOF JOIN, Parquet | Doc 02 | §3 |
| Async patterns, concurrency | Doc 02 | §4 |
| Backend testing | Doc 02 | §5 |
| Next.js, Server/Client Components | Doc 03 | §1 |
| AG Grid, DOM Virtualization | Doc 03 | §2 |
| Canvas Charts, TradingView | Doc 03 | §3 |
| Zustand, WebSocket bridge | Doc 03 | §4 |
| Frontend testing | Doc 03 | §5 |
| LangGraph StateGraph, Agents | Doc 04 | §1 |
| OpenVINO INT4, NPU inference | Doc 04 | §2 |
| Prompt versioning | Doc 04 | §3 |
| Vector Store, RAG (optional) | Doc 04 | §4 |
| SSI RSA auth, key storage | Doc 05 | §1 |
| OMS, idempotency, order FSM | Doc 05 | §2 |
| T+2.5, price bands, lot size | Doc 05 | §3 |
| Retry, backoff, circuit breaker | Doc 05 | §4 |
| All coding standards | Doc 06 | Full document |
| Hardware resource allocation | Doc 01 | §4 |
| System data flow | Doc 01 | §3 |

---

*This plan is a living document. Update it as implementation reveals new constraints or opportunities. The blueprints (01-06) remain the authoritative source for technical details — this plan tells you WHEN and IN WHAT ORDER to build them.*
