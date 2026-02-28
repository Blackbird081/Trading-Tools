# Enterprise Algo-Trading Platform on Hybrid AI

**Production-Ready** 🚀 | **All Phases Completed** ✅

[![CI](https://github.com/Blackbird081/Trading-Tools/actions/workflows/ci.yml/badge.svg)](https://github.com/Blackbird081/Trading-Tools/actions/workflows/ci.yml)

## Tổng quan

Hệ thống giao dịch thuật toán doanh nghiệp với AI lai (Hybrid AI):
- **Backend**: Python 3.12+ monorepo với Clean Architecture (Hexagonal)
- **Database**: DuckDB (in-process OLAP) với Parquet partitioning
- **AI/ML**: LangGraph multi-agent + OpenVINO NPU (Intel Core Ultra)
- **Frontend**: Next.js 15 + React 19 + AG Grid + Zustand
- **Brokers**: SSI FastConnect API v2 + DNSE Entrade X (fallback)
- **DevOps**: Docker + GitHub Actions CI/CD

## Cấu trúc dự án

```
algo-trading/
├── packages/
│   ├── core/          # Domain layer — entities, ports, use cases (ZERO deps)
│   ├── adapters/      # Infrastructure — DuckDB, SSI, DNSE, Vnstock, OpenVINO
│   ├── agents/        # LangGraph multi-agent + Backtesting + Investor Personas
│   └── interface/     # FastAPI + WebSocket API + Auth + Rate Limiting
├── frontend/          # Next.js 15 dashboard
├── tests/
│   ├── unit/          # Pure logic tests + property-based (hypothesis)
│   └── integration/   # DuckDB, SSI auth, order sync tests
├── Dockerfile         # Multi-stage production build
├── docker-compose.yml # Full stack deployment
└── .github/workflows/ # CI/CD pipeline
```

## Cài đặt nhanh

### Backend

```bash
uv sync
uv run uvicorn interface.app:app --reload --port 8000
uv run pytest tests/ -v --cov=packages
```

### Frontend

```bash
cd frontend && pnpm install && pnpm dev
```

### Docker

```bash
docker-compose up --build
```

## Cấu hình

Copy `.env.example` thành `.env`:

| Biến | Mô tả |
|------|--------|
| `SSI_CONSUMER_ID` | SSI FastConnect Consumer ID |
| `SSI_CONSUMER_SECRET` | SSI Consumer Secret |
| `SSI_PRIVATE_KEY_B64` | RSA private key (base64) |
| `SSI_ACCOUNT_NO` | Số tài khoản SSI |
| `DRY_RUN` | `true` = không đặt lệnh thật |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Telegram chat ID |
| `AUTH_ENABLED` | `false` cho dev, `true` cho production |

## API Endpoints

| Endpoint | Mô tả |
|----------|--------|
| `GET /api/health` | Health check |
| `GET /api/health/live` | Liveness probe |
| `GET /api/health/ready` | Readiness probe |
| `GET /api/portfolio` | Portfolio state |
| `GET /api/portfolio/positions` | Positions với T+2.5 |
| `GET /api/portfolio/pnl?days=30` | P&L history |
| `ws://host/ws/market` | Real-time market data |

## Kiến trúc

### Multi-Agent Pipeline

```
START → screener → technical → [fundamental] → risk → executor → END
```

### Risk Checks (7 layers)

1. Kill Switch, 2. Price Band (±7% HOSE), 3. Lot Size (×100),
4. Position Size (max % NAV), 5. Buying Power, 6. Sellable Qty (T+2.5),
7. Daily Loss Limit

### Investor Personas (FinceptTerminal-inspired)

- **Nhà Đầu Tư Giá Trị VN** — Buffett style: ROE ≥15%, P/E ≤20x
- **Nhà Đầu Tư Tăng Trưởng VN** — Revenue growth ≥20%/năm
- **Momentum Trader HOSE** — RSI, MACD, Volume spike ≥2x
- **Nhà Đầu Tư Cổ Tức VN** — Dividend yield ≥4%
- **Nhà Đầu Tư Ngược Chiều VN** — P/B ≤1.0, RSI <25

### Backtesting Metrics

Sharpe ratio, Sortino ratio, Calmar ratio, Max Drawdown, CAGR, SQN, Profit Factor

## Security

- JWT Bearer + API Key authentication
- Rate limiting: 60 req/min (10 req/min cho orders)
- CORS: explicit origins/methods/headers
- AI Guardrails: PII detection (CMND/CCCD, phone VN), prompt injection protection
- Credentials: AES-GCM + scrypt KDF, RSA 2048+ bit

## Tài liệu

- [USER_MANUAL.md](docs/USER_MANUAL.md)
- [IMPLEMENTATION_PLAN.md](docs/plans/IMPLEMENTATION_PLAN.md)
- [01_System_Architecture_Overview.md](docs/blueprints/01_System_Architecture_Overview.md)

## License

Proprietary — Enterprise Internal Use Only

---

**Status**: ✅ **Production-Ready** — All phases completed, security hardened, Docker-ready.
