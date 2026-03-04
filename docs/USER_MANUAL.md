# User Manual — Algo Trading System

**Document version:** 1.0
**Update date:** 2026-02-10
**Target:** Operators, developers, technical traders

---

## Table of contents

1. [Introduction & Overview](#1-introduction--overview)
2. [System Requirements & First Time Installation](#2-system-requirements-first-time-installation)
3. [Environment configuration](#3-environment-configuration)
4. [Run program](#4-run-program)
5. [User Interface — Basic](#5-user-interface-basic)
6. [User Interface — Advanced](#6-user-interface-advanced)
7. [API & Integration](#7-api--integration)
8. [Pipeline & dry-run / live mode](#8-pipeline--dry-run-mode--live)
9. [Troubleshooting](#9-troubleshooting)
10. [Security & Recommendation](#10-security--recommendation)

---

## 1. Introduction & Overview

### 1.1 What is a system?

**Algo Trading Platform** is an automated trading system that combines:

- **Real-time market data** from SSI FastConnect (WebSocket)
- **Multi-agent pipeline** (Screener → Technical → Risk → Executor) runs on LangGraph
- **AI analysis on NPU** (OpenVINO, Phi-3 INT4) for basic insight
- **Place orders with idempotency** via SSI/DNSE, with risk checks (T+2.5, price band, lot size, VaR…)
- **Terminal interface** Dark Mode: AG Grid price list, TradingView candlestick chart, Command Palette (Ctrl+K)

### 1.2 General architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js 15, http://localhost:3000)                    │
│ • Dashboard: price list + candlestick chart + signal overlay │
│  • Portfolio / Orders / Screener / Settings                     │
│  • WebSocket client ←→ Backend /ws/market                        │
└───────────────────────────────┬───────────────────────────────┘
                                 │
┌───────────────────────────────▼───────────────────────────────┐
│  BACKEND (FastAPI, http://localhost:8000)                       │
│  • /api/health, /api/portfolio                                 │
│  • WebSocket /ws/market (broadcast ticks, signals, positions)   │
│  • Data Agent: SSI WS → buffer → DuckDB + Parquet              │
│  • Agent Pipeline: Screener → Technical → Risk → Executor      │
│  • OMS: place_order (idempotency), OrderStatusSynchronizer     │
└───────────────────────────────┬───────────────────────────────┘
                                 │
┌───────────────────────────────▼───────────────────────────────┐
│ DATA & EXTERNALS │
│  • DuckDB (ticks, orders, news_embeddings)                      │
│  • SSI: auth, market WS, broker, portfolio                     │
│  • Vnstock: history, screener, news (optional)                  │
│ • OpenVINO: INT4 model on NPU/GPU/CPU │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Terms you need to know

|Terminology|Meaning|
|:---|:---|
| **Tick** |Real-time price/volume data in real time|
| **Pipeline** |Agent chain: Screener → Technical → Risk → Executor (can add Fundamental)|
| **Dry-run** |Run pipeline and create execution plan but **do not** send orders to the exchange|
| **Live** |Send real orders via broker (SSI/DNSE) with idempotency|
| **Idempotency** |The same "order intent" (idempotency key) only creates **one** order on the exchange, avoiding duplicate orders|
| **NAV** |Total net assets (cash + portfolio value)|
| **T+2.5** |Vietnamese securities settlement date; You can only sell after the shares have been returned to your account|

---

## 2. System Requirements & First Time Installation

### 2.1 Hardware & software requirements

**Obligatory:**

- **Python 3.12+** — Test: `python --version`
- **uv** — Python dependency management: [https://astral.sh/uv/install](https://astral.sh/uv/install)
- **Node.js 20+** — Test: `node --version`
- **pnpm 9+** — Install: `npm install -g pnpm`
- **Git 2.40+**

**Recommended:**

- **Intel Core Ultra (NPU)** — To run local AI model (Phi-3 INT4); Can still run without NPU (CPU fallback)
- **RAM 16 GB+** — DuckDB + buffer + (optional) OpenVINO model
- **Drive** — Several GB for data (Parquet, DuckDB, model if used)

### 2.2 First Time Installation (Windows / Linux / macOS)

**Step 1: Clone and go to project folder**

```bash
git clone <repo-url> algo-trading
cd algo-trading
```

**Step 2: Install Python dependencies (4 packages: core, adapters, agents, interface)**

```bash
uv sync
```

**Step 3: Check the Python toolchain (optional but recommended)**

```bash
uv run ruff check packages/ tests/
uv run mypy packages/ --strict
uv run pytest tests/ -v --tb=short
```

**Step 4: Install Frontend**

```bash
cd frontend
pnpm install
cd ..
```

**Step 5: Check Frontend (optional)**

```bash
cd frontend
pnpm tsc --noEmit
pnpm vitest run
cd ..
```

**Step 6: Create environment configuration file**

```bash
cp .env.example .env
```

Then open `.env` and fill in the SSI information (see [Section 3](#3-environment-configuration)).

**Step 7: Create data folder**

```bash
# Windows (PowerShell)
New-Item -ItemType Directory -Force -Path data\models, data\parquet, data\prompts, data\secrets

# Linux / macOS
mkdir -p data/{models,parquet,prompts,secrets}
```

After this step you are ready to [run the program](#4-run-program).

---

## 3. Configure the environment

File `.env` is located in the **root directory** of the repo (`algo-trading/`). **Do not commit file `.env`** (already in `.gitignore`).

### 3.1 SSI FastConnect variable (required if using SSI)

|Variable|Describe|For example|
|:---|:---|:---|
| `SSI_CONSUMER_ID` |Consumer ID provided by SSI|Chain provided by SSI|
| `SSI_CONSUMER_SECRET` | Consumer Secret |Secret chain|
| `SSI_PRIVATE_KEY_PEM` |Private key RSA (can be Base64)|Content or base64 of the .pem file|
| `SSI_PRIVATE_KEY_PASSPHRASE` |Private key decryption password|Passphrase string|

How to get: register FastConnect with SSI, create application, get Consumer ID/Secret and RSA key pair.

### 3.2 DNSE Entrade variable (if using DNSE)

|Variable|Describe|
|:---|:---|
| `DNSE_USERNAME` |Username Entrade|
| `DNSE_PASSWORD` |Password|

### 3.3 DuckDB

|Variable|Describe|Default|
|:---|:---|:---|
| `DUCKDB_PATH` |DuckDB file path| `data/trading.duckdb` |

### 3.4 OpenVINO (AI local)

|Variable|Describe|Default|
|:---|:---|:---|
| `OPENVINO_MODEL_PATH` |The folder contains model INT4| `data/models/` |
| `OPENVINO_DEVICE` |Device: NPU/GPU/CPU| `NPU` |

Without the NPU, the system automatically fallsback to the CPU; model must be in `OPENVINO_MODEL_PATH` (e.g. `data/models/phi-3-mini-int4/`).

### 3.5 Log

|Variable|Describe|Default|
|:---|:---|:---|
| `LOG_LEVEL` | DEBUG / INFO / WARNING / ERROR | `INFO` |
| `LOG_FORMAT` | text / json | `json` |

---

## 4. Run the program

### 4.1 Running Backend (API + WebSocket)

From **root directory** `algo-trading/`:

```bash
uv run python -m interface.cli
```

- Server running at: **http://localhost:8000**
- API docs (Swagger): **http://localhost:8000/docs**
- Health: **http://localhost:8000/api/health**
- WebSocket market: **ws://localhost:8000/ws/market**

Turn off: press `Ctrl+C` in terminal.

### 4.2 Running Frontend (web interface)

Open **second terminal**, go to frontend folder:

```bash
cd frontend
pnpm dev
```

- The application runs at: **http://localhost:3000**
- Hot reload when editing code (Turbopack)

Off: `Ctrl+C`.

### 4.3 Concurrent running (development)

1. Terminal 1: `uv run python -m interface.cli`
2. Terminal 2: `cd frontend && pnpm dev`
3. Open browser: **http://localhost:3000**

Frontend connects WebSocket to `ws://localhost:8000/ws/market` (configured in WebSocket provider). Make sure the backend runs before or at the same time to receive real-time data.

### 4.4 Build production (Frontend)

```bash
cd frontend
pnpm build
pnpm start
```

- `pnpm build`: static build, output in `.next/`
- `pnpm start`: run Next.js server (default port 3000)

### 4.5 Running tests (Backend)

```bash
uv run pytest tests/ -v --tb=short
```

Run with coverage:

```bash
uv run pytest tests/ --cov=packages --cov-report=term-missing
```

### 4.6 Running tests (Frontend)

```bash
cd frontend
pnpm vitest run
```

---

## 5. User Interface — Basic

### 5.1 Layout chung

- **Left sidebar:** Navigation (Dashboard, Portfolio, Screener, Orders, Settings).
- **Top bar:** Displays the currently selected code, price, % change; button that opens the Command Palette (Ctrl+K).
- **Main content area:** Varies by page.

### 5.2 Dashboard (Home)

- **Price Board:** Columns: Stock Code, Price, Change, %, Volume. Data updates real-time via WebSocket. Click on a line to select the code and view the chart.
- **Trading Chart:** Displays candles and (if any) BUY/SELL signals from the pipeline. The code displayed is the code currently selected on the price list.

### 5.3 Portfolio

- **Asset overview:** NAV, cash (from store; can synchronize from API/WebSocket).
- **Positions table:** Stock code, volume, average price, market price, profit/loss, % profit/loss. Data from `portfolio-store`.

### 5.4 Orders

- **Order form:** Select BUY/SELL, code (according to the currently selected code), volume, price. Send command (when OMS is connected).
- **Command history:** Command table with status (PENDING, MATCHED, REJECTED, ...). Data from `order-store`.

### 5.5 Screener

- Screener results page from pipeline (list of codes that pass basic filter + volume spike). Content is scalable with backend integration.

### 5.6 Settings

- Connection status (WebSocket, API), API key / SSI configuration notes. Additional options can be extended.

### 5.7 Command Palette (Ctrl+K)

- **Shortcut:** `Ctrl+K` (Windows/Linux) or `Cmd+K` (macOS).
- **Function:**
- Navigation: type `/dashboard`, `/portfolio`, `/orders`, `/screener`, `/settings`.
- Select code: type 3-letter code (eg `FPT`, `VNM`) to set as the viewing code.
- Transaction order (parse): `BUY FPT 1000`, `BUY FPT 1000 PRICE 98.5`, `SELL VNM 500`. The system parses and can convert to order form or order API (depending on integration).

Close palette: `Escape` or click out.

---

## 6. User Interface — Advanced

### 6.1 Price list (AG Grid)

- Update by tick: WebSocket data is collected by frame and applied via `applyTransactionAsync` to reduce re-rendering, smooth with multiple codes.
- Click row → set active code → chart and (if available) command form to use that code.
- Color: blue (increase), red (decrease), yellow/neutral (ceiling/floor/constant) according to logic `PriceCell`.

### 6.2 Candlestick Charts (TradingView Lightweight Charts)

- Candles according to candle data from the store; Real-time updates when there are new candles.
- Signal overlay: marks BUY/SELL from the agent (if the backend sends via WebSocket).
- Responsive: automatically resizes according to the frame.

### 6.3 WebSocket and Store

- **WebSocket:** Connect to `ws://localhost:8000/ws/market`. When the connection is lost, the provider can reconnect itself (logic in `ws-provider.tsx`).
- **Stores (Zustand):**
  - `market-store`: ticks, candles.
  - `portfolio-store`: positions, cash, nav, purchasing power.
- `signal-store`: list of signals (BUY/SELL) from pipeline, limited to 100 records.
- `order-store`: command placed / status updated.
- `ui-store`: currently selected code, Command Palette open status, sidebar collapsed.

Messages from WebSocket are mapped according to `type` (tick, candle, signal, position, ...) and pushed to the corresponding store.

### 6.4 Hook `useMarketStream`

- Subscribe `latestTick` from market store, batch update and apply to AG Grid with `requestAnimationFrame` to achieve ~60fps when there are many ticks.

---

## 7. APIs & Integrations

### 7.1 REST API (FastAPI)

- **Base URL:** `http://localhost:8000`
- **Interactive document:** `http://localhost:8000/docs`

**Main Endpoints:**

| Method | Path |Describe|
|:---|:---|:---|
| GET | `/api/health` |System status (healthy/unhealthy)|
| GET | `/api/portfolio` |(If any) Portfolio information|

Can extend endpoint orders, screeners, pipeline triggers in the code.

### 7.2 WebSocket `/ws/market`

- **URL:** `ws://localhost:8000/ws/market`
- **Message protocol:** JSON, with fields `type` and `payload`.

Example payload (illustration):

- **Tick:** `{ "type": "tick", "payload": { "symbol": "FPT", "price": 98.5, "change": 1.2, "changePercent": 1.23, "volume": 1500000, "timestamp": 1234567890 } }`
- **Signal:** `{ "type": "signal", "payload": { "id": "...", "symbol": "FPT", "action": "BUY", "confidence": 0.85, "reason": "...", "timestamp": ... } }`
- **Position:** `{ "type": "position", "payload": { "symbol": "FPT", "quantity": 1000, "avgPrice": 95, "marketPrice": 98.5 } }`

The frontend reads `type` and updates the store accordingly.

### 7.3 Call pipeline from code (Python)

The LangGraph pipeline can be called from the runner (see `packages/agents/src/agents/runner.py`). Example to initialize state and run:

```python
from agents.runner import run_trading_pipeline
from decimal import Decimal

initial_state = {
    "dry_run": True,
    "current_nav": Decimal("1000000000"),
    "current_positions": {},
    "purchasing_power": Decimal("500000000"),
    "max_candidates": 10,
    "score_threshold": 5.0,
}
final_state = await run_trading_pipeline(initial_state)
```

Dependencies (screener, technical, risk, executor, tick_repo, broker, ...) need to be injected via `SystemDependencies` or equivalent.

---

## 8. Pipeline & dry-run / live mode

### 8.1 Pipeline flow

1. **Inject context:** run_id, max_candidates, score_threshold, dry_run, …
2. **Screener:** Filter code by fundamental + volume spike → watchlist.
3. **Technical:** Technical points (RSI, MACD, BB, MA) → top_candidates.
4. **Risk:** Check kill switch, NAV, VaR, T+2.5, lot size, ... → approved_trades.
5. **Executor:** Create execution plan; If `dry_run=False` then call broker (idempotency key), if `dry_run=True` then only log, do not send command.
6. **Finalize:** Mark the COMPLETED phase.

Fundamental Agent (AI) can run in parallel/private branch, updating `ai_insights` in state.

### 8.2 Dry-run (safe default)

- `dry_run=True`: Executor **does not** call `broker.place_order`. Only create execution plan and log. Used to test logic, backtest, demo.

### 8.3 Live (place real orders)

- `dry_run=False` and broker configured: Executor calls broker with idempotency key (eg `run_id:symbol:BUY`). Each intent creates only one order on the exchange. Need to configure SSI/DNSE and accept financial risks.

### 8.4 Idempotency

- Each command (or each intent from the pipeline) is assigned an **idempotency key**.
- If the client/pipeline sends the same key, OMS returns the saved command instead of creating a new command → avoids placing duplicate keys when retrying or double-clicking.

---

## 9. Troubleshooting

### 9.1 Backend does not start

- **Missing module error:** Rerun `uv sync` in the root directory.
- **Port 8000 is occupied:** Change the port in `interface/cli.py` (eg `port=8001`) or shut down the process using 8000.
- **Error importing core/adapters/agents:** Make sure to run from the root directory and have `uv sync` (workspace packages installed correctly).

### 9.2 Frontend does not connect data

- Check the backend running at `http://localhost:8000` and `/api/health` returns 200.
- Check WebSocket URL in frontend (default `ws://localhost:8000/ws/market`). If you run the backend on another host/port, you need to change the environment variable or config (eg `NEXT_PUBLIC_WS_URL`).
- Open DevTools → Network → WS: see if the WebSocket connection is successful and if there is a message.

### 9.3 SSI/DNSE auth error

- Check `.env`: `SSI_CONSUMER_ID`, `SSI_CONSUMER_SECRET`, `SSI_PRIVATE_KEY_PEM`, `SSI_PRIVATE_KEY_PASSPHRASE` are correct and do not have extra spaces.
- Private key: correct PEM format (or base64), correct passphrase. If the key saves a file, the adapter can support reading from the file (see `credential_manager`).

### 9.4 OpenVINO/AI is not running

- Model not available: need to export INT4 (see `scripts/quantize_model.py` and OpenVINO doc). Put the model in `OPENVINO_MODEL_PATH` (eg `data/models/phi-3-mini-int4/`).
- No NPU: CPU fallback system; can be slow. Set `OPENVINO_DEVICE=CPU` if you want to be explicit.
- Missing libraries: install `openvino`, `openvino-genai` (or follow Phase 5 instructions). If not installed, Fundamental Agent returns the default content “[AI engine unavailable]”.

### 9.5 Orders do not appear on the exchange/duplicate orders

- Check that `dry_run` has set `False` and that the broker (SSI/DNSE) has been configured and injected into the Executor.
- Idempotency: if you send the same idempotency key twice, the second time you will receive the results of the created command (do not create a new command). Check the “Duplicate order detected” log if there is one.
- Risk rejection: see reason log (kill switch, exceed NAV, exceed sellable qty, exceed price band, lot size not multiple of 100, ...).

### 9.6 Logging and debugging

- Backend: log according to `LOG_LEVEL` and `LOG_FORMAT` in `.env`. `LOG_LEVEL=DEBUG` to see details.
- Frontend: browser console; React DevTools for state (Zustand).
- Pipeline: observability (structured log) records each agent step (run_id, phase, ...) to trace.

---

## 10. Security & Recommendations

### 10.1 Security

- **Do not commit `.env`:** This file contains consumer secret, private key, passphrase. Always in `.gitignore`.
- **Do not hardcode the key in the code** or in the repo. Use environment variables or keyring/secret manager.
- **Private key:** Save in a safe place; can be encrypted with a passphrase and saved in `data/secrets/` (supported in credential manager).
- **HTTPS/WSS in production:** When deploying, use HTTPS for REST and WSS for WebSocket; Configure reverse proxy (nginx, Caddy) and certificate.

### 10.2 Operating recommendations

- **Always start with dry_run=True** when running pipelines with real data; Only turn on live after checking carefully.
- **WebSocket connection monitoring:** If connection is lost during trading hours, tick data may be missing; The system has buffers and reconnection, but there should be a warning when the connection is lost for a long time.
- **Backup data:** The `data/` folder (DuckDB, Parquet, prompts) should be backed up periodically; Do not commit to git.
- **Update dependencies:** Periodically `uv sync` and `pnpm install`; Check for CVEs for critical libraries (auth, broker, crypto).

### 10.3 Limitations and risks

- The system does not replace human investment decisions. Signals and execution are for support purposes only.
- Financial risk: real trading can lead to loss of capital. Only use with acceptable capital and a clear understanding of risk logic (T+2.5, price band, lot size, VaR, kill switch).
- Comply with legal regulations and floor rules (SSI, DNSE, VSD) on automatic transactions and data storage.

---

## Appendix A: Quick commands (Cheat sheet)

|Things to do|Command|
|:---|:---|
|First time installation| `uv sync` → `cd frontend && pnpm install` |
|Run the backend| `uv run python -m interface.cli` |
|Run frontend| `cd frontend && pnpm dev` |
| Build frontend | `cd frontend && pnpm build && pnpm start` |
| Test backend | `uv run pytest tests/ -v --tb=short` |
| Test frontend | `cd frontend && pnpm vitest run` |
| Lint Python | `uv run ruff check packages/ tests/` |
| Type check Python | `uv run mypy packages/ --strict` |
|Open Command Palette|`Ctrl+K` or `Cmd+K`|

---

## Appendix B: Important directory structure

```
algo-trading/
├── .env # Configuration (no commit)
├── .env.example # Environment variable template
├── pyproject.toml          # Workspace Python (uv)
├── packages/
│   ├── core/               # Entity, port, use case
│   ├── adapters/           # SSI, DuckDB, Vnstock, OpenVINO, …
│   ├── agents/             # Screener, Technical, Risk, Executor, Fundamental, Supervisor
│   └── interface/          # FastAPI, WebSocket, CLI
├── frontend/               # Next.js app
│   ├── app/                # Routes, layouts, pages
│   ├── stores/             # Zustand
│   ├── providers/          # WebSocket
│   ├── components/         # Sidebar, TopNav, CommandPalette, PriceCell
│   └── hooks/              # useMarketStream
├── data/                   # DuckDB, Parquet, models, prompts, secrets
├── tests/                  # pytest (unit + integration)
├── scripts/                # quantize_model.py, ci
└── docs/                   # Blueprints, plans, reports, USER_MANUAL.md
```

---

*This document describes the system version according to the Implementation Plan and blueprints 01–06. When features change, USER_MANUAL.md.* should be updated.
