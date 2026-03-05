# ROADMAP — Improved Algo-Trading System

> Compiled from independent code reviews. Prioritize according to impact on correctness and security.

---

## 🔴 SPRINT 1 — Critical Fixes (Weeks 1-2)

### 1.1 Fix Entry Price Logic trong ExecutorAgent

**File:** [`packages/agents/src/agents/executor_agent.py:45`](packages/agents/src/agents/executor_agent.py)

**Problem:** `entry_price = risk.take_profit_price` — use take-profit price (+10%) as order price. The LO order will match immediately at the market price but `_calculate_quantity` calculates the wrong quantity.

**Fix:**
```python
# Add latest_price field to RiskAssessment
@dataclass(frozen=True, slots=True)
class RiskAssessment:
    latest_price: Decimal  # ★ NEW: actual market price
    stop_loss_price: Decimal   # = latest_price * (1 - stop_loss_pct)
    take_profit_price: Decimal # = latest_price * (1 + take_profit_pct)
    ...

# Trong executor_agent.py
entry_price = risk.latest_price # ★ FIX: use actual market price
```

**Test:** Add unit test to check `entry_price == latest_price` in `test_executor_agent.py`.

---

### 1.2 Fix Float Conversion trong ExecutorAgent

**File:** [`packages/agents/src/agents/executor_agent.py:135`](packages/agents/src/agents/executor_agent.py)

**Problem:** `price=float(price)` — loss of Decimal precision at a large VND cost (e.g. 98,500 VND).

**Fix:**
```python
# BEFORE
price=float(price),

# SAU
price=str(price), # Consistent with SSI broker "★ String, not float"
```

---

## 🟠 SPRINT 2 — High Priority (Weeks 3-4)

### 2.1 Refactor Position Size Calculation

**File:** [`packages/agents/src/agents/risk_agent.py:162`](packages/agents/src/agents/risk_agent.py)

**Problem:** `purchasing_power / nav` does not take into account actual stock prices.

**Fix:**
```python
def _calculate_position_size(
    self,
    nav: Decimal,
    purchasing_power: Decimal,
    latest_price: Decimal,
    max_pct: Decimal,
) -> Decimal:
"""Calculate the actual % NAV that will be used for this command."""
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

**Problem:** Stop-loss = -7% = HOSE price band floor → never triggered in a session.

**Fix:**
```python
# Trong core/entities/risk.py
@dataclass(frozen=True, slots=True)
class RiskLimit:
    max_position_pct: Decimal
    max_daily_loss: Decimal
    kill_switch_active: bool
stop_loss_pct: Decimal = Decimal("0.05") # ★ NEW: 5% below entry
take_profit_pct: Decimal = Decimal("0.15") # ★ NEW: 15% on entry

# Trong risk_agent.py
stop_loss = latest_price * (1 - self._limits.stop_loss_pct)
take_profit = latest_price * (1 + self._limits.take_profit_pct)
```

---

### 2.3 Create IdempotencyPort Interface

**New file:** [`packages/core/src/core/ports/idempotency.py`](packages/core/src/core/ports/idempotency.py)

**Problem:** There are 2 implementations that do not have a common interface: in-memory (core) and DuckDB (adapters).

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

Update `place_order.py` to receive `IdempotencyPort` instead of `IdempotencyStore`.

---

## 🟡 SPRINT 3 — Medium Priority (Weeks 5-6)

### 3.1 Fix X-Forwarded-For Spoofing

**File:** [`packages/interface/src/interface/middleware/rate_limit.py:72`](packages/interface/src/interface/middleware/rate_limit.py)

**Problem:** Attacker can set `X-Forwarded-For: 127.0.0.1` to bypass rate limit.

**Fix:**
```python
TRUSTED_PROXY_NETWORKS = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]

def _get_client_ip(request: Request) -> str:
    client_host = request.client.host if request.client else "unknown"
# Only trust X-Forwarded-For from trusted proxies
    if _is_trusted_proxy(client_host):
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return client_host
```

---

### 3.2 Fix Singleton Pool Race Condition

**File:** [`packages/adapters/src/adapters/duckdb/connection.py:150`](packages/adapters/src/adapters/duckdb/connection.py)

**Problem:** `if _default_pool is None: _default_pool = ...` is not thread-safe.

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

**Problem:** `min_eps_growth=0.10`, `max_pe_ratio=15.0` hardcoded.

**Fix:** Added `AgentState`:
```python
class AgentState(TypedDict, total=False):
    screener_min_eps_growth: float   # default 0.10
    screener_max_pe_ratio: float     # default 15.0
    screener_volume_spike_threshold: float  # default 2.0
```

---

### 3.4 Increase DuckDB Pool Shutdown Timeout

**File:** [`packages/adapters/src/adapters/duckdb/connection.py:117`](packages/adapters/src/adapters/duckdb/connection.py)

**Fix:**
```python
# BEFORE
await asyncio.sleep(0.1)

# SAU
await asyncio.sleep(2.0) # Enough time for in-flight queries to complete
```

---

### 3.5 Fix WebSocket Error Logging

**File:** [`frontend/providers/ws-provider.tsx:62`](frontend/providers/ws-provider.tsx)

**Fix:**
```typescript
// BEFORE
ws.onerror = () => ws.close();

// SAU
ws.onerror = (event) => {
  console.error("[WS] Connection error:", event);
  ws.close();
};
```

---

## 🟢 SPRINT 4 — Long-term Improvements (February-March)

### 4.1 Dead Letter Queue cho Failed Orders

**Problem:** When broker call fails in `executor_agent.py:139`, the order is completely dropped.

**Solution:**
- Create `DLQStore` (DuckDB-backed) to store failed orders
- Background task retry with exponential backoff
- Telegram notification when order entered DLQ

---

### 4.2 Declaring Optional Dependencies

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

**Problem:** Only agent-level metrics, no database query tracing.

**Solution:** Wrap DuckDB connection pool with OpenTelemetry spans:
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

- [x] Move `MarketIndexBar` to the footer of the Market Board page
- [x] Delete `TradingChart` from Dashboard — click on the stock code to open the chart page
- [ ] Optimistic updates cho order placement
- [ ] Dark/light theme toggle
- [ ] Keyboard shortcuts (command palette already available, expandable)

---

## 📊 Timeline Summary

| Sprint |Time|Target| Effort |
|--------|-----------|----------|--------|
| Sprint 1 |Week 1-2| Fix 2 critical bugs |2 days|
| Sprint 2 |Week 3-4| Refactor risk/position logic |5 days|
| Sprint 3 |Week 5-6| Security + stability fixes |4 days|
| Sprint 4 |February-March| Long-term improvements |2-3 weeks|

---

## 🎯 Success Metrics

- [ ] Zero critical bugs trong production
- [ ] Test coverage ≥ 85% (latest release validation snapshot on gated scope: frontend lines 99.4%, backend critical 97.51%)
- [ ] P95 latency agent pipeline < 5s
- [ ] Zero X-Forwarded-For bypass incidents
- [ ] DuckDB pool never race condition in load test

---

*Last updated: 2026-03-05*
