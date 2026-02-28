# ROADMAP — Cải Tiến Hệ Thống Algo-Trading

> Được tổng hợp từ đánh giá code độc lập. Ưu tiên theo mức độ ảnh hưởng đến tính đúng đắn và bảo mật.

---

## 🔴 SPRINT 1 — Critical Fixes (Tuần 1-2)

### 1.1 Fix Entry Price Logic trong ExecutorAgent

**File:** [`packages/agents/src/agents/executor_agent.py:45`](packages/agents/src/agents/executor_agent.py)

**Vấn đề:** `entry_price = risk.take_profit_price` — dùng giá take-profit (+10%) làm giá đặt lệnh. Lệnh LO sẽ khớp ngay ở giá thị trường nhưng `_calculate_quantity` tính sai số lượng.

**Fix:**
```python
# Thêm field latest_price vào RiskAssessment
@dataclass(frozen=True, slots=True)
class RiskAssessment:
    latest_price: Decimal  # ★ NEW: actual market price
    stop_loss_price: Decimal   # = latest_price * (1 - stop_loss_pct)
    take_profit_price: Decimal # = latest_price * (1 + take_profit_pct)
    ...

# Trong executor_agent.py
entry_price = risk.latest_price  # ★ FIX: dùng giá thị trường thực tế
```

**Test:** Thêm unit test kiểm tra `entry_price == latest_price` trong `test_executor_agent.py`.

---

### 1.2 Fix Float Conversion trong ExecutorAgent

**File:** [`packages/agents/src/agents/executor_agent.py:135`](packages/agents/src/agents/executor_agent.py)

**Vấn đề:** `price=float(price)` — mất Decimal precision với giá VND lớn (ví dụ: 98,500 VND).

**Fix:**
```python
# TRƯỚC
price=float(price),

# SAU
price=str(price),  # Consistent với SSI broker "★ String, not float"
```

---

## 🟠 SPRINT 2 — High Priority (Tuần 3-4)

### 2.1 Refactor Position Size Calculation

**File:** [`packages/agents/src/agents/risk_agent.py:162`](packages/agents/src/agents/risk_agent.py)

**Vấn đề:** `purchasing_power / nav` không tính đến giá cổ phiếu thực tế.

**Fix:**
```python
def _calculate_position_size(
    self,
    nav: Decimal,
    purchasing_power: Decimal,
    latest_price: Decimal,
    max_pct: Decimal,
) -> Decimal:
    """Tính % NAV thực sự sẽ dùng cho lệnh này."""
    if nav <= 0 or latest_price <= 0:
        return Decimal("0")
    max_order_value = nav * max_pct
    affordable = min(purchasing_power, max_order_value)
    # Round down to nearest lot (100 shares)
    lots = int(affordable / latest_price) // 100
    actual_value = Decimal(lots * 100) * latest_price
    return actual_value / nav
```

---

### 2.2 Configurable Stop-Loss / Take-Profit

**File:** [`packages/agents/src/agents/risk_agent.py:104`](packages/agents/src/agents/risk_agent.py)

**Vấn đề:** Stop-loss = -7% = HOSE price band floor → không bao giờ trigger trong 1 phiên.

**Fix:**
```python
# Trong core/entities/risk.py
@dataclass(frozen=True, slots=True)
class RiskLimit:
    max_position_pct: Decimal
    max_daily_loss: Decimal
    kill_switch_active: bool
    stop_loss_pct: Decimal = Decimal("0.05")    # ★ NEW: 5% dưới entry
    take_profit_pct: Decimal = Decimal("0.15")  # ★ NEW: 15% trên entry

# Trong risk_agent.py
stop_loss = latest_price * (1 - self._limits.stop_loss_pct)
take_profit = latest_price * (1 + self._limits.take_profit_pct)
```

---

### 2.3 Tạo IdempotencyPort Interface

**File mới:** [`packages/core/src/core/ports/idempotency.py`](packages/core/src/core/ports/idempotency.py)

**Vấn đề:** Có 2 implementations không có interface chung: in-memory (core) và DuckDB (adapters).

**Fix:**
```python
# packages/core/src/core/ports/idempotency.py
from abc import ABC, abstractmethod

class IdempotencyPort(ABC):
    @abstractmethod
    async def check(self, key: str) -> dict | None: ...

    @abstractmethod
    async def record(self, key: str, result: dict) -> None: ...

    @abstractmethod
    async def prune_expired(self) -> int: ...
```

Cập nhật `place_order.py` để nhận `IdempotencyPort` thay vì `IdempotencyStore`.

---

## 🟡 SPRINT 3 — Medium Priority (Tuần 5-6)

### 3.1 Fix X-Forwarded-For Spoofing

**File:** [`packages/interface/src/interface/middleware/rate_limit.py:72`](packages/interface/src/interface/middleware/rate_limit.py)

**Vấn đề:** Attacker có thể set `X-Forwarded-For: 127.0.0.1` để bypass rate limit.

**Fix:**
```python
TRUSTED_PROXY_NETWORKS = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]

def _get_client_ip(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
    # Chỉ trust X-Forwarded-For từ trusted proxy
    if _is_trusted_proxy(client_host):
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return client_host
```

---

### 3.2 Fix Singleton Pool Race Condition

**File:** [`packages/adapters/src/adapters/duckdb/connection.py:150`](packages/adapters/src/adapters/duckdb/connection.py)

**Vấn đề:** `if _default_pool is None: _default_pool = ...` không thread-safe.

**Fix:**
```python
_pool_lock = threading.Lock()

def get_default_pool(db_path=":memory:", max_connections=5):
    global _default_pool
    if _default_pool is None:
        with _pool_lock:
            if _default_pool is None:  # Double-checked locking
                _default_pool = DuckDBConnectionPool(db_path, max_connections=max_connections)
    return _default_pool
```

---

### 3.3 Configurable Screener Parameters

**File:** [`packages/agents/src/agents/screener_agent.py:60`](packages/agents/src/agents/screener_agent.py)

**Vấn đề:** `min_eps_growth=0.10`, `max_pe_ratio=15.0` hardcoded.

**Fix:** Thêm vào `AgentState`:
```python
class AgentState(TypedDict, total=False):
    screener_min_eps_growth: float   # default 0.10
    screener_max_pe_ratio: float     # default 15.0
    screener_volume_spike_threshold: float  # default 2.0
```

---

### 3.4 Tăng Shutdown Timeout DuckDB Pool

**File:** [`packages/adapters/src/adapters/duckdb/connection.py:117`](packages/adapters/src/adapters/duckdb/connection.py)

**Fix:**
```python
# TRƯỚC
await asyncio.sleep(0.1)

# SAU
await asyncio.sleep(2.0)  # Đủ thời gian cho in-flight queries hoàn thành
```

---

### 3.5 Fix WebSocket Error Logging

**File:** [`frontend/providers/ws-provider.tsx:62`](frontend/providers/ws-provider.tsx)

**Fix:**
```typescript
// TRƯỚC
ws.onerror = () => ws.close();

// SAU
ws.onerror = (event) => {
  console.error("[WS] Connection error:", event);
  ws.close();
};
```

---

## 🟢 SPRINT 4 — Long-term Improvements (Tháng 2-3)

### 4.1 Dead Letter Queue cho Failed Orders

**Vấn đề:** Khi broker call thất bại trong `executor_agent.py:139`, lệnh bị drop hoàn toàn.

**Giải pháp:**
- Tạo `DLQStore` (DuckDB-backed) lưu failed orders
- Background task retry với exponential backoff
- Telegram notification khi order vào DLQ

---

### 4.2 Khai Báo Optional Dependencies

**File:** [`pyproject.toml`](pyproject.toml)

**Fix:**
```toml
[project.optional-dependencies]
full = [
    "pandas-ta>=0.3.14b",
    "pandas>=2.0",
]
```

---

### 4.3 OpenTelemetry cho DuckDB Queries

**Vấn đề:** Chỉ có agent-level metrics, không có database query tracing.

**Giải pháp:** Wrap DuckDB connection pool với OpenTelemetry spans:
```python
with tracer.start_as_current_span("duckdb.query") as span:
    span.set_attribute("db.statement", sql[:100])
    result = conn.execute(sql, params)
```

---

### 4.4 Async Factory cho DuckDBIdempotencyStore

**File:** [`packages/adapters/src/adapters/duckdb/idempotency_store.py:28`](packages/adapters/src/adapters/duckdb/idempotency_store.py)

**Fix:**
```python
@classmethod
async def create(cls, conn, max_age_hours=24):
    store = cls.__new__(cls)
    store._conn = conn
    store._max_age_hours = max_age_hours
    await asyncio.to_thread(conn.execute, _DDL)
    return store
```

---

### 4.5 UI/UX Improvements (Frontend)

- [x] Di chuyển `MarketIndexBar` xuống footer của Market Board page
- [x] Xóa `TradingChart` khỏi Dashboard — click vào mã CP để mở chart page
- [ ] Optimistic updates cho order placement
- [ ] Dark/light theme toggle
- [ ] Keyboard shortcuts (đã có command palette, mở rộng thêm)

---

## 📊 Tóm Tắt Timeline

| Sprint | Thời gian | Mục tiêu | Effort |
|--------|-----------|----------|--------|
| Sprint 1 | Tuần 1-2 | Fix 2 critical bugs | 2 ngày |
| Sprint 2 | Tuần 3-4 | Refactor risk/position logic | 5 ngày |
| Sprint 3 | Tuần 5-6 | Security + stability fixes | 4 ngày |
| Sprint 4 | Tháng 2-3 | Long-term improvements | 2-3 tuần |

---

## 🎯 Metrics Thành Công

- [ ] Zero critical bugs trong production
- [ ] Test coverage ≥ 85% (hiện tại ~80% ước tính)
- [ ] P95 latency agent pipeline < 5s
- [ ] Zero X-Forwarded-For bypass incidents
- [ ] DuckDB pool không bao giờ race condition trong load test

---

*Cập nhật lần cuối: 2026-02-28*
