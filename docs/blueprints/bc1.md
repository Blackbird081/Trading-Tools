Dưới đây là bản báo cáo tổng hợp hoàn chỉnh (Final Report), được biên soạn dựa trên cấu trúc chuẩn của Báo cáo 2 ("Nâng Cấp Kiến Trúc Hệ Thống Tài Chính") và tích hợp chi tiết kỹ thuật, thuật toán, mã nguồn từ Báo cáo 1 ("Tư vấn xây dựng Web App chứng khoán").

Nội dung đảm bảo giữ nguyên 100% các thông tin quan trọng từ cả hai báo cáo, được sắp xếp lại logic để tạo thành một thể thống nhất: **Hệ thống giao dịch thuật toán Enterprise trên nền tảng Hybrid AI & Intel Core Ultra.**

---

# BÁO CÁO NGHIÊN CỨU CHUYÊN SÂU: KIẾN TRÚC HỆ THỐNG GIAO DỊCH THUẬT TOÁN ĐA TÁC VỤ THẾ HỆ MỚI (ENTERPRISE EDITION) & TRIỂN KHAI TRÊN NỀN TẢNG HYBRID AI

## TỔNG QUAN ĐIỀU HÀNH VÀ TẦM NHÌN CHIẾN LƯỢC

### 1.1. Bối Cảnh và Sự Chuyển Dịch Mô Hình
Trong kỷ nguyên tài chính kỹ thuật số, ranh giới giữa giao dịch tổ chức (institutional trading) và cá nhân chuyên nghiệp đang bị xóa nhòa. Tuy nhiên, các hệ thống hiện tại thường đánh đổi giữa giao diện đẹp (GUI) và chiều sâu xử lý. Báo cáo này đề xuất kiến trúc tham chiếu cho một nền tảng giao dịch "Make-in-Vietnam", phá vỡ sự đánh đổi trên bằng cách kết hợp:
1.  **Trải nghiệm Enterprise:** GUI được coi là "sản phẩm cốt lõi", tương đương Bloomberg Terminal nhưng chạy trên Web hiện đại.
2.  **Sức mạnh Hybrid AI:** Tận dụng NPU của chip Intel Core Ultra (dòng Lunar Lake) để chạy AI cục bộ kết hợp với dữ liệu đám mây.
3.  **Hệ thống Đa Tác Vụ (Multi-Agent System - MAS):** Các tác nhân AI chuyên biệt phối hợp xử lý dữ liệu thời gian thực.

### 1.2. Mục Tiêu Cốt Lõi
Hệ thống "Cố vấn số" (Digital Advisor) và Giao dịch tự động này có khả năng:
*   **Kết nối sâu (Deep Linking):** Truy xuất danh mục tài sản thời gian thực từ CTCK (SSI, DNSE).
*   **Xử lý thời gian thực (Real-time):** Phân tích luồng dữ liệu thị trường với độ trễ thấp bằng DuckDB và WebSockets.
*   **Trí tuệ nhân tạo biên (Edge AI):** Chạy mô hình ngôn ngữ lớn (LLM) cục bộ trên NPU Intel Core Ultra.
*   **Thuật toán định lượng:** Kết hợp Phân tích kỹ thuật và Lý thuyết danh mục hiện đại (MPT).

---

## CHƯƯƠNG 1: CÁC TRỤ CỘT CÔNG NGHỆ VÀ KIẾN TRÚC HYBRID

Để hiện thực hóa tầm nhìn, việc lựa chọn ngăn xếp công nghệ (tech stack) dựa trên hiệu năng và khả năng mở rộng.

### 1.1. Bảng Công Nghệ Lựa Chọn (Tech Stack)

| Thành phần | Công nghệ lựa chọn | Lý do chiến lược |
| :--- | :--- | :--- |
| **Phần cứng (Hardware)** | **Intel Core Ultra 7 256V (Lunar Lake)** | Tận dụng NPU 48 TOPS để chạy AI cục bộ, tiết kiệm điện năng và bảo mật dữ liệu. |
| **Frontend (GUI)** | **Next.js (React 19) + AG Grid Enterprise** | Render hàng nghìn dòng dữ liệu/giây; Server Components tối ưu tải trang; Kiến trúc module hóa. |
| **Trực quan hóa** | **TradingView Lightweight Charts** | Sử dụng Canvas HTML5 thay vì SVG, tối ưu cho tick data tần suất cao, độ trễ gần như bằng không. |
| **Backend API** | **FastAPI (Python)** | Framework nhanh nhất, hỗ trợ bất đồng bộ (asyncio), tích hợp chặt chẽ hệ sinh thái AI. |
| **Quản lý Gói** | **uv (Astral)** | Thay thế pip/poetry. Viết bằng Rust, tốc độ cài đặt nhanh gấp 10-100 lần, hỗ trợ Workspaces cho monorepo. |
| **Cơ sở dữ liệu** | **DuckDB** | DB phân tích nhúng (in-process OLAP), thay thế TimescaleDB/SQLite, cho phép truy vấn vector hóa trên dữ liệu tick ngay trong RAM. |
| **Trí tuệ nhân tạo** | **LangGraph + OpenVINO** | Điều phối hệ thống đa tác nhân (Multi-Agent) và tối ưu hóa model AI chạy trên NPU Intel. |

### 1.2. Kiến Trúc Hybrid Cloud-Edge
Hệ thống hoạt động theo mô hình Hybrid để tối ưu hóa tài nguyên:
*   **Cloud (API CTCK & Market Data):** Các tác vụ I/O bound như lấy giá realtime, đồng bộ danh mục từ SSI/Vnstock.
*   **Edge (Local NPU - Intel Core Ultra):** Các tác vụ Compute bound (Tính toán nặng) và AI Inference chạy cục bộ. Việc chạy Local LLM trên NPU giúp bảo mật tuyệt đối dữ liệu tài chính và không tốn chi phí API token.

---

## CHƯƠNG 2: KIẾN TRÚC FRONTEND - TRẢI NGHIỆM CHUẨN ENTERPRISE

Yêu cầu tiên quyết: "GUI là yếu tố quan trọng nhất". Frontend được xây dựng độc lập, giao tiếp với Backend qua WebSockets.

### 2.1. Nền Tảng Next.js và Chiến Lược Render
Sử dụng **Next.js (App Router)** để cung cấp trải nghiệm cấp doanh nghiệp:
*   **Server Components:** Xử lý khung vỏ (App Shell), layout, xác thực ban đầu.
*   **Client Components:** Chứa logic giao dịch thực sự (Bảng giá, Biểu đồ, Sổ lệnh) để duy trì kết nối WebSocket liên tục.
*   **Persistent Layouts:** Thanh điều hướng và widget "ghim" không bị re-render khi chuyển trang (ví dụ: từ "Screener" sang "Portfolio").

### 2.2. Hệ Thống Lưới Dữ Liệu: AG Grid Enterprise
*   **Ảo hóa DOM:** Chỉ render các dòng đang hiển thị (viewport), đảm bảo mượt mà dù Watchlist có 2.000 mã.
*   **Transaction Update:** Cập nhật dữ liệu ở mức tế bào (cell level) theo lô (batch update) khớp với tần số quét màn hình (60fps).
*   **Master-Detail & Pivot:** Cho phép click vào mã chứng khoán để mở panel chi tiết (biểu đồ mini, chỉ số cơ bản) hoặc xoay chiều dữ liệu theo nhóm ngành/rủi ro.

### 2.3. Trực Quan Hóa: TradingView Lightweight Charts & Custom Overlays
Sử dụng công nghệ HTML5 Canvas để vẽ biểu đồ nến và chỉ báo kỹ thuật mà không tốn tài nguyên CPU (reflow/repaint) như SVG.
*   **Lớp phủ tương tác (Custom Overlays):**
    *   *Technical Agent:* Vẽ tự động các đường trendline, điểm chốt mô hình "Vai-Đầu-Vai".
    *   *Risk Agent:* Hiển thị mức Stop-loss/Take-profit động, cho phép kéo thả trực tiếp trên biểu đồ.
    *   *Signal Markers:* Mũi tên Mua/Bán kèm tooltip giải thích lý do (ví dụ: "RSI quá bán + Divergence").

### 2.4. Giao Diện UI/UX
*   **Shadcn UI + Tailwind CSS:** Thiết kế theo phong cách "High Density" (Mật độ thông tin cao).
*   **Dark Mode:** Chế độ tối mặc định, độ tương phản cao (Slate/Zinc palette).
*   **Command Palette (Ctrl+K):** Trung tâm điều khiển, cho phép nhập lệnh bằng văn bản (ví dụ: "Buy FPT 1000 price 98.5" hoặc "Show MA 200").

---

## CHƯƠNG 3: HẠ TẦNG BACKEND & ĐỘNG CƠ DỮ LIỆU (DUCKDB)

Backend được xây dựng lại hoàn toàn trên nền tảng Python hiện đại, tối ưu cho tốc độ cao.

### 3.1. Quản Lý Gói và Môi Trường với uv
Sử dụng **uv** (viết bằng Rust) thay cho pip/poetry.
*   **Tốc độ:** Cài đặt và giải quyết phụ thuộc nhanh gấp 10-100 lần.
*   **Kiến trúc Monorepo:** Sử dụng tính năng Workspaces của uv để tổ chức mã nguồn thành các gói riêng biệt (`/core`, `/connectors`, `/analytics`, `/agents`) nhưng quản lý chung trong một repo.

### 3.2. FastAPI và Kiến Trúc Bất Đồng Bộ
*   **Asyncio:** Xử lý hàng nghìn kết nối WebSocket đồng thời.
*   **Background Tasks:** Đẩy các tác vụ nặng (chạy NPU Inference, tối ưu Portfolio) xuống chạy ngầm, trả phản hồi tức thì cho UI.
*   **Pydantic V2:** Validate dữ liệu JSON từ sàn giao dịch cực nhanh nhờ core viết bằng Rust.

### 3.3. Động Cơ Dữ Liệu: DuckDB (Thay thế TimescaleDB)
DuckDB hoạt động như một DB OLAP nhúng, loại bỏ độ trễ mạng.
*   **Lưu trữ dạng cột (Columnar):** Nén dữ liệu Tick cực tốt.
*   **Phân vùng (Partitioning):** Lưu trữ file Parquet theo Ngày/Tháng, truy vấn trực tiếp không cần nạp toàn bộ vào RAM.
*   **Kỹ thuật ASOF JOIN:** "Vũ khí" của tài chính. Ghép nối bảng Lệnh và Bảng Giá dựa trên thời điểm gần nhất (ví dụ: Tìm giá thị trường tại chính xác mili-giây lệnh bán được gửi đi) để tính PnL và Backtesting siêu tốc.
*   **Phân tích Vector hóa:** Các Agent đẩy logic tính toán xuống DuckDB (SQL) thay vì lặp bằng Python.

---

## CHƯƠNG 4: HỆ THỐNG ĐA TÁC VỤ (MULTI-AGENT SYSTEM) & THUẬT TOÁN

Hệ thống AI ("The Brain") được chia nhỏ thành các Agent chuyên biệt, phối hợp qua framework **LangGraph** theo mô hình Supervisor (Siêu Agent điều phối).

### 4.1. Data Agent (Cảm Biến Thị Trường)
*   **Nhiệm vụ:** Kết nối WebSocket tới SSI/Vnstock, chuẩn hóa dữ liệu.
*   **Kỹ thuật:**
    *   Sử dụng thư viện `websockets` của Python (async).
    *   Quản lý bộ đệm (buffer) để ghi dữ liệu vào DuckDB theo lô (batch insert) mỗi 1 giây.
    *   Quản lý dữ liệu In-Memory (Redis hoặc Python Dict) cho giá mới nhất để truy xuất cực nhanh, không query DB cho mỗi tick.

### 4.2. Screener Agent (Bộ Lọc)
*   **Nhiệm vụ:** Quét toàn bộ thị trường tìm cơ hội.
*   **Kỹ thuật:**
    *   Sử dụng `vnstock.stock_screening()` để lọc cơ bản (EPS tăng, PE thấp).
    *   Định kỳ kích hoạt truy vấn SQL vector hóa trên DuckDB để tính toán chỉ báo kỹ thuật.
    *   Kết quả trả về là "Dynamic Watchlist" đẩy lên Frontend.

### 4.3. Technical Analysis Agent (Nhà Phân Tích Kỹ Thuật)
Đây là nơi áp dụng các thuật toán định lượng từ Báo cáo 1.
*   **Công cụ:** Thư viện `pandas-ta` và `PyPortfolioOpt`.
*   **Thuật toán 1: Tối Ưu Hóa Danh Mục (Portfolio Rebalancing):**
    *   Dựa trên Modern Portfolio Theory (MPT).
    *   Sử dụng `PyPortfolioOpt` để tìm đường biên hiệu quả (Efficient Frontier).
    *   Xử lý ràng buộc lô chẵn (Lot Size 100) bằng module `DiscreteAllocation`.
*   **Thuật toán 2: Chấm điểm kỹ thuật (Technical Scoring):**
    *   Hệ thống chấm điểm thang 10 dựa trên: RSI (Quá mua/Quá bán), MACD (Cắt lên/xuống), Bollinger Bands, Trend (MA50/MA200).
    *   **Quyết nghị:** Điểm > 8 (MUA MỚI), < -5 (BÁN), -5 đến 5 (NẮM GIỮ).

### 4.4. Fundamental Analysis Agent (Nhà Phân Tích Cơ Bản & AI)
Tận dụng phần cứng Intel Core Ultra.
*   **Công nghệ:** **OpenVINO™ GenAI**.
*   **Triển khai:**
    *   Chạy model **Phi-3-mini** hoặc **Llama-3-8B** đã được lượng tử hóa (INT4) trên NPU.
    *   **Quy trình:** Lấy tin tức từ vnstock -> Gửi vào NPU kèm chỉ số kỹ thuật -> NPU trả về đoạn văn bản phân tích tự nhiên ("AI Insight").
    *   **Lợi ích:** Không chia sẻ dữ liệu ra ngoài, tốc độ suy luận cao, không tốn chi phí.

### 4.5. Risk Management Agent (Quản Trị Rủi Ro)
*   **Nhiệm vụ:** Middleware kiểm soát mọi lệnh đặt.
*   **Logic:**
    *   **Kill Switch:** Nút dừng khẩn cấp trên giao diện.
    *   **Safety Checks:** Không mua quá 20% NAV/lệnh, giá đặt không vượt trần/sàn.
    *   **VaR (Value at Risk):** Tính toán rủi ro thời gian thực bằng dữ liệu lịch sử trong DuckDB.

---

## CHƯƠNG 5: TÍCH HỢP DỮ LIỆU THỊ TRƯỜNG VIỆT NAM (SSI & DNSE)

Hệ thống được thiết kế đặc thù cho thị trường Việt Nam (T+2.5).

### 5.1. Phân Tích Hạ Tầng Môi Giới
*   **Chiến lược "Hai Trụ Cột":**
    1.  **SSI (FastConnect Trading API):** Dùng cho giao dịch và lấy dữ liệu Portfolio chính xác nhất. Ổn định, chuẩn mực.
    2.  **Vnstock (Wrapper):** Dùng làm nguồn dữ liệu bổ trợ (Lịch sử giá, Tin tức, Data Mining) thay thế cho các gói dữ liệu đắt đỏ.

### 5.2. Chi Tiết Triển Khai Kết Nối SSI (Implementation)
Khác với API thông thường, SSI yêu cầu ký số RSA.
*   **Quy trình xác thực (Handshake):**
    1.  Tạo cặp khóa RSA (Private/Public Key). Upload Public Key lên iBoard SSI.
    2.  Sử dụng thư viện `pycryptodome` để ký các request bằng Private Key.
    3.  Lấy Access Token (JWT) để duy trì phiên làm việc.
*   **Đồng bộ Danh mục (Portfolio Sync):**
    *   Gọi endpoint `stockPosition`.
    *   **Data Normalization:** Chuẩn hóa dữ liệu thô từ SSI về cấu trúc nội bộ (Mapping các trường `onHand`, `sellableQty`, `avgPrice`, `marketPrice`).
    *   **Xử lý T+2.5:** Logic phân biệt "Tiền mặt thực có" (cashBal) và "Sức mua" (purchasingPower) để tránh Call Margin.

### 5.3. Kết Nối DNSE (Entrade X)
*   Tận dụng API hiện đại RESTful của DNSE cho các tác vụ cần tốc độ cao hoặc miễn phí giao dịch.
*   Lưu ý cơ chế quản lý Token/Refresh Token để tránh mất kết nối.

---

## CHƯƠNG 6: LỘ TRÌNH TRIỂN KHAI & KẾT LUẬN

### 6.1. Lộ Trình Phát Triển (12 Tuần)
1.  **Giai đoạn 1 (Tuần 1-4):** Thiết lập hạ tầng `uv` workspace, kết nối DuckDB. Xây dựng Data Agent kết nối SSI (xác thực RSA) và Vnstock.
2.  **Giai đoạn 2 (Tuần 5-8):** Phát triển Frontend Next.js với AG Grid và TradingView Charts. Hiển thị dữ liệu realtime qua WebSocket.
3.  **Giai đoạn 3 (Tuần 9-10):** Phát triển các Agent thuật toán (Screener, Tech Analysis với PyPortfolioOpt/Pandas-TA). Tích hợp logic ASOF JOIN.
4.  **Giai đoạn 4 (Tuần 11-12):** Tích hợp Fundamental Agent (OpenVINO GenAI trên NPU). Hoàn thiện Risk Agent, GUI Dark Mode, Command Palette và Testing.

### 6.2. Kết Luận
Báo cáo đã trình bày một kiến trúc toàn diện, kết hợp sức mạnh phần cứng cá nhân tiên tiến (Intel Core Ultra) với kiến trúc phần mềm Enterprise (Next.js, DuckDB, Multi-Agent). Đây không chỉ là công cụ giao dịch, mà là một lợi thế cạnh tranh công nghệ, cho phép nhà đầu tư khai thác tối đa cơ hội thị trường với sự hỗ trợ đắc lực của AI và tốc độ xử lý vượt trội.

---
*Hết báo cáo.*