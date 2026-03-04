# 01 — SYSTEM ARCHITECTURE OVERVIEW

**Project:** Multi-Task Algorithmic Trading System (Enterprise Edition)
**Platform:** Hybrid AI & Intel Core Ultra
**Author:** Senior System Architect
**Version:** 1.0 | February 2026

---

## 1. EXECUTIVE SUMMARY (TECHNICAL VIEW)

### 1.1. Hybrid AI & Edge Computing model — Why not pure Cloud-native?

The system architecture is designed according to the **Hybrid Cloud-Edge** model, in which the workload is clearly separated between two processing layers:

| Floor | Workload | Features |
|:---|:---|:---|
| **Cloud (Remote)** | Market Data ingestion, Portfolio Sync, News Feed | I/O-bound, high-bandwidth, low-compute |
| **Edge (Local NPU/CPU)** | AI Inference, Quantitative Analysis, Risk Calc | Compute-bound, latency-sensitive, data-private |

#### 1.1.1. The Latency Problem — Why Edge Wins Over Cloud

In algorithmic trading, **every millisecond has a monetary value**. Analyze latency budget for a decision cycle:

```
Cloud-native Pipeline:
  Market Tick → Cloud Ingest → Cloud AI Inference → Cloud DB Query → Response
  Latency:  ~2ms    ~15-40ms (WAN RTT)   ~50-200ms (LLM API)   ~5-15ms     = 72-257ms

Hybrid Edge Pipeline:
  Market Tick → Local Ingest → NPU Inference → DuckDB In-Process → Response
  Latency:  ~2ms    ~0.1ms (IPC)       ~8-25ms (INT4 local)  ~0.5-2ms    = 10.6-29.1ms
```

**Conclusion:** Pipeline Edge reduces latency on average **5-10x** compared to Cloud-native. With high frequency tick data (hundreds of ticks/second), eliminating network round-trip is the deciding factor.

#### 1.1.2. Privacy problem — Zero Data Leakage

Cloud-native forces sensitive financial data (portfolio positions, trading signals, risk parameters) to transit through the public internet and store on third-party infrastructure. The Edge model thoroughly solves:

- **Data Residency:** All transaction data, categories, and AI model weights reside on local storage. No bytes leave the machine except API calls to the exchange.
- **Inference Privacy:** LLM runs on NPU and processes basic analysis (news, financial reports) completely offline. No prompt/response is logged by the third-party API provider.
- **Compliance-ready:** Compliant with regulations on personal financial data security without the need for complex end-to-end encryption via the cloud.

#### 1.1.3. Why Intel Core Ultra 7 256V NPU?

The NPU (Neural Processing Unit) on Lunar Lake provides **48 TOPS (INT8)** — enough to run INT4 quantized LLM models (Phi-3-mini, Llama-3-8B) with acceptable throughput, while consuming only **~5-10W TDP** (compared to discrete GPUs consuming 75-350W). This is the optimal balance between AI inference performance and power efficiency for a system that runs continuously during the trading session (9:00–15:00 daily).

---

## 2. TECH STACK JUSTIFICATION

### 2.1. Package Manager: `uv` (Rust) vs `poetry` (Python)

| Criteria | `uv` (Astral, Rust) | `poetry` (Python) | Verdict |
|:---|:---|:---|:---|
| **Resolve + install speed** | 10-100x faster than pip/poetry (real benchmark: `uv pip install` < 1s for ~200 packages) | Resolve is slow, especially with complex dependency trees (~30-120s) | **uv** ✓ |
| **Cold start** | No need for Python runtime to bootstrap | Need Python + pip to install poetry first | **uv** ✓ |
| **Monorepo / Workspaces** | Native support — allows organizing `/core`, `/connectors`, `/analytics`, `/agents` in the same repo | Does not support native, must use workaround (path dependencies) | **uv** ✓ |
| **Lockfile determinism** | `uv.lock` — cross-platform, reproducible | `poetry.lock` — equivalent to | Horizontal |
| **Ecosystem maturity** | New (2024+), API is stabilizing fast | Mature, large community | **poetry** ✓ |
| **Reason for choosing** | In trading systems, CI/CD pipeline and developer iteration speed are critical. `uv` reduces environment setup time from minutes to seconds, and native workspace support fits perfectly into the Multi-Agent monorepo architecture. | | |

### 2.2. Database: DuckDB (OLAP) vs PostgreSQL (OLTP) cho Tick Data

| Criteria | DuckDB | PostgreSQL (+ TimescaleDB) | Verdict |
|:---|:---|:---|:---|
| **Architecture** | In-process, embedded (like SQLite but columnar) | Client-server, needs separate daemon | **DuckDB** ✓ |
| **Storage format** | Columnar (column-oriented) | Row-oriented (TimescaleDB: hybrid) | **DuckDB** ✓ cho analytics |
| **Network latency** | **Zero** — runs in the same process as Python | ~0.5-2ms per query (localhost TCP) | **DuckDB** ✓ |
| **Compression ratio (tick data)** | Extreme — columnar + dictionary encoding on columns `symbol`, `exchange`. Parquet files compressed ~5-10x | Moderate — TOAST compression, row-level | **DuckDB** ✓ |
| **ASOF JOIN** | **Native SQL support** — critical for financial time-series (matching orders with prices at the most recent time) | Not native, must use `LATERAL JOIN` + complex subquery | **DuckDB** ✓ |
| **Vectorized execution** | The entire query engine processes in batches (vector of values), optimizing CPU cache | Tuple-at-a-time (Volcano model) | **DuckDB** ✓ |
| **Direct Scan of Parquet** | Native — directly query file `.parquet` on disk without import | Need separate ETL pipeline (COPY, fdw) | **DuckDB** ✓ |
| **Concurrent writes** | Single-writer — not suitable for multi-user OLTP | Multi-writer, full ACID | **PostgreSQL** ✓ |
| **Reason for choosing** | This system is a **single-user analytical workstation**, not a multi-tenant web app. DuckDB completely eliminates the overhead of database server, network protocol, and connection pooling. With tick data (append-heavy, scan-heavy, join-heavy), columnar storage + vectorized execution + native ASOF JOIN creates a **10-100x** performance advantage for analytical queries compared to PostgreSQL row-store. | | |

### 2.3. AI Orchestration: LangGraph + OpenVINO

| Criteria | LangGraph + OpenVINO | Alternatives (LangChain + Cloud LLM API) |
|:---|:---|:---|
| **Agent orchestration** | Graph-based state machine — deterministic, debuggable | Chain-based, difficult to control complex flows |
| **Inference runtime** | OpenVINO on NPU — local, zero API cost | Cloud API (OpenAI, Anthropic) — pay-per-token, high latency |
| **Model support** | Phi-3-mini, Llama-3-8B (INT4 quantized) — enough for financial text analysis | GPT-4, Claude — stronger but overkill + privacy risk |
| **Reason for choosing** | LangGraph allows modeling Multi-Agent System as directed graph with clear state management (Supervisor pattern). OpenVINO is the only runtime optimized for Intel NPU, allowing to run LLM inference without the need for a discrete GPU. | |

### 2.4. Frontend: Next.js + AG Grid + TradingView Lightweight Charts

| Criteria | Options | Reason |
|:---|:---|:---|
| **Framework** | Next.js (App Router, React 19) | Server Components for initial load, Client Components for real-time WebSocket. Persistent layouts avoid re-rendering when switching views. |
| **Data Grid** | AG Grid Enterprise | DOM virtualization — render only viewport rows. Cell-level transaction update at 60fps. Pivot/Master-Detail for multidimensional analysis. |
| **Charting** | TradingView Lightweight Charts | HTML5 Canvas (no SVG) — zero reflow/repaint overhead. Custom overlay API for Technical/Risk Agent markers. |
| **UI System** | Shadcn UI + Tailwind CSS | High-density design, default Dark Mode (Slate/Zinc palette). Component-level tree-shaking. |

---

## 3. SYSTEM TOPOGRAPHY — DATA FLOW

### 3.1. End-to-End data flow overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL DATA SOURCES                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │ SSI FastConnect│  │   Vnstock    │  │  DNSE API    │                      │
│  │  (WebSocket)  │  │  (REST/WS)   │  │  (REST)      │                      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                      │
└─────────┼──────────────────┼──────────────────┼─────────────────────────────┘
          │ wss://           │ https://          │ https://
          ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PYTHON BACKEND (FastAPI + Asyncio)                       │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     DATA AGENT (Ingestion Layer)                    │    │
│ │ • WebSocket client (async) receives market ticks │ │
│ │ • In-memory buffer (dict/deque) holds latest price per symbol │ │
│ │ • Batch writer: flush buffer → DuckDB every 1s │ │
│  └──────────────────────────┬──────────────────────────────────────────┘    │
│                             │                                               │
│                             ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                     DuckDB (In-Process OLAP)                       │    │
│  │  • Columnar storage: tick data, OHLCV, order history               │    │
│  │  • Parquet files partitioned by date (YYYY/MM/DD/)                 │    │
│  │  • ASOF JOIN engine cho PnL calculation & backtesting              │    │
│  └──────────────────────────┬──────────────────────────────────────────┘    │
│                             │                                               │
│              ┌──────────────┼──────────────┐                                │
│              ▼              ▼              ▼                                │
│  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐                     │
│  │ Screener Agent│ │Technical Agent│ │  Risk Agent   │                     │
│  │ (SQL queries) │ │(pandas-ta,   │ │(VaR, position │                     │
│  │               │ │ PyPortOpt)   │ │ limits)       │                     │
│  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘                     │
│          │                 │                 │                              │
│          └────────┬────────┴────────┬────────┘                              │
│                   ▼                 ▼                                       │
│  ┌───────────────────┐  ┌────────────────────────┐                         │
│  │  Supervisor Agent │  │  Fundamental Agent     │                         │
│  │  (LangGraph)      │◄─│  (OpenVINO on NPU)     │                         │
│  │  Aggregates all   │  │  LLM Inference:        │                         │
│  │  agent outputs    │  │  Phi-3 / Llama-3 INT4  │                         │
│  └────────┬──────────┘  └────────────────────────┘                         │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │              FastAPI WebSocket Server (Outbound)                    │    │
│  │  • JSON streaming: signals, scores, AI insights, portfolio state   │    │
│  │  • Binary frames: high-frequency tick data (MessagePack)           │    │
│  └──────────────────────────┬──────────────────────────────────────────┘    │
└─────────────────────────────┼───────────────────────────────────────────────┘
                              │ ws://localhost:8000
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     NEXT.JS FRONTEND (Browser)                              │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  AG Grid     │  │  TradingView │  │  Portfolio    │  │  Command     │   │
│  │  (Watchlist, │  │  Charts      │  │  Dashboard   │  │  Palette     │   │
│  │   Screener)  │  │  (Candles +  │  │  (PnL, Risk) │  │  (Ctrl+K)    │   │
│  │              │  │   Overlays)  │  │              │  │              │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                             │
│                          ┌──────────┐                                       │
│                          │   USER   │                                       │
│                          └──────────┘                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2. Details of processing flow for each phase

**Phase 1 — Data Ingestion (Continuous)**
1. `Data Agent` opens a persistent WebSocket connection to SSI FastConnect.
2. Each tick message is deserialized, validated (Pydantic V2 — Rust core), and written to the in-memory buffer (Python `dict` keyed by symbol).
3. Background task flush buffer into DuckDB every 1 second (batch insert ~500-2000 rows/batch). At the same time, write Parquet file partitioned by date.

**Phase 2 — Analysis (Event-driven + Periodic)**
4. `Screener Agent` runs vectorized SQL queries on DuckDB every 30–60 seconds, calculating technical indicators across the market. Output: Dynamic Watchlist.
5. `Technical Agent` receives a trigger when a symbol is added to the watchlist or according to the schedule. Run `pandas-ta` for scoring, `PyPortfolioOpt` for portfolio rebalancing. Push heavy logic down to DuckDB SQL (ASOF JOIN, window functions).
6. `Fundamental Agent` retrieves information from Vnstock, packages it into a prompt, and sends it to NPU via OpenVINO runtime. Get back AI Insight (natural language analysis).
7. `Risk Agent` runs in parallel, validating every signal/order before emitting it. Calculate VaR from historical data in DuckDB.

**Phase 3 — Delivery (Real-time)**
8. `Supervisor Agent` (LangGraph) aggregates output from all agents, resolves conflicts, creates unified signal.
9. FastAPI WebSocket server streams results to the frontend: JSON for signals/insights, MessagePack for high-frequency data.
10. Next.js Client Components receive data, update AG Grid (cell-level transaction update), draw overlay on TradingView Charts, refresh Portfolio Dashboard.

---

## 4. HARDWARE UTILIZATION — RESOURCE ALLOCATION PER AGENT

### 4.1. Intel Core Ultra 7 256V — Resource Map

Lunar Lake provides 3 compute domains:

| Domain | Specs (Core Ultra 7 256V) | Optimal properties |
|:---|:---|:---|
| **CPU** | 4P-cores (Lion Cove) + 4E-cores (Skymont), ~30W PBP | General-purpose, sequential logic, I/O orchestration |
| **NPU** | Intel AI Boost, 48 TOPS (INT8) | Sustained AI inference, power-efficient, matrix operations |
| **GPU** | Intel Arc (8 Xe-cores), ~7 TOPS (FP16) | Parallel compute, visualization offload |

### 4.2. Agent → Hardware Mapping

```
┌─────────────────────────────────────────────────────────────────┐
│                    HARDWARE RESOURCE ALLOCATION                  │
├─────────────────────┬───────────┬───────────┬───────────────────┤
│ Agent               │ CPU       │ NPU       │ GPU               │
├─────────────────────┼───────────┼───────────┼───────────────────┤
│ Data Agent          │ ██████░░  │ ░░░░░░░░  │ ░░░░░░░░░░░░░░░  │
│ (WebSocket I/O)     │ E-cores   │ —         │ —                 │
│                     │ asyncio   │           │                   │
├─────────────────────┼───────────┼───────────┼───────────────────┤
│ Screener Agent      │ ██░░░░░░  │ ░░░░░░░░  │ ░░░░░░░░░░░░░░░  │
│ (SQL dispatch)      │ E-core    │ —         │ —                 │
│                     │ (DuckDB   │           │                   │
│                     │  internal │           │                   │
│                     │  threads) │           │                   │
├─────────────────────┼───────────┼───────────┼───────────────────┤
│ Technical Agent     │ ████████  │ ░░░░░░░░  │ ██░░░░░░░░░░░░░  │
│ (pandas-ta,         │ P-cores   │ —         │ Optional:         │
│  PyPortfolioOpt)    │ NumPy/    │           │ cuBLAS-like       │
│                     │ SciPy     │           │ matrix ops via    │
│                     │           │           │ oneAPI/SYCL       │
├─────────────────────┼───────────┼───────────┼───────────────────┤
│ Fundamental Agent   │ ██░░░░░░  │ ████████  │ ░░░░░░░░░░░░░░░  │
│ (LLM Inference)     │ Pre/post  │ OpenVINO  │ —                 │
│                     │ processing│ INT4 model│                   │
│                     │ tokenizer │ inference │                   │
├─────────────────────┼───────────┼───────────┼───────────────────┤
│ Risk Agent          │ ████░░░░  │ ░░░░░░░░  │ ░░░░░░░░░░░░░░░  │
│ (VaR, validation)   │ P-core    │ —         │ —                 │
│                     │ DuckDB    │           │                   │
│                     │ queries   │           │                   │
├─────────────────────┼───────────┼───────────┼───────────────────┤
│ Supervisor Agent    │ ██░░░░░░  │ ░░░░░░░░  │ ░░░░░░░░░░░░░░░  │
│ (LangGraph state    │ E-core    │ —         │ —                 │
│  machine)           │ lightweight│          │                   │
├─────────────────────┼───────────┼───────────┼───────────────────┤
│ Frontend Rendering  │ ░░░░░░░░  │ ░░░░░░░░  │ ████████████████ │
│ (Browser/Chromium)  │ —         │ —         │ Canvas 2D/WebGL   │
│                     │           │           │ compositing       │
└─────────────────────┴───────────┴───────────┴───────────────────┘
```

### 4.3. Detailed allocation strategy

#### CPU — P-core / E-core split

- **E-cores (Efficiency):** For I/O-bound tasks that run continuously — `Data Agent` (WebSocket listener), `Supervisor Agent` (state routing), `Screener Agent` (SQL dispatch). These tasks need stable throughput but do not need high single-thread performance. E-cores consume little power, suitable for always-on workloads.
- **P-cores (Performance):** For burst compute — `Technical Agent` when running portfolio optimization (SciPy solver), `Risk Agent` when calculating VaR Monte Carlo simulation. These tasks need high peak single-thread IPC but only run according to event/schedule.

**Mechanism:** Use OS thread affinity (`taskset` on Linux, `SetThreadAffinityMask` on Windows) or Python `os.sched_setaffinity()` to pin agent threads to appropriate core groups. DuckDB manages its own internal thread pool, taking advantage of all available cores when running queries.

#### NPU — Dedicated cho LLM Inference

- **Exclusive workload:** `Fundamental Agent` is the only consumer of NPU.
- **Pipeline:** Tokenization (CPU) → Model forward pass (NPU via OpenVINO) → Detokenization (CPU).
- **Model config:** Phi-3-mini-4k-instruct (INT4, ~2.2GB) or Llama-3-8B (INT4, ~4.5GB). Batch size = 1 (single request at a time, suitable for single-user).
- **Throughput target:** ~15-30 tokens/second (INT4 on 48 TOPS NPU) — enough to generate 1 piece of AI Insight (~200 tokens) in ~7-13 seconds.
- **Power profile:** NPU consumes ~5-10W when active, ~0W when idle. Does not affect CPU/GPU thermal budget.

#### GPU (Intel Arc iGPU) — Visualization + Optional Compute

- **Primary role:** Browser rendering — TradingView Canvas 2D, AG Grid DOM compositing, CSS animations. This is the natural workload of the GPU in any desktop system.
- **Secondary role (optional):** If you need to speed up matrix operations for `Technical Agent` (large-scale covariance matrix, Monte Carlo), you can use Intel oneAPI/SYCL to offload to GPU. However, with the size of the Vietnamese market (~ 1,800 codes), P-core CPUs are enough to handle.
- **Do not use GPU for LLM:** NPU is more efficient than integrated GPU for sustained inference workload (higher tokens/watt).

### 4.4. Thermal & Power Budget (Estimated trading session)

| Status | CPU | NPU | GPU | Total TDP |
|:---|:---|:---|:---|:---|
| **Idle** (outside trading hours) | ~5W (E-cores only) | 0W | ~2W (desktop render) | ~7W |
| **Normal** (session, data streaming) | ~12W (E-cores active, P-cores boost occasionally) | 0-5W (on-demand inference) | ~3W (charts updated) | ~15-20W |
| **Peak** (portfolio rebalance + AI analysis + full market scan) | ~25W (all cores boost) | ~10W (sustained inference) | ~5W (heavy chart render) | ~40W |

All statuses are within Lunar Lake's 30W PBP, ensuring the system runs stably on laptops without external power for short periods of time, or runs continuously when plugged in.

---

## 5. KEY ARCHITECTURAL DECISIONS (ADR Summary)

| # | Decision | Rationale | Trade-off |
|:---|:---|:---|:---|
| ADR-001 | In-process DB (DuckDB) instead of client-server DB | Zero network latency, zero ops overhead | Single-writer, not scalable to multi-user |
| ADR-002 | NPU inference instead of Cloud LLM API | Privacy, zero cost, low latency | Limited model capability (≤8B params) |
| ADR-003 | Monorepo + `uv` workspaces | Shared types, atomic refactoring, fast CI | Need discipline within module boundaries |
| ADR-004 | WebSocket-first (no REST polling) | Real-time data push, lower overhead | More complicated error handling/reconnection |
| ADR-005 | Parquet partitioned storage | Compression, direct scan, time-travel queries | Not suitable for random point lookups |

---

*Document generated for internal technical review. Subject to revision as implementation progresses.*
