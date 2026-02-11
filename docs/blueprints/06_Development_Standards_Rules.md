# 06 — DEVELOPMENT STANDARDS & RULES

**Project:** Hệ thống Giao dịch Thuật toán Đa Tác vụ (Enterprise Edition)
**Role:** Tech Lead — Final Authority on Code Quality
**Version:** 1.0 | February 2026
**Status:** MANDATORY — Every line of code in this repo MUST comply.

---

> **This document is LAW.** It is loaded into Cursor's context at the start of every coding session. Every AI assistant and every human developer writes code that obeys these rules — no exceptions, no shortcuts, no "I'll fix it later."

---

## 0. THE VIBE CODE — PROJECT IDENTITY

### 0.1. Core Philosophy

This is not a toy project. This is a **financial trading system** where bugs cost real money. Every design choice follows three pillars:

```
╔══════════════════════════════════════════════════════════════════════╗
║                     THE THREE PILLARS                                ║
║                                                                      ║
║  1. EXPLICIT IS BETTER THAN IMPLICIT                                ║
║     No magic. No hidden state. No clever tricks.                    ║
║     If a reader can't understand what code does in 10 seconds,      ║
║     the code is wrong — not the reader.                             ║
║                                                                      ║
║  2. TYPE-SAFETY FIRST                                                ║
║     Types are documentation that the compiler enforces.             ║
║     If it compiles (mypy --strict / tsc --strict), it's probably    ║
║     correct. If it doesn't compile, it's definitely wrong.          ║
║                                                                      ║
║  3. FUNCTION OVER CLASS (WHERE APPROPRIATE)                          ║
║     A pure function is easier to test, easier to reason about,      ║
║     and impossible to break via inheritance. Use classes ONLY        ║
║     when you need state or lifecycle (adapters, agents, services).  ║
║     Business logic = functions. Infrastructure = classes.            ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 0.2. Decision Hierarchy — When Rules Conflict

When two principles conflict, resolve in this order:

```
Priority 1: CORRECTNESS    — Code must produce correct financial results.
                             A wrong number in a trading system is catastrophic.
Priority 2: SAFETY         — Code must not lose money, leak data, or crash.
                             Defensive coding > elegant coding.
Priority 3: READABILITY    — Code must be understood by the NEXT developer
                             (or the NEXT AI). Write for humans first.
Priority 4: PERFORMANCE    — Code must meet latency targets (see Section 6).
                             Optimize only AFTER profiling, NEVER by gut feeling.
Priority 5: CONCISENESS    — Shorter code is better ONLY if it doesn't sacrifice
                             the above four priorities.
```

### 0.3. Audience Awareness

This codebase is read by:
1. **Human developers** — must understand intent without running the code.
2. **AI assistants (Cursor)** — must have unambiguous context to generate correct code.
3. **`mypy --strict` / `tsc --strict`** — must pass without `# type: ignore` hacks.
4. **Future-you at 2 AM debugging a production issue** — be kind to that person.

---

## 1. CODING STANDARDS — PYTHON

### 1.1. The Non-Negotiables

```
TOOLCHAIN (enforced in CI — PR cannot merge if any fail):
  Formatter:    Ruff (format)     — zero config debates, just run it
  Linter:       Ruff (check)      — replaces flake8, isort, pyupgrade, 30+ tools
  Type checker: mypy --strict     — EVERY function typed, EVERY return typed
  Python:       3.12+             — use modern syntax (X | Y, match/case, etc.)
  Runner:       uv                — NOT pip, NOT poetry, NOT conda
```

### 1.2. Type Hinting — Absolute Requirements

```python
# ══════════════════════════════════════════════════════════════
# REQUIRED: Every function signature MUST be fully typed.
# mypy --strict rejects untyped functions.
# ══════════════════════════════════════════════════════════════

# ✅ CORRECT — fully typed, modern syntax
from __future__ import annotations
from decimal import Decimal
from typing import TYPE_CHECKING, NewType

if TYPE_CHECKING:
    from core.entities.tick import Tick

Symbol = NewType("Symbol", str)
Price = NewType("Price", Decimal)

def calculate_pnl(
    buy_price: Price,
    sell_price: Price,
    quantity: int,
) -> Decimal:
    return (sell_price - buy_price) * quantity

def find_position(symbol: Symbol) -> Position | None:  # Union with |, not Optional
    ...

async def fetch_ticks(symbols: list[Symbol]) -> dict[Symbol, Tick]:
    ...


# ❌ BANNED — will be rejected by mypy and in code review
def calculate_pnl(buy_price, sell_price, quantity):  # No types
    ...

def find_position(symbol) -> Optional[Position]:  # Old-style Optional
    ...

def process(data: Any) -> Any:  # Any = giving up on type safety
    ...

def get_items() -> List[Dict[str, Any]]:  # Old generics, Any
    ...
```

### 1.3. Data Modeling — Entities & Value Objects

```python
# ══════════════════════════════════════════════════════════════
# RULE: Domain objects MUST be frozen dataclasses.
# RULE: Financial values MUST use Decimal, NEVER float.
# RULE: Domain primitives MUST use NewType.
# ══════════════════════════════════════════════════════════════

# ✅ CORRECT
from dataclasses import dataclass
from decimal import Decimal
from typing import NewType

Symbol = NewType("Symbol", str)
Price = NewType("Price", Decimal)
Quantity = NewType("Quantity", int)

@dataclass(frozen=True, slots=True)
class Order:
    order_id: str
    symbol: Symbol
    price: Price         # Decimal — exact financial arithmetic
    quantity: Quantity
    # frozen=True → immutable after creation → thread-safe
    # slots=True → 30-40% less memory


# ❌ BANNED
class Order:               # Not a dataclass
    def __init__(self, ...):
        self.price = 98.5  # float for money — IEEE 754 rounding errors
        self.data = {}     # dict instead of typed fields

order.price = 99.0         # Mutation — breaks immutability invariant
```

### 1.4. Function Design — Pure First

```python
# ══════════════════════════════════════════════════════════════
# RULE: Business logic MUST be pure functions.
# Pure function = same input → same output, no side effects.
# Pure functions need NO mocks to test.
# ══════════════════════════════════════════════════════════════

# ✅ CORRECT — pure function, trivially testable
def validate_lot_size(quantity: int) -> tuple[bool, str]:
    if quantity % 100 != 0:
        return False, f"Quantity {quantity} not a multiple of 100"
    return True, "Valid"


# ✅ CORRECT — pure function, no I/O
def calculate_technical_score(
    rsi: float,
    macd_signal: str,
    bb_position: str,
) -> float:
    score = 0.0
    if rsi < 30:
        score += 3.0
    # ... deterministic scoring logic
    return score


# ❌ WRONG — impure, side effects, hard to test
def validate_and_save_order(order):
    if order.quantity % 100 != 0:
        logger.error("Bad lot size")        # Side effect: logging
        db.save_error(order)                # Side effect: database write
        send_email("admin@co.vn", "error")  # Side effect: email
        return False
    db.save(order)                          # Side effect
    return True
    # Testing this requires mocking logger, db, email — fragile
```

### 1.5. Async Discipline

```python
# ══════════════════════════════════════════════════════════════
# RULE: Never block the asyncio event loop.
# Blocking call > 1ms MUST be offloaded to thread/process pool.
# ══════════════════════════════════════════════════════════════

# ✅ CORRECT
await asyncio.sleep(1.0)                                    # Non-blocking
await httpx_client.get("https://api.ssi.com.vn/...")        # Async HTTP
result = await asyncio.to_thread(duckdb_conn.execute, sql)  # Offload blocking C FFI
score = await loop.run_in_executor(process_pool, compute)   # Offload CPU-bound

# ❌ BANNED — instant code review rejection
import time; time.sleep(1.0)       # Blocks entire event loop
import requests; requests.get(url) # Blocking I/O
duckdb_conn.execute(sql)           # Blocking C call on event loop
```

### 1.6. Import Style

```python
# ══════════════════════════════════════════════════════════════
# RULE: Imports follow strict order (enforced by Ruff).
# RULE: Use TYPE_CHECKING to break circular imports.
# RULE: from __future__ import annotations in EVERY file.
# ══════════════════════════════════════════════════════════════

from __future__ import annotations           # 1. Future annotations (ALWAYS first)

import asyncio                                # 2. Standard library
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

import httpx                                  # 3. Third-party
from pydantic import BaseModel

from core.entities.order import Order         # 4. First-party (our packages)
from core.value_objects import Price, Symbol

if TYPE_CHECKING:                             # 5. Type-checking only imports
    from core.ports.repository import OrderRepository
```

### 1.7. Ruff Configuration

```toml
# ruff.toml (workspace root — shared across all packages)
target-version = "py312"
line-length = 99

[lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade (modernize syntax)
    "B",      # flake8-bugbear (common bugs)
    "S",      # flake8-bandit (security)
    "C4",     # flake8-comprehensions
    "SIM",    # flake8-simplify
    "TCH",    # flake8-type-checking (TYPE_CHECKING blocks)
    "RUF",    # Ruff-specific rules
    "ASYNC",  # flake8-async (async anti-patterns)
    "PT",     # flake8-pytest-style
]
ignore = [
    "S101",   # assert is fine in tests
    "S311",   # random is fine for jitter (not crypto)
]

[lint.per-file-ignores]
"tests/**" = ["S101", "S106"]  # Allow assert and hardcoded passwords in tests

[format]
quote-style = "double"
indent-style = "space"
```

### 1.8. mypy Configuration

```ini
# mypy.ini (workspace root)
[mypy]
python_version = 3.12
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
disallow_untyped_calls = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
check_untyped_defs = true
show_error_codes = true

# Per-package overrides for third-party libs without stubs
[mypy-duckdb.*]
ignore_missing_imports = true
[mypy-pandas_ta.*]
ignore_missing_imports = true
[mypy-vnstock.*]
ignore_missing_imports = true
[mypy-openvino_genai.*]
ignore_missing_imports = true
```

---

## 2. CODING STANDARDS — TYPESCRIPT / FRONTEND

### 2.1. The Non-Negotiables

```
TOOLCHAIN (enforced in CI):
  Language:     TypeScript 5.6+, strict mode
  Framework:    Next.js 15 (App Router), React 19
  Linter:       ESLint (strict + next/core-web-vitals)
  Formatter:    Prettier (via ESLint plugin)
  State:        Zustand (NOT React Context for real-time data)
  Styling:      Tailwind CSS 4 + Shadcn UI
  Type check:   tsc --noEmit --strict
```

### 2.2. TypeScript Strict Rules

```typescript
// tsconfig.json — MANDATORY settings
{
  "compilerOptions": {
    "strict": true,                       // Enables ALL strict checks below:
    // "noImplicitAny": true,             //   ← included in strict
    // "strictNullChecks": true,          //   ← included in strict
    // "strictFunctionTypes": true,       //   ← included in strict
    // "strictPropertyInitialization": true, // ← included in strict
    "noUncheckedIndexedAccess": true,     // array[i] is T | undefined, not T
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "exactOptionalPropertyTypes": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

### 2.3. The `any` Ban

```typescript
// ══════════════════════════════════════════════════════════════
// RULE: `any` is BANNED in this codebase. Zero tolerance.
// If you need dynamic types, use `unknown` and narrow.
// ══════════════════════════════════════════════════════════════

// ✅ CORRECT — unknown + type guard
function parseMessage(raw: unknown): TickData {
  if (!isTickData(raw)) {
    throw new Error(`Invalid tick data: ${JSON.stringify(raw)}`);
  }
  return raw;
}

function isTickData(value: unknown): value is TickData {
  return (
    typeof value === "object" &&
    value !== null &&
    "symbol" in value &&
    "price" in value &&
    typeof (value as Record<string, unknown>).symbol === "string" &&
    typeof (value as Record<string, unknown>).price === "number"
  );
}


// ❌ BANNED — every one of these triggers CI failure
function parseMessage(raw: any): any { ... }
const data = response.json() as any;
// @ts-ignore
// @ts-expect-error — allowed ONLY with a comment explaining WHY
```

### 2.4. Interface & Type Naming

```typescript
// ══════════════════════════════════════════════════════════════
// RULE: Interfaces for object shapes. Types for unions/intersections.
// RULE: No "I" prefix on interfaces. We are not writing C#.
// RULE: Props types suffixed with "Props".
// ══════════════════════════════════════════════════════════════

// ✅ CORRECT
interface TickData {          // Object shape → interface
  symbol: string;
  price: number;
  volume: number;
  timestamp: number;
}

interface PriceBoardProps {   // Component props → interface + "Props" suffix
  symbols: string[];
  onSymbolSelect: (symbol: string) => void;
}

type OrderAction = "BUY" | "SELL" | "HOLD";  // Union → type alias
type ApiResponse<T> = { data: T; error: null } | { data: null; error: string };


// ❌ BANNED
interface ITickData { ... }   // No "I" prefix
interface ITradingService { ... }
type TickDataType = { ... };  // Don't suffix types with "Type"
```

### 2.5. Component Conventions

```typescript
// ══════════════════════════════════════════════════════════════
// RULE: "use client" ONLY on components that need browser APIs.
// RULE: Server Components by default — client is the exception.
// RULE: Name component files in kebab-case: price-board.tsx
// RULE: One exported component per file.
// ══════════════════════════════════════════════════════════════

// ✅ CORRECT — Client Component (needs browser APIs)
// File: _components/price-board.tsx
"use client";

import { useRef } from "react";

interface PriceBoardProps {
  symbols: string[];
}

export function PriceBoard({ symbols }: PriceBoardProps) {
  const gridRef = useRef(null);
  return <div>{/* AG Grid */}</div>;
}


// ✅ CORRECT — Server Component (NO "use client", NO hooks, NO browser APIs)
// File: app/(dashboard)/page.tsx
import { Suspense } from "react";
import { PriceBoard } from "./_components/price-board";

export default function DashboardPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <PriceBoard symbols={["FPT", "VNM"]} />
    </Suspense>
  );
}


// ❌ BANNED
"use client";  // on a component that doesn't use useState/useEffect/browser APIs
export default function SettingsPage() {    // Static page doesn't need client JS
  return <div>Settings</div>;
}
```

---

## 3. ARCHITECTURE RULES — THE LAW OF LAYERS

### 3.1. Dependency Direction (ONE WAY ONLY)

```
interface ──► agents ──► adapters ──► core
                │                      ▲
                └──────────────────────┘

★ RULE: core    NEVER imports from adapters, agents, or interface.
★ RULE: adapters NEVER imports from agents or interface.
★ RULE: agents  NEVER imports from interface.
★ RULE: interface wires everything together (Dependency Injection).

VIOLATION = IMMEDIATE PR REJECTION. No exceptions.
```

### 3.2. What Goes Where

| Layer | Contains | May Import From | Examples |
|:---|:---|:---|:---|
| **core** | Entities, Value Objects, Ports (Protocol), Use Cases | Standard library only | `Order`, `Tick`, `validate_order()`, `MarketDataPort` |
| **adapters** | Infrastructure implementations | core | `DuckDBTickRepository`, `SSIAuthClient`, `OpenVINOEngine` |
| **agents** | LangGraph nodes, Agent business logic | core, adapters | `ScreenerAgent`, `TechnicalAgent`, `supervisor.py` |
| **interface** | FastAPI routes, WebSocket handlers, CLI, DI wiring | core, adapters, agents | `app.py`, `dependencies.py`, `/ws/market` |

### 3.3. Test Layer Rules

| Test Type | What It Tests | May Use | Speed Target |
|:---|:---|:---|:---|
| **Unit (core)** | Pure functions, entities, use cases | Nothing (no mocks, no I/O) | < 5ms/test |
| **Unit (agents)** | Routing logic, state transforms | Mock ports (fake classes) | < 20ms/test |
| **Integration** | Adapter + real DuckDB (`:memory:`) | DuckDB in-memory, mock network | < 100ms/test |
| **E2E** | Full pipeline, API endpoints | Real server (test mode) | < 5s/test |

---

## 4. COMMIT & PR RULES — CONVENTIONAL COMMITS

### 4.1. Commit Message Format (Mandatory)

```
<type>(<scope>): <description>

[optional body — explain WHY, not WHAT]

[optional footer — BREAKING CHANGE, ticket refs]
```

### 4.2. Allowed Types

| Type | Meaning | Example |
|:---|:---|:---|
| `feat` | New feature (user-facing) | `feat(screener): add volume spike detection` |
| `fix` | Bug fix | `fix(oms): prevent duplicate orders on timeout retry` |
| `refactor` | Code restructure (no behavior change) | `refactor(core): extract price band logic to use case` |
| `perf` | Performance improvement | `perf(duckdb): add partition pruning to tick queries` |
| `test` | Add/update tests | `test(risk): add T+2.5 settlement edge cases` |
| `docs` | Documentation | `docs: update 06_Development_Standards_Rules.md` |
| `build` | Build system, dependencies | `build: upgrade duckdb to 1.2.0` |
| `ci` | CI/CD changes | `ci: add mypy --strict to pre-commit` |
| `chore` | Routine maintenance | `chore: clean up unused imports` |
| `security` | Security fix or hardening | `security(auth): rotate RSA key encryption to AES-256-GCM` |

### 4.3. Allowed Scopes

```
core, adapters, agents, interface, frontend
ssi, dnse, duckdb, openvino, vnstock
screener, technical, risk, executor, fundamental
oms, auth, ws, grid, chart
```

### 4.4. Commit Rules (Enforced by Git Hook)

```
★ RULE: Subject line ≤ 72 characters.
★ RULE: Subject in imperative mood: "add feature" not "added feature".
★ RULE: No period at end of subject line.
★ RULE: Body wraps at 80 characters.
★ RULE: One logical change per commit. Atomic commits.
★ RULE: NEVER commit: .env, *.pem, *.key, data/, node_modules/, __pycache__/
```

### 4.5. Examples

```bash
# ✅ GOOD commits
git commit -m "feat(screener): add EPS growth filter to stock screening pipeline"
git commit -m "fix(oms): use idempotency key to prevent duplicate orders on retry"
git commit -m "refactor(core): split risk_check into price_band and settlement modules"
git commit -m "perf(duckdb): switch ASOF JOIN to use pre-sorted tick partitions"
git commit -m "test(risk): cover ceiling/floor validation for all 3 exchanges"
git commit -m "security(auth): encrypt RSA private key at rest with AES-256-GCM"

# ❌ BAD commits — will be rejected
git commit -m "fix stuff"                    # No type, no scope, no description
git commit -m "WIP"                          # No WIP commits on main/develop
git commit -m "feat: added new feature."     # Past tense, period, vague
git commit -m "Updated multiple files"       # What? Why? Which files?
```

### 4.6. Pull Request Rules

```
PR REQUIREMENTS (all must pass before merge):
══════════════════════════════════════════════════════════════════

  □ Title follows Conventional Commit format
  □ Description explains WHY (not just WHAT)
  □ All CI checks pass:
    ├── Python: ruff check + ruff format --check + mypy --strict
    ├── TypeScript: tsc --noEmit + eslint
    ├── Tests: pytest (unit + integration) + vitest
    └── Coverage: ≥ 85% (core), ≥ 80% (adapters), ≥ 80% (frontend)
  □ No increase in `# type: ignore` count
  □ No increase in `as any` / `@ts-ignore` count
  □ No decrease in test coverage
  □ No new linter warnings
  □ Reviewed by at least 1 team member (or Tech Lead for security-critical)

SECURITY-CRITICAL PRs (auth, orders, risk, money):
  □ Reviewed by Tech Lead personally
  □ Test coverage ≥ 95% for changed code
  □ No new dependencies without security audit
```

---

## 5. DEFINITION OF DONE (DoD) — WHEN IS A FEATURE "DONE"?

### 5.1. The Checklist — ALL Items Must Be True

A feature, bug fix, or refactor is only "Done" when:

```
DEFINITION OF DONE
══════════════════════════════════════════════════════════════════

CODE QUALITY
  □ Code compiles with zero errors:
    ├── Python: mypy --strict passes
    └── TypeScript: tsc --noEmit passes
  □ Linter passes with zero warnings:
    ├── Python: ruff check passes
    └── TypeScript: eslint passes
  □ Code formatted:
    ├── Python: ruff format (no diff)
    └── TypeScript: prettier (no diff)
  □ No `# type: ignore` added without specific error code + comment
  □ No `any` types in TypeScript
  □ No `float` used for financial values (use Decimal)

TESTING
  □ Unit tests written for ALL new pure functions
  □ Integration tests written for adapter/database interactions
  □ Edge cases covered:
    ├── Empty input
    ├── Null/None values
    ├── Boundary values (0, max, negative)
    └── Error cases (network failure, invalid data)
  □ All existing tests still pass (no regressions)
  □ Coverage not decreased from baseline

PERFORMANCE
  □ No blocking calls on asyncio event loop
  □ DuckDB queries tested with expected data volume (~1M rows)
  □ AG Grid updates verified at ≥ 55fps with 1,800 rows
  □ Bundle size not increased beyond budget (< 500 KB gzipped)
  □ No N+1 query patterns introduced

SECURITY (if applicable)
  □ No credentials in code or logs
  □ Input validated (Pydantic for Python, Zod/type guards for TS)
  □ Price band / T+2.5 rules enforced if order-related
  □ Idempotency key used for order submissions

DOCUMENTATION
  □ Complex logic has inline comments explaining WHY (not WHAT)
  □ Public functions have docstrings (Python) or JSDoc (TypeScript)
  □ Architecture docs updated if structural changes made
```

### 5.2. NOT Done — Common Traps

```
"It works on my machine"          → NOT done. Must pass CI.
"Tests pass but linter has errors" → NOT done. Fix linting first.
"I'll add tests later"            → NOT done. Tests are NOT optional.
"It's just a small change"        → NOT done until DoD is checked.
"The AI generated it so it's fine" → NOT done. AI code is reviewed to
                                     SAME standard as human code.
```

---

## 6. PERFORMANCE CONTRACTS — NON-NEGOTIABLE TARGETS

### 6.1. Backend Latency Budgets

| Operation | Target | Hard Limit | Measured At |
|:---|:---|:---|:---|
| Tick ingestion (WebSocket → buffer) | < 0.5ms | < 2ms | `DataAgent._ingest_loop` |
| Buffer flush (batch → DuckDB) | < 50ms / 1000 rows | < 200ms | `DataAgent._flush_buffer` |
| Screener scan (full market) | < 500ms | < 2s | `ScreenerAgent.run` |
| Technical scoring (1 symbol) | < 200ms | < 500ms | `TechnicalAgent._compute` |
| Risk validation (1 order) | < 50ms | < 200ms | `validate_order()` |
| ASOF JOIN (100K orders × 10M ticks) | < 300ms | < 1s | DuckDB query |
| NPU inference (200-token response) | < 10s | < 15s | `OpenVINOEngine.generate` |
| Full pipeline (Screener → Executor) | < 3s | < 5s | `run_trading_pipeline` |

### 6.2. Frontend Performance Budgets

| Metric | Target | Hard Limit | Tool |
|:---|:---|:---|:---|
| First Contentful Paint (FCP) | < 0.5s | < 1.0s | Lighthouse |
| Time to Interactive (TTI) | < 1.0s | < 2.0s | Lighthouse |
| AG Grid frame rate (1,800 rows) | ≥ 55fps | ≥ 45fps | Chrome DevTools |
| DOM nodes (price board) | < 800 | < 1,200 | Chrome DevTools |
| JS bundle (gzipped) | < 400 KB | < 500 KB | `next build` output |
| WebSocket → Store → Grid update | < 16ms | < 33ms | `performance.mark()` |

### 6.3. Violation Protocol

```
If a PR causes ANY metric to breach its Hard Limit:
  1. PR is BLOCKED from merge.
  2. Author must profile, identify root cause, and fix.
  3. If fix is non-trivial, create a tech debt ticket with deadline.
  4. Tech Lead approves temporary waiver ONLY with documented justification.
```

---

## 7. PRE-CODING CHECKLIST — THE FIVE QUESTIONS

**Before writing ANY code** — whether you are a human developer or an AI assistant — you MUST mentally answer these five questions. If any answer is "no" or "I don't know," STOP and resolve it before touching the keyboard.

### 7.1. The Five Questions

```
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║  Q1. WHERE DOES THIS CODE LIVE IN THE ARCHITECTURE?                  ║
║  ─────────────────────────────────────────────────────────────────── ║
║  "Am I in core, adapters, agents, or interface?"                    ║
║  "Am I violating the dependency direction?"                         ║
║  "Does this import something from a layer it shouldn't?"            ║
║                                                                      ║
║  If you're writing business logic that imports FastAPI → WRONG.     ║
║  If you're writing a use case that imports DuckDB → WRONG.          ║
║  Business logic goes in core. DuckDB goes in adapters.              ║
║                                                                      ║
║  Q2. WHAT HAPPENS WHEN THE NETWORK FAILS?                           ║
║  ─────────────────────────────────────────────────────────────────── ║
║  "Does this code call an external API (SSI, DNSE, Vnstock)?"       ║
║  "What if the request times out?"                                   ║
║  "What if the response is malformed JSON?"                          ║
║  "What if the WebSocket disconnects mid-message?"                   ║
║                                                                      ║
║  If you're calling a network API without timeout + retry → WRONG.   ║
║  If you're placing an order without idempotency key → WRONG.        ║
║  If you're not handling ConnectionError → WRONG.                    ║
║                                                                      ║
║  Q3. DOES THIS HANDLE MONEY CORRECTLY?                              ║
║  ─────────────────────────────────────────────────────────────────── ║
║  "Am I using Decimal for all financial calculations?"               ║
║  "Am I checking ceiling/floor price before submitting an order?"    ║
║  "Am I using sellableQty (not onHand) for sell validation?"         ║
║  "Am I enforcing lot size = 100?"                                   ║
║  "Could this code accidentally place a duplicate order?"            ║
║                                                                      ║
║  If you're using float for prices → WRONG.                          ║
║  If you're skipping price band validation → WRONG.                  ║
║  If you're trusting onHand for sell quantity → WRONG (T+2.5).       ║
║                                                                      ║
║  Q4. WILL THIS SCALE TO PRODUCTION DATA VOLUME?                     ║
║  ─────────────────────────────────────────────────────────────────── ║
║  "Will this query run fast on 1 million tick rows?"                 ║
║  "Am I looping in Python where I should be using DuckDB SQL?"       ║
║  "Am I creating N+1 queries (1 query per symbol in a loop)?"        ║
║  "Am I blocking the event loop with a CPU-bound calculation?"       ║
║                                                                      ║
║  If you're iterating 1,800 symbols in a Python for-loop to          ║
║  compute indicators → WRONG. Push it to DuckDB vectorized SQL.      ║
║  If you're calling await db.query() inside a for-loop → WRONG.      ║
║  Batch it.                                                           ║
║                                                                      ║
║  Q5. HOW WILL SOMEONE TEST THIS?                                    ║
║  ─────────────────────────────────────────────────────────────────── ║
║  "Can this function be tested WITHOUT mocks?"                       ║
║  "If it needs a mock, can I simplify the design?"                   ║
║  "What are the edge cases? (zero, null, max, negative, empty)"     ║
║  "Does a test for this already exist? Am I about to break it?"     ║
║                                                                      ║
║  If testing requires 5+ mocks → design is wrong. Simplify.         ║
║  If you can't write a test in < 30 seconds → function does too much.║
║  Split it.                                                           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 7.2. Quick Decision Matrix

```
I need to...                  → Do this                    → NOT this
──────────────────────────────────────────────────────────────────────
Store a price                 → Decimal("98.50")           → 98.5 (float)
Define an entity              → @dataclass(frozen=True)    → plain class / dict
Add business rule             → pure function in core/     → method on adapter
Call DuckDB                   → await asyncio.to_thread()  → direct conn.execute()
Call SSI API                  → httpx + retry + timeout    → requests.get() bare
Validate order price          → check ceiling/floor FIRST  → send to broker and hope
Sell shares                   → check sellableQty          → check onHand
Place order with retry        → idempotency_key            → pray for no duplicates
Handle WebSocket disconnect   → exponential backoff        → while True: reconnect()
Pass data between layers      → Protocol (Port)            → direct import of adapter
Make a type optional          → Price | None               → Optional[Price]
Skip type checking            → NEVER                      → # type: ignore
Use dynamic typing            → unknown + type guard (TS)  → any
Use global mutable state      → Dependency Injection       → module-level dict/list
Log an error                  → logger.exception()         → print() / pass
Sleep in async code           → await asyncio.sleep()      → time.sleep()
```

---

## 8. BANNED PATTERNS — CONSOLIDATED BLACKLIST

This is the single authoritative list of all banned patterns across the entire codebase. Sourced from Documents 02, 03, 04, and 05.

### 8.1. Python — Banned

| # | Pattern | Why It's Banned | Correct Alternative |
|:---|:---|:---|:---|
| P01 | `import requests` | Blocking I/O — freezes event loop | `import httpx` (async client) |
| P02 | `time.sleep(n)` | Blocks event loop | `await asyncio.sleep(n)` |
| P03 | `float` for financial values | IEEE 754: `0.1 + 0.2 != 0.3` | `Decimal` |
| P04 | `dict` for domain objects | No type safety, mutable | `@dataclass(frozen=True, slots=True)` |
| P05 | Global mutable state | Thread-unsafe, untestable | Dependency injection |
| P06 | `except Exception: pass` | Silently swallows real bugs | Catch specific exceptions, log them |
| P07 | `# type: ignore` bare | Hides real type errors | Fix the type, or `# type: ignore[specific-code]` with comment |
| P08 | `from typing import Optional, List, Dict` | Old-style generics | `X \| None`, `list[X]`, `dict[K, V]` |
| P09 | `Any` type | Escape hatch from type safety | Restructure code to use concrete types |
| P10 | Circular imports | Architecture violation | Restructure layers, use `TYPE_CHECKING` |
| P11 | `PRIVATE_KEY = "..."` in source | Credential leak on repo exposure | Env var, encrypted file, or OS keyring |
| P12 | `verify=False` in httpx | Disables TLS verification (MITM) | Always `verify=True` |
| P13 | `random.random()` for security tokens | Predictable — not CSPRNG | `secrets.token_urlsafe()` |
| P14 | `eval()` / `exec()` on external input | Remote code execution | Pydantic validation + strict parsing |
| P15 | Retry order without idempotency key | Duplicate orders = financial loss | Always include `idempotency_key` |
| P16 | `onHand` for sell quantity validation | Ignores T+2.5 settlement | Use `sellableQty` from broker API |
| P17 | Logging credentials or tokens | Credential exposure via logs | Log redacted identifiers only |

### 8.2. TypeScript — Banned

| # | Pattern | Why It's Banned | Correct Alternative |
|:---|:---|:---|:---|
| T01 | `any` type | Disables TypeScript's entire value | `unknown` + type guard |
| T02 | `@ts-ignore` | Hides real errors | `@ts-expect-error` with explanation comment |
| T03 | `as Type` without validation | Unsafe cast, skips runtime check | Type guard function + narrow |
| T04 | `"use client"` on static pages | Ships unnecessary JS to browser | Default to Server Component |
| T05 | `React.Context` for high-freq data | Re-renders ALL consumers on every update | Zustand with selectors |
| T06 | `setInterval` for render loops | Runs when browser can't paint | `requestAnimationFrame` |
| T07 | `moment.js` | 300KB+ legacy library | `date-fns` or `Temporal` |
| T08 | SVG for real-time charts | DOM explosion at 500+ elements | HTML5 Canvas (TradingView LW) |
| T09 | `setRowData()` on AG Grid | Full grid re-render on every tick | `applyTransactionAsync` |
| T10 | `window.onresize` for chart sizing | Only fires on window resize | `ResizeObserver` on container |
| T11 | `interface IFoo { }` | C# naming convention, not TypeScript | `interface Foo { }` |

---

## 9. FILE & NAMING CONVENTIONS

### 9.1. Python

```
★ Files:         snake_case.py          (tick_repo.py, risk_check.py)
★ Classes:       PascalCase             (OrderRepository, SSIAuthClient)
★ Functions:     snake_case             (validate_order, calculate_var)
★ Constants:     UPPER_SNAKE_CASE       (MAX_POSITION_PCT, SSI_AUTH_URL)
★ Type aliases:  PascalCase (NewType)   (Symbol, Price, Quantity)
★ Private:       _leading_underscore    (_flush_buffer, _reconnect)
★ Modules:       singular nouns         (entity, not entities — except collections)
★ Test files:    test_<module>.py       (test_risk_check.py)
```

### 9.2. TypeScript

```
★ Files:         kebab-case.tsx/.ts     (price-board.tsx, market-store.ts)
★ Components:    PascalCase function    (export function PriceBoard() {})
★ Hooks:         camelCase, use prefix  (useMarketStream, useWebSocket)
★ Interfaces:    PascalCase, no "I"     (TickData, PriceBoardProps)
★ Types:         PascalCase             (OrderAction, ApiResponse)
★ Constants:     UPPER_SNAKE_CASE       (WS_URL, MAX_RETRIES)
★ Store files:   <domain>-store.ts      (market-store.ts, signal-store.ts)
★ Test files:    <name>.test.ts(x)      (market-store.test.ts)
★ Stories:       <name>.stories.tsx     (price-cell.stories.tsx)
```

### 9.3. Directory Layout Reference

```
algo-trading/                     # Monorepo root
├── packages/
│   ├── core/                     # Layer 0: Pure domain (ZERO external deps)
│   │   └── src/core/
│   │       ├── entities/         # Frozen dataclasses
│   │       ├── ports/            # Protocol interfaces
│   │       ├── use_cases/        # Pure business logic functions
│   │       └── value_objects.py  # NewType definitions
│   ├── adapters/                 # Layer 1: Infrastructure implementations
│   │   └── src/adapters/
│   │       ├── ssi/              # SSI broker adapter
│   │       ├── dnse/             # DNSE broker adapter
│   │       ├── duckdb/           # Database adapter
│   │       ├── vnstock/          # Data source adapter
│   │       └── openvino/         # NPU inference adapter
│   ├── agents/                   # Layer 2: LangGraph orchestration
│   │   └── src/agents/
│   │       ├── state.py          # Shared AgentState
│   │       ├── supervisor.py     # Graph definition
│   │       └── *_agent.py        # Individual agent nodes
│   └── interface/                # Layer 3: FastAPI, WebSocket, CLI
│       └── src/interface/
│           ├── app.py
│           ├── dependencies.py   # DI wiring
│           ├── ws/               # WebSocket endpoints
│           └── rest/             # REST endpoints
├── tests/
│   ├── unit/                     # Pure logic tests (no I/O)
│   ├── integration/              # Adapter tests (DuckDB in-memory)
│   └── conftest.py               # Shared fixtures
├── frontend/                     # Next.js (separate toolchain)
│   └── app/                      # App Router pages
├── data/                         # Runtime data (gitignored)
│   ├── models/                   # OpenVINO IR files
│   ├── parquet/                  # Partitioned tick data
│   ├── prompts/                  # Versioned LLM prompts
│   └── secrets/                  # Encrypted credentials
├── pyproject.toml                # uv workspace root
├── ruff.toml                     # Linter config
├── mypy.ini                      # Type checker config
└── .gitignore                    # Security-critical exclusions
```

---

## 10. CI PIPELINE — THE GATE

Nothing merges to `main` or `develop` without passing every stage.

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CI PIPELINE (sequential)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Stage 1: LINT + FORMAT CHECK                              ~5s     │
│  ├── uv run ruff check packages/ tests/                            │
│  ├── uv run ruff format --check packages/ tests/                   │
│  ├── pnpm eslint frontend/                                         │
│  └── pnpm prettier --check frontend/                               │
│                                                                     │
│  Stage 2: TYPE CHECK                                       ~8s     │
│  ├── uv run mypy packages/ --strict                                │
│  └── pnpm tsc --noEmit (frontend)                                  │
│                                                                     │
│  Stage 3: UNIT TESTS                                       ~5s     │
│  ├── uv run pytest tests/unit/ -x --tb=short                      │
│  └── pnpm vitest run (frontend)                                    │
│                                                                     │
│  Stage 4: INTEGRATION TESTS                                ~15s    │
│  └── uv run pytest tests/integration/ -x --tb=short               │
│                                                                     │
│  Stage 5: COVERAGE GATE                                    ~20s    │
│  ├── uv run pytest --cov=packages --cov-fail-under=85              │
│  └── pnpm vitest run --coverage --coverage.thresholds.lines=80     │
│                                                                     │
│  Stage 6: SECURITY SCAN                                    ~10s    │
│  ├── ruff check --select S (bandit rules)                          │
│  ├── Verify no credentials in diff (git secrets scan)              │
│  └── Verify no new `# type: ignore` without justification         │
│                                                                     │
│  TOTAL:                                                    ~63s    │
│  (Fast thanks to: uv install speed + DuckDB in-memory + no        │
│   external services required)                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 11. CURSOR AI CONTEXT RULES — HOW TO USE THIS DOCUMENT

### 11.1. For AI Assistants (Cursor, Copilot, etc.)

When generating code for this project, you MUST:

```
1. READ THIS FILE FIRST. It overrides your default patterns.
2. Use Python 3.12+ syntax (X | Y, match/case, from __future__ import annotations).
3. Type EVERY function parameter and return value. mypy --strict must pass.
4. Use Decimal for money. Never float.
5. Use @dataclass(frozen=True, slots=True) for domain objects.
6. Put business logic in pure functions in packages/core/src/core/use_cases/.
7. Put infrastructure in packages/adapters/src/adapters/.
8. Use Protocol (not ABC) for dependency inversion.
9. Offload blocking calls with asyncio.to_thread() or run_in_executor().
10. Include idempotency_key in any order-related code.
11. Check price bands (ceiling/floor) and T+2.5 sellable qty in order validation.
12. Handle network failures: timeout, retry with backoff, circuit breaker.
13. Use httpx (async), NEVER requests.
14. Use await asyncio.sleep(), NEVER time.sleep().
15. Write a test for every new function. Pure functions need NO mocks.
```

### 11.2. Context Loading Priority

When Cursor loads project context, prioritize files in this order:

```
1. 06_Development_Standards_Rules.md    ← THIS FILE (always load)
2. 02_Backend_Engineering.md            ← Architecture & code patterns
3. 01_System_Architecture_Overview.md   ← Tech stack decisions
4. 05_Integration_Security.md           ← Broker auth, OMS, T+2.5
5. 04_Multi_Agent_System.md             ← LangGraph, OpenVINO, prompts
6. 03_Frontend_Architecture.md          ← Next.js, AG Grid, Canvas
```

### 11.3. When You Are Unsure

```
If you don't know which layer code belongs to       → Re-read Section 3.
If you don't know how to handle a network call      → Re-read Doc 05, Section 4.
If you don't know the order validation rules         → Re-read Doc 05, Section 3.
If you don't know how to structure an Agent          → Re-read Doc 04, Section 1.
If you don't know the frontend performance rules     → Re-read Doc 03, Appendix A.
If you don't know the DuckDB query patterns          → Re-read Doc 02, Section 3.
```

---

## APPENDIX A: GLOSSARY — SHARED VOCABULARY

| Term | Meaning in This Project |
|:---|:---|
| **Agent** | A LangGraph node that performs one step in the trading pipeline |
| **Port** | A `Protocol` class in `core/ports/` — abstract interface |
| **Adapter** | A class in `adapters/` that implements a Port |
| **Use Case** | A pure function in `core/use_cases/` — business logic |
| **Entity** | A `@dataclass(frozen=True)` in `core/entities/` — domain object |
| **NAV** | Net Asset Value = sum(positions × market_price) + cash |
| **T+2.5** | Vietnam settlement cycle: buy today, sell afternoon of T+2 |
| **Ceiling/Floor** | Max/min price per day: HOSE ±7%, HNX ±10%, UPCOM ±15% |
| **Lot Size** | Minimum order quantity: 100 shares |
| **ASOF JOIN** | DuckDB time-series join: match nearest tick to each order |
| **Tick** | A single price/volume update for one symbol |
| **Kill Switch** | Emergency button that halts ALL automated trading instantly |
| **Idempotency Key** | Client-generated UUID ensuring an order is placed at most once |
| **NPU** | Neural Processing Unit — Intel Core Ultra's dedicated AI chip |
| **Edge** | Local machine processing (vs Cloud = remote server) |
| **Supervisor** | LangGraph graph that orchestrates all agents |

## APPENDIX B: DOCUMENT INDEX

| # | Document | Author Role | Contents |
|:---|:---|:---|:---|
| 01 | System Architecture Overview | System Architect | Tech stack, data flow, hardware mapping |
| 02 | Backend Engineering | Backend Engineer | Monorepo, Clean Architecture, DuckDB, async patterns |
| 03 | Frontend Architecture | Frontend Engineer | Next.js, AG Grid, Canvas charts, Zustand, testing |
| 04 | Multi-Agent System | AI Engineer | LangGraph, OpenVINO INT4, prompt versioning, RAG |
| 05 | Integration & Security | Security Engineer | RSA auth, OMS, T+2.5, price bands, retry/backoff |
| **06** | **Development Standards** | **Tech Lead** | **THIS FILE — the law that governs all code** |

---

*This document is maintained by the Tech Lead and is the final authority on all coding standards, conventions, and quality gates in this project. When in doubt, this document wins.*
