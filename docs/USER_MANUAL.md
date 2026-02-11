# Sổ tay người dùng — Hệ thống Algo Trading

**Phiên bản tài liệu:** 1.0  
**Ngày cập nhật:** 2026-02-10  
**Đối tượng:** Người vận hành, nhà phát triển, trader kỹ thuật

---

## Mục lục

1. [Giới thiệu & Tổng quan](#1-giới-thiệu--tổng-quan)
2. [Yêu cầu hệ thống & Cài đặt lần đầu](#2-yêu-cầu-hệ-thống--cài-đặt-lần-đầu)
3. [Cấu hình môi trường](#3-cấu-hình-môi-trường)
4. [Chạy chương trình](#4-chạy-chương-trình)
5. [Giao diện người dùng — Cơ bản](#5-giao-diện-người-dùng--cơ-bản)
6. [Giao diện người dùng — Nâng cao](#6-giao-diện-người-dùng--nâng-cao)
7. [API & Tích hợp](#7-api--tích-hợp)
8. [Pipeline & Chế độ dry-run / live](#8-pipeline--chế-độ-dry-run--live)
9. [Xử lý sự cố](#9-xử-lý-sự-cố)
10. [Bảo mật & Khuyến nghị](#10-bảo-mật--khuyến-nghị)

---

## 1. Giới thiệu & Tổng quan

### 1.1 Hệ thống là gì?

**Algo Trading Platform** là hệ thống giao dịch tự động kết hợp:

- **Dữ liệu thị trường real-time** từ SSI FastConnect (WebSocket)
- **Pipeline đa agent** (Screener → Technical → Risk → Executor) chạy trên LangGraph
- **Phân tích AI trên NPU** (OpenVINO, Phi-3 INT4) cho insight cơ bản
- **Đặt lệnh có idempotency** qua SSI/DNSE, với kiểm tra rủi ro (T+2.5, price band, lot size, VaR…)
- **Giao diện terminal** Dark Mode: bảng giá AG Grid, biểu đồ nến TradingView, Command Palette (Ctrl+K)

### 1.2 Kiến trúc tổng quan

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND (Next.js 15, http://localhost:3000)                    │
│  • Dashboard: bảng giá + biểu đồ nến + signal overlay           │
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
│  DỮ LIỆU & NGOẠI VIÊN                                           │
│  • DuckDB (ticks, orders, news_embeddings)                      │
│  • SSI: auth, market WS, broker, portfolio                     │
│  • Vnstock: history, screener, news (optional)                  │
│  • OpenVINO: model INT4 trên NPU/GPU/CPU                       │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Thuật ngữ cần biết

| Thuật ngữ | Ý nghĩa |
|:---|:---|
| **Tick** | Dữ liệu giá/khối lượng real-time theo thời gian thực |
| **Pipeline** | Chuỗi agent: Screener → Technical → Risk → Executor (có thể thêm Fundamental) |
| **Dry-run** | Chạy pipeline và tạo execution plan nhưng **không** gửi lệnh lên sàn |
| **Live** | Gửi lệnh thật qua broker (SSI/DNSE) với idempotency |
| **Idempotency** | Cùng một “ý định lệnh” (idempotency key) chỉ tạo **một** lệnh trên sàn, tránh đặt trùng |
| **NAV** | Tổng tài sản ròng (tiền mặt + giá trị danh mục) |
| **T+2.5** | Ngày thanh toán chứng khoán Việt Nam; bán chỉ được sau khi cổ phiếu đã về tài khoản |

---

## 2. Yêu cầu hệ thống & Cài đặt lần đầu

### 2.1 Yêu cầu phần cứng & phần mềm

**Bắt buộc:**

- **Python 3.12+** — Kiểm tra: `python --version`
- **uv** — Quản lý dependency Python: [https://astral.sh/uv/install](https://astral.sh/uv/install)
- **Node.js 20+** — Kiểm tra: `node --version`
- **pnpm 9+** — Cài: `npm install -g pnpm`
- **Git 2.40+**

**Khuyến nghị:**

- **Intel Core Ultra (NPU)** — Để chạy model AI local (Phi-3 INT4); không có NPU vẫn chạy được (CPU fallback)
- **RAM 16 GB+** — DuckDB + buffer + (tuỳ chọn) model OpenVINO
- **Ổ đĩa** — Vài GB cho data (Parquet, DuckDB, model nếu dùng)

### 2.2 Cài đặt lần đầu (Windows / Linux / macOS)

**Bước 1: Clone và vào thư mục dự án**

```bash
git clone <repo-url> algo-trading
cd algo-trading
```

**Bước 2: Cài đặt dependency Python (4 package: core, adapters, agents, interface)**

```bash
uv sync
```

**Bước 3: Kiểm tra toolchain Python (tuỳ chọn nhưng nên chạy)**

```bash
uv run ruff check packages/ tests/
uv run mypy packages/ --strict
uv run pytest tests/ -v --tb=short
```

**Bước 4: Cài đặt Frontend**

```bash
cd frontend
pnpm install
cd ..
```

**Bước 5: Kiểm tra Frontend (tuỳ chọn)**

```bash
cd frontend
pnpm tsc --noEmit
pnpm vitest run
cd ..
```

**Bước 6: Tạo file cấu hình môi trường**

```bash
cp .env.example .env
```

Sau đó mở `.env` và điền thông tin SSI (xem [Mục 3](#3-cấu-hình-môi-trường)).

**Bước 7: Tạo thư mục dữ liệu**

```bash
# Windows (PowerShell)
New-Item -ItemType Directory -Force -Path data\models, data\parquet, data\prompts, data\secrets

# Linux / macOS
mkdir -p data/{models,parquet,prompts,secrets}
```

Sau bước này bạn đã sẵn sàng [chạy chương trình](#4-chạy-chương-trình).

---

## 3. Cấu hình môi trường

File `.env` nằm ở **thư mục gốc** của repo (`algo-trading/`). **Không được commit file `.env`** (đã có trong `.gitignore`).

### 3.1 Biến SSI FastConnect (bắt buộc nếu dùng SSI)

| Biến | Mô tả | Ví dụ |
|:---|:---|:---|
| `SSI_CONSUMER_ID` | Consumer ID do SSI cấp | Chuỗi do SSI cung cấp |
| `SSI_CONSUMER_SECRET` | Consumer Secret | Chuỗi bí mật |
| `SSI_PRIVATE_KEY_PEM` | Private key RSA (có thể Base64) | Nội dung hoặc base64 của file .pem |
| `SSI_PRIVATE_KEY_PASSPHRASE` | Mật khẩu giải mã private key | Chuỗi passphrase |

Cách lấy: đăng ký FastConnect với SSI, tạo ứng dụng, lấy Consumer ID/Secret và cặp key RSA.

### 3.2 Biến DNSE Entrade (nếu dùng DNSE)

| Biến | Mô tả |
|:---|:---|
| `DNSE_USERNAME` | Tên đăng nhập Entrade |
| `DNSE_PASSWORD` | Mật khẩu |

### 3.3 DuckDB

| Biến | Mô tả | Mặc định |
|:---|:---|:---|
| `DUCKDB_PATH` | Đường dẫn file DuckDB | `data/trading.duckdb` |

### 3.4 OpenVINO (AI local)

| Biến | Mô tả | Mặc định |
|:---|:---|:---|
| `OPENVINO_MODEL_PATH` | Thư mục chứa model INT4 | `data/models/` |
| `OPENVINO_DEVICE` | Thiết bị: NPU / GPU / CPU | `NPU` |

Nếu không có NPU, hệ thống tự fallback CPU; model phải nằm trong `OPENVINO_MODEL_PATH` (ví dụ `data/models/phi-3-mini-int4/`).

### 3.5 Log

| Biến | Mô tả | Mặc định |
|:---|:---|:---|
| `LOG_LEVEL` | DEBUG / INFO / WARNING / ERROR | `INFO` |
| `LOG_FORMAT` | text / json | `json` |

---

## 4. Chạy chương trình

### 4.1 Chạy Backend (API + WebSocket)

Từ **thư mục gốc** `algo-trading/`:

```bash
uv run python -m interface.cli
```

- Server chạy tại: **http://localhost:8000**
- API docs (Swagger): **http://localhost:8000/docs**
- Health: **http://localhost:8000/api/health**
- WebSocket market: **ws://localhost:8000/ws/market**

Tắt: nhấn `Ctrl+C` trong terminal.

### 4.2 Chạy Frontend (giao diện web)

Mở **terminal thứ hai**, vào thư mục frontend:

```bash
cd frontend
pnpm dev
```

- Ứng dụng chạy tại: **http://localhost:3000**
- Hot reload khi sửa code (Turbopack)

Tắt: `Ctrl+C`.

### 4.3 Chạy đồng thời (development)

1. Terminal 1: `uv run python -m interface.cli`
2. Terminal 2: `cd frontend && pnpm dev`
3. Mở trình duyệt: **http://localhost:3000**

Frontend kết nối WebSocket tới `ws://localhost:8000/ws/market` (cấu hình trong WebSocket provider). Đảm bảo backend chạy trước hoặc cùng lúc để nhận dữ liệu real-time.

### 4.4 Build production (Frontend)

```bash
cd frontend
pnpm build
pnpm start
```

- `pnpm build`: build tĩnh, output trong `.next/`
- `pnpm start`: chạy server Next.js (mặc định port 3000)

### 4.5 Chạy test (Backend)

```bash
uv run pytest tests/ -v --tb=short
```

Chạy với coverage:

```bash
uv run pytest tests/ --cov=packages --cov-report=term-missing
```

### 4.6 Chạy test (Frontend)

```bash
cd frontend
pnpm vitest run
```

---

## 5. Giao diện người dùng — Cơ bản

### 5.1 Layout chung

- **Sidebar trái:** Điều hướng (Dashboard, Portfolio, Screener, Orders, Settings).
- **Top bar:** Hiển thị mã đang chọn, giá, % thay đổi; nút mở Command Palette (Ctrl+K).
- **Vùng nội dung chính:** Thay đổi theo từng trang.

### 5.2 Dashboard (Trang chủ)

- **Bảng giá (Price Board):** Cột Mã CK, Giá, Thay đổi, %, Khối lượng. Dữ liệu cập nhật real-time qua WebSocket. Click vào một dòng để chọn mã và xem biểu đồ.
- **Biểu đồ nến (Trading Chart):** Hiển thị nến và (nếu có) signal BUY/SELL từ pipeline. Mã hiển thị là mã đang chọn trên bảng giá.

### 5.3 Portfolio

- **Tổng quan tài sản:** NAV, tiền mặt (từ store; có thể đồng bộ từ API/WebSocket).
- **Bảng vị thế (Positions):** Mã CK, khối lượng, giá TB, giá TT, lãi/lỗ, % lãi/lỗ. Dữ liệu từ `portfolio-store`.

### 5.4 Orders

- **Form đặt lệnh:** Chọn MUA/BÁN, mã (theo mã đang chọn), khối lượng, giá. Gửi lệnh (khi đã kết nối OMS).
- **Lịch sử lệnh:** Bảng lệnh với trạng thái (PENDING, MATCHED, REJECTED, …). Dữ liệu từ `order-store`.

### 5.5 Screener

- Trang kết quả screener từ pipeline (danh sách mã vượt bộ lọc cơ bản + volume spike). Nội dung có thể mở rộng theo tích hợp backend.

### 5.6 Settings

- Trạng thái kết nối (WebSocket, API), ghi chú cấu hình API key / SSI. Có thể mở rộng thêm tuỳ chọn.

### 5.7 Command Palette (Ctrl+K)

- **Phím tắt:** `Ctrl+K` (Windows/Linux) hoặc `Cmd+K` (macOS).
- **Chức năng:**
  - Điều hướng: gõ `/dashboard`, `/portfolio`, `/orders`, `/screener`, `/settings`.
  - Chọn mã: gõ mã 3 ký tự (ví dụ `FPT`, `VNM`) để đặt làm mã đang xem.
  - Lệnh giao dịch (parse): `BUY FPT 1000`, `BUY FPT 1000 PRICE 98.5`, `SELL VNM 500`. Hệ thống parse và có thể chuyển sang form lệnh hoặc API đặt lệnh (tuỳ tích hợp).

Đóng palette: `Escape` hoặc click ra ngoài.

---

## 6. Giao diện người dùng — Nâng cao

### 6.1 Bảng giá (AG Grid)

- Cập nhật theo tick: dữ liệu WebSocket được gom theo frame và áp dụng qua `applyTransactionAsync` để giảm re-render, mượt với nhiều mã.
- Click hàng → đặt mã active → biểu đồ và (nếu có) form lệnh dùng mã đó.
- Màu: xanh (tăng), đỏ (giảm), vàng/trung tính (trần/sàn/không đổi) theo logic `PriceCell`.

### 6.2 Biểu đồ nến (TradingView Lightweight Charts)

- Nến theo dữ liệu candle từ store; cập nhật real-time khi có candle mới.
- Signal overlay: đánh dấu BUY/SELL từ agent (nếu backend gửi qua WebSocket).
- Responsive: tự resize theo khung.

### 6.3 WebSocket và Store

- **WebSocket:** Kết nối tới `ws://localhost:8000/ws/market`. Khi mất kết nối, provider có thể tự reconnect (logic trong `ws-provider.tsx`).
- **Stores (Zustand):**
  - `market-store`: ticks, candles.
  - `portfolio-store`: positions, cash, nav, purchasing power.
  - `signal-store`: danh sách signal (BUY/SELL) từ pipeline, giới hạn 100 bản ghi.
  - `order-store`: lệnh đã đặt / cập nhật trạng thái.
  - `ui-store`: mã đang chọn, trạng thái mở Command Palette, thu gọn sidebar.

Message từ WebSocket được map theo `type` (tick, candle, signal, position, …) và đẩy vào store tương ứng.

### 6.4 Hook `useMarketStream`

- Subscribe `latestTick` từ market store, batch update và áp dụng lên AG Grid bằng `requestAnimationFrame` để đạt ~60fps khi có nhiều tick.

---

## 7. API & Tích hợp

### 7.1 REST API (FastAPI)

- **Base URL:** `http://localhost:8000`
- **Tài liệu tương tác:** `http://localhost:8000/docs`

**Endpoints chính:**

| Method | Path | Mô tả |
|:---|:---|:---|
| GET | `/api/health` | Trạng thái hệ thống (healthy/unhealthy) |
| GET | `/api/portfolio` | (Nếu có) Thông tin portfolio |

Có thể mở rộng thêm endpoint orders, screener, pipeline trigger trong code.

### 7.2 WebSocket `/ws/market`

- **URL:** `ws://localhost:8000/ws/market`
- **Giao thức message:** JSON, có trường `type` và `payload`.

Ví dụ payload (minh hoạ):

- **Tick:** `{ "type": "tick", "payload": { "symbol": "FPT", "price": 98.5, "change": 1.2, "changePercent": 1.23, "volume": 1500000, "timestamp": 1234567890 } }`
- **Signal:** `{ "type": "signal", "payload": { "id": "...", "symbol": "FPT", "action": "BUY", "confidence": 0.85, "reason": "...", "timestamp": ... } }`
- **Position:** `{ "type": "position", "payload": { "symbol": "FPT", "quantity": 1000, "avgPrice": 95, "marketPrice": 98.5 } }`

Frontend đọc `type` và cập nhật store tương ứng.

### 7.3 Gọi pipeline từ code (Python)

Pipeline LangGraph có thể được gọi từ runner (xem `packages/agents/src/agents/runner.py`). Ví dụ khởi tạo state và chạy:

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

Dependency (screener, technical, risk, executor, tick_repo, broker, …) cần được inject qua `SystemDependencies` hoặc tương đương.

---

## 8. Pipeline & Chế độ dry-run / live

### 8.1 Luồng pipeline

1. **Inject context:** run_id, max_candidates, score_threshold, dry_run, …
2. **Screener:** Lọc mã theo fundamental + volume spike → watchlist.
3. **Technical:** Điểm kỹ thuật (RSI, MACD, BB, MA) → top_candidates.
4. **Risk:** Kiểm tra kill switch, NAV, VaR, T+2.5, lot size, … → approved_trades.
5. **Executor:** Tạo execution plan; nếu `dry_run=False` thì gọi broker (idempotency key), nếu `dry_run=True` thì chỉ log, không gửi lệnh.
6. **Finalize:** Đánh dấu phase COMPLETED.

Fundamental Agent (AI) có thể chạy song song/nhánh riêng, cập nhật `ai_insights` vào state.

### 8.2 Dry-run (mặc định an toàn)

- `dry_run=True`: Executor **không** gọi `broker.place_order`. Chỉ tạo execution plan và log. Dùng để kiểm tra logic, backtest, demo.

### 8.3 Live (đặt lệnh thật)

- `dry_run=False` và broker được cấu hình: Executor gọi broker với idempotency key (ví dụ `run_id:symbol:BUY`). Mỗi ý định chỉ tạo một lệnh trên sàn. Cần cấu hình SSI/DNSE và chấp nhận rủi ro tài chính.

### 8.4 Idempotency

- Mỗi lệnh (hoặc mỗi ý định từ pipeline) gắn một **idempotency key**.
- Nếu client/pipeline gửi trùng key, OMS trả về lệnh đã lưu thay vì tạo lệnh mới → tránh đặt trùng khi retry hoặc double-click.

---

## 9. Xử lý sự cố

### 9.1 Backend không start

- **Lỗi thiếu module:** Chạy lại `uv sync` ở thư mục gốc.
- **Port 8000 bị chiếm:** Đổi port trong `interface/cli.py` (ví dụ `port=8001`) hoặc tắt process đang dùng 8000.
- **Lỗi import core/adapters/agents:** Đảm bảo chạy từ thư mục gốc và đã `uv sync` (workspace packages được cài đúng).

### 9.2 Frontend không kết nối dữ liệu

- Kiểm tra backend đã chạy tại `http://localhost:8000` và `/api/health` trả 200.
- Kiểm tra WebSocket URL trong frontend (mặc định `ws://localhost:8000/ws/market`). Nếu chạy backend ở host/port khác, cần đổi biến môi trường hoặc config (ví dụ `NEXT_PUBLIC_WS_URL`).
- Mở DevTools → Network → WS: xem kết nối WebSocket có thành công và có message không.

### 9.3 SSI / DNSE auth lỗi

- Kiểm tra `.env`: `SSI_CONSUMER_ID`, `SSI_CONSUMER_SECRET`, `SSI_PRIVATE_KEY_PEM`, `SSI_PRIVATE_KEY_PASSPHRASE` đúng và không thừa khoảng trắng.
- Private key: đúng định dạng PEM (hoặc base64), passphrase đúng. Nếu key lưu file, adapter có thể hỗ trợ đọc từ file (xem `credential_manager`).

### 9.4 OpenVINO / AI không chạy

- Model chưa có: cần export INT4 (xem `scripts/quantize_model.py` và doc OpenVINO). Đặt model vào `OPENVINO_MODEL_PATH` (ví dụ `data/models/phi-3-mini-int4/`).
- Không có NPU: hệ thống fallback CPU; có thể chậm. Đặt `OPENVINO_DEVICE=CPU` nếu muốn rõ ràng.
- Thiếu thư viện: cài `openvino`, `openvino-genai` (hoặc theo hướng dẫn Phase 5). Nếu không cài, Fundamental Agent trả về nội dung mặc định “[AI engine unavailable]”.

### 9.5 Lệnh không lên sàn / trùng lệnh

- Kiểm tra `dry_run` đã đặt `False` và broker (SSI/DNSE) đã cấu hình và được inject vào Executor.
- Idempotency: nếu gửi cùng idempotency key hai lần, lần hai nhận lại kết quả lệnh đã tạo (không tạo lệnh mới). Kiểm tra log “Duplicate order detected” nếu có.
- Risk từ chối: xem log lý do (kill switch, vượt NAV, vượt sellable qty, vượt price band, lot size không đúng bội 100, …).

### 9.6 Log và debug

- Backend: log theo `LOG_LEVEL` và `LOG_FORMAT` trong `.env`. `LOG_LEVEL=DEBUG` để xem chi tiết.
- Frontend: console trình duyệt; React DevTools cho state (Zustand).
- Pipeline: observability (structured log) ghi từng bước agent (run_id, phase, …) để trace.

---

## 10. Bảo mật & Khuyến nghị

### 10.1 Bảo mật

- **Không commit `.env`:** File này chứa consumer secret, private key, passphrase. Luôn nằm trong `.gitignore`.
- **Không hardcode key trong code** hoặc trong repo. Dùng biến môi trường hoặc keyring/secret manager.
- **Private key:** Lưu ở nơi an toàn; có thể mã hoá bằng passphrase và lưu trong `data/secrets/` (đã có hỗ trợ trong credential manager).
- **HTTPS/WSS trong production:** Khi deploy, dùng HTTPS cho REST và WSS cho WebSocket; cấu hình reverse proxy (nginx, Caddy) và certificate.

### 10.2 Khuyến nghị vận hành

- **Luôn bắt đầu với dry_run=True** khi chạy pipeline với dữ liệu thật; chỉ bật live khi đã kiểm tra kỹ.
- **Giám sát kết nối WebSocket:** Nếu mất kết nối trong giờ giao dịch, dữ liệu tick có thể thiếu; hệ thống có buffer và reconnect, nhưng nên có cảnh báo khi mất kết nối lâu.
- **Sao lưu data:** Thư mục `data/` (DuckDB, Parquet, prompts) nên được backup định kỳ; không commit vào git.
- **Cập nhật dependency:** Định kỳ `uv sync` và `pnpm install`; kiểm tra CVE cho thư viện quan trọng (auth, broker, crypto).

### 10.3 Giới hạn và rủi ro

- Hệ thống không thay thế quyết định đầu tư của con người. Tín hiệu và execution chỉ mang tính hỗ trợ.
- Rủi ro tài chính: giao dịch thật có thể dẫn đến mất vốn. Chỉ dùng với số vốn chấp nhận được và đã hiểu rõ logic risk (T+2.5, price band, lot size, VaR, kill switch).
- Tuân thủ quy định pháp luật và nội quy sàn (SSI, DNSE, VSD) về giao dịch tự động và lưu trữ dữ liệu.

---

## Phụ lục A: Lệnh nhanh (Cheat sheet)

| Việc cần làm | Lệnh |
|:---|:---|
| Cài đặt lần đầu | `uv sync` → `cd frontend && pnpm install` |
| Chạy backend | `uv run python -m interface.cli` |
| Chạy frontend | `cd frontend && pnpm dev` |
| Build frontend | `cd frontend && pnpm build && pnpm start` |
| Test backend | `uv run pytest tests/ -v --tb=short` |
| Test frontend | `cd frontend && pnpm vitest run` |
| Lint Python | `uv run ruff check packages/ tests/` |
| Type check Python | `uv run mypy packages/ --strict` |
| Mở Command Palette | `Ctrl+K` hoặc `Cmd+K` |

---

## Phụ lục B: Cấu trúc thư mục quan trọng

```
algo-trading/
├── .env                    # Cấu hình (không commit)
├── .env.example            # Mẫu biến môi trường
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

*Tài liệu này mô tả phiên bản hệ thống theo Implementation Plan và các blueprint 01–06. Khi tính năng thay đổi, nên cập nhật lại USER_MANUAL.md.*
