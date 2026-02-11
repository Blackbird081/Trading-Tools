# 01 — SYSTEM ARCHITECTURE OVERVIEW

**Project:** Hệ thống Giao dịch Thuật toán Đa Tác vụ (Enterprise Edition)
**Platform:** Hybrid AI & Intel Core Ultra
**Author:** Senior System Architect
**Version:** 1.0 | February 2026

---

## 1. EXECUTIVE SUMMARY (TECHNICAL VIEW)

### 1.1. Mô hình Hybrid AI & Edge Computing — Tại sao không Cloud-native thuần túy?

Kiến trúc hệ thống được thiết kế theo mô hình **Hybrid Cloud-Edge**, trong đó workload được phân tách rõ ràng giữa hai tầng xử lý:

| Tầng | Workload | Đặc tính |
|:---|:---|:---|
| **Cloud (Remote)** | Market Data ingestion, Portfolio Sync, News Feed | I/O-bound, high-bandwidth, low-compute |
| **Edge (Local NPU/CPU)** | AI Inference, Quantitative Analysis, Risk Calc | Compute-bound, latency-sensitive, data-private |

#### 1.1.1. Bài toán Latency — Tại sao Edge thắng Cloud

Trong giao dịch thuật toán, **mỗi mili-giây đều có giá trị tiền tệ**. Phân tích latency budget cho một chu kỳ quyết định (decision cycle):

```
Cloud-native Pipeline:
  Market Tick → Cloud Ingest → Cloud AI Inference → Cloud DB Query → Response
  Latency:  ~2ms    ~15-40ms (WAN RTT)   ~50-200ms (LLM API)   ~5-15ms     = 72-257ms

Hybrid Edge Pipeline:
  Market Tick → Local Ingest → NPU Inference → DuckDB In-Process → Response
  Latency:  ~2ms    ~0.1ms (IPC)       ~8-25ms (INT4 local)  ~0.5-2ms    = 10.6-29.1ms
```

**Kết luận:** Pipeline Edge giảm latency trung bình **5-10x** so với Cloud-native. Với tick data tần suất cao (hàng trăm tick/giây), việc loại bỏ network round-trip là yếu tố quyết định.

#### 1.1.2. Bài toán Privacy — Zero Data Leakage

Cloud-native buộc dữ liệu tài chính nhạy cảm (portfolio positions, trading signals, risk parameters) phải transit qua public internet và lưu trên infrastructure của bên thứ ba. Mô hình Edge giải quyết triệt để:

- **Data Residency:** Toàn bộ dữ liệu giao dịch, danh mục, và AI model weights nằm trên local storage. Không có byte nào rời khỏi máy trừ API calls tới sàn.
- **Inference Privacy:** LLM chạy trên NPU xử lý phân tích cơ bản (tin tức, báo cáo tài chính) hoàn toàn offline. Không có prompt/response nào bị log bởi third-party API provider.
- **Compliance-ready:** Phù hợp với các quy định về bảo mật dữ liệu tài chính cá nhân mà không cần mã hóa end-to-end phức tạp qua cloud.

#### 1.1.3. Tại sao NPU Intel Core Ultra 7 256V?

NPU (Neural Processing Unit) trên Lunar Lake cung cấp **48 TOPS (INT8)** — đủ để chạy các model LLM lượng tử hóa INT4 (Phi-3-mini, Llama-3-8B) với throughput chấp nhận được, trong khi tiêu thụ chỉ **~5-10W TDP** (so với GPU discrete tiêu thụ 75-350W). Đây là điểm cân bằng tối ưu giữa hiệu năng AI inference và power efficiency cho một hệ thống chạy liên tục trong phiên giao dịch (9:00–15:00 daily).

---

## 2. TECH STACK JUSTIFICATION

### 2.1. Package Manager: `uv` (Rust) vs `poetry` (Python)

| Tiêu chí | `uv` (Astral, Rust) | `poetry` (Python) | Verdict |
|:---|:---|:---|:---|
| **Tốc độ resolve + install** | 10-100x nhanh hơn pip/poetry (benchmark thực tế: `uv pip install` < 1s cho ~200 packages) | Resolve chậm, đặc biệt với dependency tree phức tạp (~30-120s) | **uv** ✓ |
| **Cold start** | Không cần Python runtime để bootstrap | Cần Python + pip để cài poetry trước | **uv** ✓ |
| **Monorepo / Workspaces** | Native support — cho phép tổ chức `/core`, `/connectors`, `/analytics`, `/agents` trong cùng repo | Không hỗ trợ native, phải dùng workaround (path dependencies) | **uv** ✓ |
| **Lockfile determinism** | `uv.lock` — cross-platform, reproducible | `poetry.lock` — tương đương | Ngang |
| **Ecosystem maturity** | Mới (2024+), API đang ổn định nhanh | Mature, community lớn | **poetry** ✓ |
| **Lý do chọn** | Trong hệ thống trading, CI/CD pipeline và developer iteration speed là critical. `uv` giảm thời gian setup environment từ phút xuống giây, và native workspace support phù hợp hoàn hảo với kiến trúc Multi-Agent monorepo. | | |

### 2.2. Database: DuckDB (OLAP) vs PostgreSQL (OLTP) cho Tick Data

| Tiêu chí | DuckDB | PostgreSQL (+ TimescaleDB) | Verdict |
|:---|:---|:---|:---|
| **Kiến trúc** | In-process, embedded (như SQLite nhưng columnar) | Client-server, cần daemon riêng | **DuckDB** ✓ |
| **Storage format** | Columnar (column-oriented) | Row-oriented (TimescaleDB: hybrid) | **DuckDB** ✓ cho analytics |
| **Network latency** | **Zero** — chạy cùng process với Python | ~0.5-2ms per query (localhost TCP) | **DuckDB** ✓ |
| **Compression ratio (tick data)** | Cực cao — columnar + dictionary encoding trên cột `symbol`, `exchange`. Parquet files nén ~5-10x | Moderate — TOAST compression, row-level | **DuckDB** ✓ |
| **ASOF JOIN** | **Native SQL support** — critical cho financial time-series (ghép lệnh với giá tại thời điểm gần nhất) | Không native, phải dùng `LATERAL JOIN` + subquery phức tạp | **DuckDB** ✓ |
| **Vectorized execution** | Toàn bộ query engine xử lý theo batch (vector of values), tối ưu CPU cache | Tuple-at-a-time (Volcano model) | **DuckDB** ✓ |
| **Scan trực tiếp Parquet** | Native — query trực tiếp file `.parquet` trên disk mà không cần import | Cần ETL pipeline riêng (COPY, fdw) | **DuckDB** ✓ |
| **Concurrent writes** | Single-writer — không phù hợp multi-user OLTP | Multi-writer, ACID full | **PostgreSQL** ✓ |
| **Lý do chọn** | Hệ thống này là **single-user analytical workstation**, không phải multi-tenant web app. DuckDB loại bỏ hoàn toàn overhead của database server, network protocol, connection pooling. Với tick data (append-heavy, scan-heavy, join-heavy), columnar storage + vectorized execution + native ASOF JOIN tạo ra lợi thế hiệu năng **10-100x** cho các truy vấn phân tích so với PostgreSQL row-store. | | |

### 2.3. AI Orchestration: LangGraph + OpenVINO

| Tiêu chí | LangGraph + OpenVINO | Alternatives (LangChain + Cloud LLM API) |
|:---|:---|:---|
| **Agent orchestration** | Graph-based state machine — deterministic, debuggable | Chain-based, khó kiểm soát flow phức tạp |
| **Inference runtime** | OpenVINO trên NPU — local, zero API cost | Cloud API (OpenAI, Anthropic) — pay-per-token, latency cao |
| **Model support** | Phi-3-mini, Llama-3-8B (INT4 quantized) — đủ cho financial text analysis | GPT-4, Claude — mạnh hơn nhưng overkill + privacy risk |
| **Lý do chọn** | LangGraph cho phép mô hình hóa Multi-Agent System dưới dạng directed graph với state management rõ ràng (Supervisor pattern). OpenVINO là runtime duy nhất tối ưu cho Intel NPU, cho phép chạy LLM inference mà không cần GPU discrete. | |

### 2.4. Frontend: Next.js + AG Grid + TradingView Lightweight Charts

| Tiêu chí | Lựa chọn | Lý do |
|:---|:---|:---|
| **Framework** | Next.js (App Router, React 19) | Server Components cho initial load, Client Components cho real-time WebSocket. Persistent layouts tránh re-render khi chuyển view. |
| **Data Grid** | AG Grid Enterprise | DOM virtualization — render chỉ viewport rows. Cell-level transaction update ở 60fps. Pivot/Master-Detail cho phân tích đa chiều. |
| **Charting** | TradingView Lightweight Charts | HTML5 Canvas (không SVG) — zero reflow/repaint overhead. Custom overlay API cho Technical/Risk Agent markers. |
| **UI System** | Shadcn UI + Tailwind CSS | High-density design, Dark Mode mặc định (Slate/Zinc palette). Component-level tree-shaking. |

---

## 3. SYSTEM TOPOGRAPHY — DATA FLOW

### 3.1. Tổng quan luồng dữ liệu End-to-End

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
│  │  • WebSocket client (async) nhận market ticks                      │    │
│  │  • In-memory buffer (dict/deque) giữ latest price per symbol       │    │
│  │  • Batch writer: flush buffer → DuckDB mỗi 1s                     │    │
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

### 3.2. Chi tiết luồng xử lý theo từng phase

**Phase 1 — Data Ingestion (Continuous)**
1. `Data Agent` mở persistent WebSocket connection tới SSI FastConnect.
2. Mỗi tick message được deserialize, validate (Pydantic V2 — Rust core), và ghi vào in-memory buffer (Python `dict` keyed by symbol).
3. Background task flush buffer vào DuckDB mỗi 1 giây (batch insert ~500-2000 rows/batch). Đồng thời ghi Parquet file partitioned theo ngày.

**Phase 2 — Analysis (Event-driven + Periodic)**
4. `Screener Agent` chạy SQL vectorized queries trên DuckDB mỗi 30s–60s, tính toán chỉ báo kỹ thuật trên toàn thị trường. Output: Dynamic Watchlist.
5. `Technical Agent` nhận trigger khi có symbol vào watchlist hoặc theo schedule. Chạy `pandas-ta` cho scoring, `PyPortfolioOpt` cho portfolio rebalancing. Đẩy logic nặng xuống DuckDB SQL (ASOF JOIN, window functions).
6. `Fundamental Agent` lấy tin tức từ Vnstock, đóng gói thành prompt, gửi vào NPU qua OpenVINO runtime. Nhận lại AI Insight (natural language analysis).
7. `Risk Agent` chạy song song, validate mọi signal/order trước khi phát ra. Tính VaR từ historical data trong DuckDB.

**Phase 3 — Delivery (Real-time)**
8. `Supervisor Agent` (LangGraph) tổng hợp output từ tất cả agent, resolve conflicts, tạo unified signal.
9. FastAPI WebSocket server stream kết quả về frontend: JSON cho signals/insights, MessagePack cho high-frequency data.
10. Next.js Client Components nhận data, cập nhật AG Grid (cell-level transaction update), vẽ overlay lên TradingView Charts, refresh Portfolio Dashboard.

---

## 4. HARDWARE UTILIZATION — RESOURCE ALLOCATION PER AGENT

### 4.1. Intel Core Ultra 7 256V — Resource Map

Lunar Lake cung cấp 3 compute domains:

| Domain | Specs (Core Ultra 7 256V) | Đặc tính tối ưu |
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

### 4.3. Chiến lược phân bổ chi tiết

#### CPU — Phân chia P-core / E-core

- **E-cores (Efficiency):** Dành cho các tác vụ I/O-bound chạy liên tục — `Data Agent` (WebSocket listener), `Supervisor Agent` (state routing), `Screener Agent` (SQL dispatch). Các tác vụ này cần throughput ổn định nhưng không cần single-thread performance cao. E-cores tiêu thụ ít điện, phù hợp cho workload always-on.
- **P-cores (Performance):** Dành cho burst compute — `Technical Agent` khi chạy portfolio optimization (SciPy solver), `Risk Agent` khi tính VaR Monte Carlo simulation. Các tác vụ này cần peak single-thread IPC cao nhưng chỉ chạy theo event/schedule.

**Cơ chế:** Sử dụng OS thread affinity (`taskset` trên Linux, `SetThreadAffinityMask` trên Windows) hoặc Python `os.sched_setaffinity()` để pin agent threads vào core groups phù hợp. DuckDB tự quản lý thread pool nội bộ, tận dụng tất cả available cores khi chạy query.

#### NPU — Dedicated cho LLM Inference

- **Exclusive workload:** `Fundamental Agent` là consumer duy nhất của NPU.
- **Pipeline:** Tokenization (CPU) → Model forward pass (NPU via OpenVINO) → Detokenization (CPU).
- **Model config:** Phi-3-mini-4k-instruct (INT4, ~2.2GB) hoặc Llama-3-8B (INT4, ~4.5GB). Batch size = 1 (single request at a time, phù hợp single-user).
- **Throughput target:** ~15-30 tokens/second (INT4 on 48 TOPS NPU) — đủ để generate 1 đoạn AI Insight (~200 tokens) trong ~7-13 giây.
- **Power profile:** NPU tiêu thụ ~5-10W khi active, ~0W khi idle. Không ảnh hưởng thermal budget của CPU/GPU.

#### GPU (Intel Arc iGPU) — Visualization + Optional Compute

- **Primary role:** Browser rendering — TradingView Canvas 2D, AG Grid DOM compositing, CSS animations. Đây là workload tự nhiên của GPU trong mọi hệ thống desktop.
- **Secondary role (optional):** Nếu cần tăng tốc matrix operations cho `Technical Agent` (large-scale covariance matrix, Monte Carlo), có thể sử dụng Intel oneAPI/SYCL để offload sang GPU. Tuy nhiên, với quy mô thị trường Việt Nam (~1,800 mã), CPU P-cores đủ xử lý.
- **Không dùng GPU cho LLM:** NPU hiệu quả hơn GPU integrated cho inference workload sustained (tokens/watt cao hơn).

### 4.4. Thermal & Power Budget (Ước tính phiên giao dịch)

| Trạng thái | CPU | NPU | GPU | Tổng TDP |
|:---|:---|:---|:---|:---|
| **Idle** (ngoài giờ giao dịch) | ~5W (E-cores only) | 0W | ~2W (desktop render) | ~7W |
| **Normal** (phiên giao dịch, data streaming) | ~12W (E-cores active, P-cores boost occasional) | 0-5W (on-demand inference) | ~3W (charts updating) | ~15-20W |
| **Peak** (portfolio rebalance + AI analysis + full market scan) | ~25W (all cores boost) | ~10W (sustained inference) | ~5W (heavy chart render) | ~40W |

Tất cả trạng thái đều nằm trong PBP 30W của Lunar Lake, đảm bảo hệ thống chạy ổn định trên laptop không cần nguồn ngoài trong thời gian ngắn, hoặc chạy liên tục khi cắm nguồn.

---

## 5. KEY ARCHITECTURAL DECISIONS (ADR Summary)

| # | Decision | Rationale | Trade-off |
|:---|:---|:---|:---|
| ADR-001 | In-process DB (DuckDB) thay vì client-server DB | Zero network latency, zero ops overhead | Single-writer, không scale multi-user |
| ADR-002 | NPU inference thay vì Cloud LLM API | Privacy, zero cost, low latency | Model capability giới hạn (≤8B params) |
| ADR-003 | Monorepo + `uv` workspaces | Shared types, atomic refactoring, fast CI | Cần discipline trong module boundaries |
| ADR-004 | WebSocket-first (không REST polling) | Real-time data push, lower overhead | Phức tạp hơn trong error handling/reconnection |
| ADR-005 | Parquet partitioned storage | Compression, direct scan, time-travel queries | Không phù hợp cho random point lookups |

---

*Document generated for internal technical review. Subject to revision as implementation progresses.*
