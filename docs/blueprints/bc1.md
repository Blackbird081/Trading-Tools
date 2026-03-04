Below is the complete summary report (Final Report), compiled based on the standard structure of Report 2 ("Upgrading Financial System Architecture") and integrating technical details, algorithms, and source code from Report 1 ("Consulting on building a securities Web App").

The content is guaranteed to retain 100% of the important information from both reports, logically rearranged to form a unified whole: **Enterprise algorithmic trading system on Hybrid AI & Intel Core Ultra platform.**

---

# IN-DEPTH RESEARCH REPORT: ARCHITECTURE OF NEW GENERATION MULTI-TASK ALGORITHM TRADING SYSTEM (ENTERPRISE EDITION) & IMPLEMENTATION ON HYBRID AI PLATFORM

## EXECUTIVE OVERVIEW AND STRATEGIC VISION

### 1.1. Context and Paradigm Shift
In the era of digital finance, the lines between institutional trading and professional individuals are blurring. However, current systems often trade off between a beautiful interface (GUI) and processing depth. This report proposes a reference architecture for a "Make-in-Vietnam" trading platform, which breaks the above trade-offs by incorporating:
1. **Enterprise Experience:** GUI is considered the "core product", equivalent to Bloomberg Terminal but running on the modern Web.
2. **Hybrid AI Power:** Leverage the NPU of the Intel Core Ultra chip (Lunar Lake series) to run local AI combined with cloud data.
3. **Multi-Agent System (MAS):** Specialized AI agents coordinate real-time data processing.

### 1.2. Core Goals
This "Digital Advisor" and Automated Trading system is capable of:
* **Deep Linking:** Retrieve real-time asset portfolio from securities companies (SSI, DNSE).
* **Real-time processing:** Analyze market data streams with low latency using DuckDB and WebSockets.
* **Edge AI:** Run large language models (LLM) locally on Intel Core Ultra NPUs.
* **Quantitative Algorithm:** Combines Technical Analysis and Modern Portfolio Theory (MPT).

---

## CHAPTER 1: TECHNOLOGY PILLARS AND HYBRID ARCHITECTURE

To realize the vision, the choice of technology stack is based on performance and scalability.

### 1.1. Tech Stack

|Ingredient|Technology selection|Strategic reasons|
| :--- | :--- | :--- |
|**Hardware**| **Intel Core Ultra 7 256V (Lunar Lake)** |Leverage the 48 TOPS NPU to run AI locally, save power, and secure data.|
| **Frontend (GUI)** | **Next.js (React 19) + AG Grid Enterprise** |Render thousands of lines of data/second; Server Components optimize page loading; Modular architecture.|
|**Visualization**| **TradingView Lightweight Charts** |Use HTML5 Canvas instead of SVG, optimized for high-frequency data ticks, with almost zero latency.|
| **Backend API** | **FastAPI (Python)** |Fastest framework, asynchronous support (asyncio), tightly integrated with the AI ​​ecosystem.|
|**Package Management**| **uv (Astral)** |Replace pip/poetry. Written in Rust, installation speed is 10-100 times faster, supports Workspaces for monorepo.|
|**Database**| **DuckDB** |Embedded analytics DB (in-process OLAP), replacing TimescaleDB/SQLite, allows vectorized queries on tick data right in RAM.|
|**Artificial Intelligence**| **LangGraph + OpenVINO** |Multi-Agent system orchestration and optimization of AI models running on Intel NPUs.|

### 1.2. Hybrid Cloud-Edge Architecture
The system operates according to a Hybrid model to optimize resources:
* **Cloud (API CTCK & Market Data):** Bound I/O tasks such as getting realtime prices, synchronizing catalogs from SSI/Vnstock.
* **Edge (Local NPU - Intel Core Ultra):** Compute bound and AI Inference tasks run locally. Running Local LLM on NPU provides absolute security of financial data and no API token costs.

---

## CHAPTER 2: FRONTEND ARCHITECTURE - ENTERPRISE STANDARD EXPERIENCE

Prerequisite: "GUI is the most important element". Frontend is built independently, communicating with Backend via WebSockets.

### 2.1. Next.js Platform and Render Strategy
Use **Next.js (App Router)** to deliver enterprise-grade experiences:
* **Server Components:** Handles the App Shell, layout, and initial authentication.
* **Client Components:** Contains the actual trading logic (Price List, Chart, Order Book) to maintain a persistent WebSocket connection.
* **Persistent Layouts:** Navigation bars and "pinned" widgets are not re-rendered when switching pages (e.g. from "Screener" to "Portfolio").

### 2.2. Data Grid System: AG Grid Enterprise
* **DOM virtualization:** Only renders the currently displayed lines (viewport), ensuring smoothness even though the Watchlist has 2,000 codes.
* **Transaction Update:** Update cell level data in batches (batch update) matching the screen scanning frequency (60fps).
* **Master-Detail & Pivot:** Allows clicking on a stock code to open a detailed panel (mini chart, basic index) or rotate data by industry/risk group.

### 2.3. Visualization: TradingView Lightweight Charts & Custom Overlays
Use HTML5 Canvas technology to draw candlestick charts and technical indicators without consuming CPU resources (reflow/repaint) like SVG.
* **Custom Overlays:**
* *Technical Agent:* Automatically draw trendlines and key points of the "Head-Shoulders" model.
* *Risk Agent:* Displays dynamic Stop-loss/Take-profit levels, allowing drag and drop directly on the chart.
* *Signal Markers:* Buy/Sell arrow with tooltip explaining the reason (e.g. "Oversold RSI + Divergence").

### 2.4. UI/UX Interface
* **Shadcn UI + Tailwind CSS:** Designed in "High Density" style.
* **Dark Mode:** Default dark mode, high contrast (Slate/Zinc palette).
* **Command Palette (Ctrl+K):** Control center, allowing to enter text commands (for example: "Buy FPT 1000 price 98.5" or "Show MA 200").

---

## CHAPTER 3: BACKEND INFRASTRUCTURE & DATA ENGINE (DUCKDB)

The backend is completely rebuilt on a modern Python platform, optimized for high speed.

### 3.1. Package and Environment Management with uv
Use **uv** (written in Rust) instead of pip/poetry.
* **Speed:** Install and resolve dependencies 10-100 times faster.
* **Monorepo Architecture:** Uses uv's Workspaces feature to organize source code into separate packages (`/core`, `/connectors`, `/analytics`, `/agents`) but manage them together in one repo.

### 3.2. FastAPI and Asynchronous Architecture
* **Asyncio:** Handles thousands of concurrent WebSocket connections.
* **Background Tasks:** Push heavy tasks (running NPU Inference, optimizing Portfolio) to the background, giving instant feedback to the UI.
* **Pydantic V2:** Validate JSON data from the exchange extremely fast thanks to the core written in Rust.

### 3.3. Data Engine: DuckDB (Replaces TimescaleDB)
DuckDB works as an embedded OLAP DB, eliminating network latency.
* **Columnar storage:** Compresses Tick data extremely well.
* **Partitioning:** Store Parquet files by Day/Month, query directly without loading the entire file into RAM.
* **ASOF JOIN technique:** "Weapon" of finance. Pair the Order table and Price table based on the most recent time (for example: Find the market price at the exact millisecond the sell order was sent) to calculate PnL and Backtesting super fast.
* **Vectorized Analysis:** Agents push computational logic down to DuckDB (SQL) instead of looping in Python.

---

## CHAPTER 4: MULTI-AGENT SYSTEM & ALGORITHM

The AI ​​system ("The Brain") is divided into specialized Agents, coordinated through the **LangGraph** framework according to the Supervisor model.

### 4.1. Data Agent (Market Sensor)
* **Task:** Connect WebSocket to SSI/Vnstock, standardize data.
*   **Technique:**
* Use Python's `websockets` library (async).
* Buffer management to write data to DuckDB in batch inserts every 1 second.
* In-Memory data management (Redis or Python Dict) for the latest prices for extremely fast retrieval, without querying the DB for every tick.

### 4.2. Screener Agent
* **Task:** Scan the entire market for opportunities.
*   **Technique:**
* Use `vnstock.stock_screening()` for basic filtering (EPS up, PE down).
* Periodically enable vectorized SQL queries on DuckDB to calculate technical indicators.
* The returned result is "Dynamic Watchlist" pushed to the Frontend.

### 4.3. Technical Analysis Agent
This is where the quantitative algorithms from Report 1 apply.
* **Tools:** Libraries `pandas-ta` and `PyPortfolioOpt`.
* **Algorithm 1: Portfolio Optimization (Portfolio Rebalancing):**
* Based on Modern Portfolio Theory (MPT).
* Use `PyPortfolioOpt` to find the efficient frontier.
* Handle the even lot constraint (Lot Size 100) using the `DiscreteAllocation` module.
* **Algorithm 2: Technical Scoring:**
* 10 scale scoring system based on: RSI (Overbought/Oversold), MACD (Cut up/down), Bollinger Bands, Trend (MA50/MA200).
* **Resolution:** Score > 8 (BUY NEW), < -5 (SELL), -5 to 5 (HOLD).

### 4.4. Fundamental Analysis Agent
Take advantage of Intel Core Ultra hardware.
* **Technology:** **OpenVINO™ GenAI**.
*   **Deployment:**
* Run the quantized **Phi-3-mini** or **Llama-3-8B** model (INT4) on the NPU.
* **Process:** Get news from vnstock -> Send to NPU with technical indicators -> NPU returns natural analysis text ("AI Insight").
* **Benefits:** No data sharing, high inference speed, no cost.

### 4.5. Risk Management Agent
* **Task:** Middleware controls all orders.
*   **Logic:**
* **Kill Switch:** Emergency stop button on the interface.
* **Safety Checks:** Do not buy more than 20% NAV/order, set price does not exceed ceiling/floor.
* **VaR (Value at Risk):** Calculate real-time risk using historical data in DuckDB.

---

## CHAPTER 5: VIETNAM MARKET DATA INTEGRATION (SSI & DNSE)

The system is specifically designed for the Vietnamese market (T+2.5).

### 5.1. Brokerage Infrastructure Analysis
* **"Two Pillars" Strategy:**
1. **SSI (FastConnect Trading API):** Used for trading and getting the most accurate Portfolio data. Stable, standard.
2. **Vnstock (Wrapper):** Used as a supplementary data source (Price History, News, Data Mining) to replace expensive data packages.

### 5.2. SSI Connection Deployment Details (Implementation)
Different from regular API, SSI requires RSA digital signing.
* **Authentication process (Handshake):**
1. Create a RSA key pair (Private/Public Key). Upload Public Key to iBoard SSI.
2. Use the `pycryptodome` library to sign requests with Private Key.
3. Get Access Token (JWT) to maintain session.
* **Portfolio Sync:**
* Call endpoint `stockPosition`.
* **Data Normalization:** Normalize raw data from SSI to internal structure (Mapping fields `onHand`, `sellableQty`, `avgPrice`, `marketPrice`).
* **Handling T+2.5:** Logic distinguishes "CashBal" and "Purchase Power" (purchasingPower) to avoid Call Margin.

### 5.3. DNSE Connection (Entrade X)
* Leverage DNSE's modern RESTful API for tasks that require high speed or transaction fees.
* Note the Token/Refresh Token management mechanism to avoid losing connection.

---

## CHAPTER 6: IMPLEMENTATION ROADMAP & CONCLUSION

### 6.1. Development Roadmap (12 Weeks)
1. **Phase 1 (Weeks 1-4):** Set up `uv` workspace infrastructure, connect DuckDB. Build Data Agent connecting SSI (RSA authentication) and Vnstock.
2. **Phase 2 (Weeks 5-8):** Next.js Frontend Development with AG Grid and TradingView Charts. Display realtime data via WebSocket.
3. **Phase 3 (Weeks 9-10):** Develop algorithmic agents (Screener, Tech Analysis with PyPortfolioOpt/Pandas-TA). Integrated ASOF JOIN logic.
4. **Phase 4 (Weeks 11-12):** Integrate Fundamental Agent (OpenVINO GenAI on NPU). Complete Risk Agent, GUI Dark Mode, Command Palette and Testing.

### 6.2. Conclude
The report presented a comprehensive architecture that combines advanced personal hardware power (Intel Core Ultra) with Enterprise software architecture (Next.js, DuckDB, Multi-Agent). This is not just a trading tool, but a technological competitive advantage, allowing investors to maximize market opportunities with the powerful support of AI and outstanding processing speed.

---
*End of report.*
