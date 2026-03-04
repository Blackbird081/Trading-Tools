# Local Personal Trading Product Roadmap

## CVF Traceability
- CVF-Doc-ID: CVF-TT-LOCAL-20260302-R1
- Owner: Product + Engineering
- Last-Updated: 2026-03-04
- Status: In execution
- Scope: Turn Trading-Tools from demo/mixed-mock to local personal trading product.

## Execution Mapping Snapshot (Updated, 2026-03-04)

Status scale:
- `DONE`: exit criteria completed and evidenced.
- `PARTIAL`: some technical assets exist, but exit criteria are not met.
- `NOT STARTED`: no meaningful implementation yet.

| Roadmap Item | Status | Evidence (current repository) | Gap to close |
|---|---|---|---|
| Phase 0 - Baseline Freeze and Contract Lock | `DONE (artifacts)` | Local baseline tag `baseline-local-roadmap-r1` created; contract doc added (`docs/plans/LOCAL_API_CONTRACTS.md`); smoke checklist added (`docs/plans/LOCAL_SMOKE_CHECKLIST.md`); baseline UI snapshot log added (`docs/plans/LOCAL_UI_BASELINE_SNAPSHOTS.md`). | Push tag to remote and enforce smoke checklist in release workflow. |
| Phase 1 - Local Runtime and Setup Wizard | `DONE` | Added external probe API/UI (`POST /api/setup/probe-external`, `frontend/app/settings/_components/setup-wizard.tsx`), setup API tests (`tests/integration/test_setup_api.py`), and onboarding benchmark tooling (`scripts/benchmark-onboarding.ps1`, `docs/plans/LOCAL_ONBOARDING_BENCHMARK.md`). | Keep benchmark artifact updated for each release candidate. |
| Phase 2 - Secure Key and Profile Management | `DONE` | Added encrypted profile vault (`packages/interface/src/interface/profile_vault.py`) + setup profile APIs (create/list/activate/export/import/rotate/revoke) + settings UI section. | Monitor passphrase/key recovery policy and UX hardening. |
| Phase 3 - OMS and Broker Execution (Dry-Run First) | `DONE` | Added backend OMS REST (`packages/interface/src/interface/rest/orders.py`), idempotency async wiring (`trading_store.py`, `DuckDBIdempotencyStore.create()`), frontend order API integration (`frontend/stores/order-store.ts`, `frontend/app/orders/_components/*`). | Wire real broker adapter for live execution (currently guarded/stubbed). |
| Phase 4 - Real Portfolio Sync | `DONE` | Implemented `/api/portfolio`, `/positions`, `/pnl`, `/refresh`, `/reconcile` and connected Portfolio UI/store (`frontend/stores/portfolio-store.ts`, `frontend/app/portfolio/*`). | Add broker-source reconciliation against real account endpoint when live broker is enabled. |
| Phase 5 - Real Agent/AI Pipeline Integration | `DONE` | Screener stream now runs with optional Fundamental agent stage and enriched outputs (`fundamental_summary`, `news_headlines`, `data_sources`) backed by local/external ports (`packages/interface/src/interface/rest/data_loader.py`, `packages/adapters/src/adapters/vnstock/news.py`) with metadata persisted in screener history. | Monitor external source reliability in live mode (`SCREENER_USE_EXTERNAL`). |
| Phase 6 - Guardrails and Trading Safety | `DONE` | Added dedicated safety integration suite (`tests/integration/test_order_safety_controls.py`) covering kill-switch, cooldown, max-notional, daily-loss, and DLQ fallback; added emergency drill automation + runbook (`scripts/emergency-fallback-drill.ps1`, `docs/plans/LOCAL_EMERGENCY_DRILL_RUNBOOK.md`). | Extend drill to include real broker adapter once enabled. |
| Phase 7 - Quality, Packaging, and Release | `DONE` | Added automated release validation bundle (`scripts/release-validation.ps1`) and expanded release/upgrade/rollback checklist coverage (`docs/plans/LOCAL_RELEASE_CHECKLIST.md`, `docs/plans/LOCAL_UPGRADE_ROLLBACK_GUIDE.md`) with report artifacts. | Execute clean-machine validation on each release candidate and archive reports. |
| Fix-01 DLQ failed orders | `DONE` | Added DLQ schema + retry worker + admin/replay APIs (`failed_orders_dlq`, `DLQRetryWorker`, `/api/orders/dlq`, `/api/orders/dlq/replay`). | Optional notifier integration (Telegram/email) for permanent failures. |
| Fix-02 Optional `pandas_ta` | `DONE` | Added optional extra `technical` with `pandas` + `pandas_ta` in `packages/agents/pyproject.toml`; fallback test added in `tests/unit/test_technical_agent.py` to verify graceful behavior when `pandas_ta` is unavailable. | Monitor package pin compatibility in CI matrix. |
| Fix-03 OpenTelemetry for DuckDB calls | `DONE` | Added `execute_with_trace()` wrapper (`packages/adapters/src/adapters/duckdb/telemetry.py`) and applied to core DuckDB paths in `interface/trading_store.py`. | Add optional exporter configuration docs for external trace backends. |
| Fix-04 Async factory for DuckDBIdempotencyStore | `DONE` | Added `DuckDBIdempotencyStore.create()` async factory and migrated runtime wiring to async path (`interface/trading_store.py`). | Monitor deprecation path for legacy sync-only initialization. |
| Fix-05 Refine `bank_account` guardrail pattern | `DONE` | Replaced broad numeric regex with VN-context strategy (`packages/agents/src/agents/guardrails.py`) and added unit tests (`tests/unit/test_guardrails.py`). | Monitor false-positive/false-negative drift with real production text samples. |
| Hardening-A1 Runtime Security Middleware Wiring | `DONE (gated)` | Added `AuthMiddleware` + runtime wiring of `RateLimitMiddleware` in `interface.app`; added integration coverage in `tests/integration/test_runtime_security_middleware.py` for unauthorized/reject + rate-limit behavior. | Monitor token distribution policy for non-dev protected environments. |
| Hardening-A2 Real Data Provider Policy | `DONE (gated)` | Added explicit provider contract (`DATA_PROVIDER_MODE=mock/live`) with production guard (`mock` blocked) in `interface.rest.data_loader`; added integration/unit tests (`tests/integration/test_data_loader_api.py`, `tests/unit/test_data_loader_helpers.py`). | Keep live provider dependency (`vnstock`) and source reliability monitored in production. |
| Hardening-A3 Monetary Precision (`Decimal`) | `DONE (gated)` | Migrated OMS request/risk checks to `Decimal` in `interface.rest.orders` (price/notional/daily-loss/buying-power path); added boundary precision regression test in `tests/integration/test_order_safety_controls.py`. | Continue Decimal migration in downstream analytics/store paths for full end-to-end precision parity. |
| Hardening-A4 Frontend Coverage Expansion | `NOT STARTED (locked)` | Current frontend global statement coverage is low for release confidence. | Raise frontend global coverage to >= 80% with risk-based test expansion (orders, dashboard, screener, market board). |
| Hardening-A5 Safe Gate Targeting | `DONE (gated)` | `scripts/phase-gates.ps1` default API base changed to local (`http://localhost:8000/api`) and production targets now require explicit `-AllowProductionTarget` override with fail-fast guard. | Add CI usage examples for guarded production smoke execution. |
| AI-06 Single-Provider Multi-Role Subagent Orchestration | `DONE (gated)` | `FundamentalAgent` now runs contextual subroles (`thesis`, `valuation`, `news_catalyst`, `risk_challenge`) via a single AI engine/API key and applies deterministic arbitration (`risk_veto_then_consensus`); pipeline emits role metadata (`ai_role_outputs`, `ai_subroles`, `ai_final_action`). | Add strict JSON schema per role and provider-level benchmark calibration (OpenAI/Claude/Gemini parity). |

## Product Direction
- User downloads and runs app locally on personal machine.
- User manages own API keys (`VNStock`, `SSI`, `AI/Agent`) locally.
- Portfolio is personal and persistent per user.
- Screener pipeline runs real agents/AI (not mock SSE).
- Default trading mode is `dry-run`; `live` requires explicit confirmation and safeguards.

## Master Plan Alignment
- `IMPLEMENTATION_PLAN.md` core phases (`P0/P1`, `Phase 1-5`) are tracked as gate-complete baseline.
- This local roadmap tracks productization scope on top of that baseline.
- Completion of master gated phases does not close local personal trading phases automatically.

## Current Gaps (As-Is)
- Real broker execution path still uses guarded placeholder; live adapter integration remains.
- External data quality in live mode depends on broker/data provider availability and credentials.
- Frontend global coverage remains below release-grade target.
- Native provider adapters for Anthropic/Gemini are not yet implemented (current remote LLM path is OpenAI-compatible).
- Role outputs are currently narrative text; schema-locked role JSON contract is not yet enforced.

## Target State (To-Be)
- One-command local bootstrap and setup wizard.
- Secure local key storage with profile-based config.
- Real broker sync for portfolio/order status.
- Real agent pipeline execution with explainable outputs.
- Single active AI provider per run with contextual subroles and deterministic conflict arbitration.
- Stable release process aligned with CVF controlled changes.

## Phase Plan

### Phase 0 - Baseline Freeze and Contract Lock
Goal: freeze current baseline before major refactor.
- Tag current state (`baseline-local-roadmap-r1`).
- Capture API contracts and current UI behavior snapshots.
- Freeze breaking UI route changes until core flows are wired.

Exit criteria:
- Git tag created.
- API contract document for `portfolio`, `orders`, `screener`.
- Smoke test checklist recorded.

### Phase 1 - Local Runtime and Setup Wizard
Goal: make local deployment predictable for individual traders.
- Provide local run profiles:
  - `dev` (hot reload),
  - `local-prod` (production-like on local machine),
  - optional Docker profile.
- Add setup wizard page for:
  - key input,
  - connection checks (`VNStock`, `SSI`, `AI`),
  - mode toggle (`dry-run`/`live`).
- Add local data path convention and first-run initialization.

Exit criteria:
- New user can run app locally in <= 15 minutes.
- Setup wizard validates keys and reports health.

### Phase 2 - Secure Key and Profile Management
Goal: user controls secrets locally and safely.
- Implement profile model:
  - multiple profiles on one machine,
  - active profile switching.
- Encrypt keys at rest (machine-local key / passphrase).
- Keep `.env` support for advanced users, but prefer profile vault.
- Add key rotation and revoke workflow.

Exit criteria:
- No plaintext key persistence in app state/storage.
- Profile export/import policy documented.

### Phase 3 - OMS and Broker Execution (Dry-Run First)
Goal: end-to-end order lifecycle from UI to broker adapter.
- Implement backend order endpoints:
  - place/cancel/status/open orders.
- Connect frontend order form/history to backend APIs.
- Start with `dry-run` as default and add explicit live guard:
  - two-step confirm,
  - risk pre-check summary,
  - idempotency key audit.
- Add persistent order history in DuckDB.

Exit criteria:
- UI order actions are backed by real API calls.
- `dry-run` flow fully operational with audit logs.

### Phase 4 - Real Portfolio Sync
Goal: portfolio reflects user's real account state (or dry-run state).
- Implement `/api/portfolio`, `/api/portfolio/positions`, `/api/portfolio/pnl`.
- Add periodic sync + manual refresh.
- Add reconciliation between broker state and local snapshot.
- Show sync status and last update timestamp in UI.

Exit criteria:
- Portfolio page displays non-placeholder, account-specific data.
- Reconciliation mismatch alert available.

### Phase 5 - Real Agent/AI Pipeline Integration
Goal: replace simulated screener pipeline with real multi-agent execution.
- Wire `/run-screener` to actual runner/supervisor flow.
- Ingest real market + fundamentals + news inputs.
- Return:
  - score,
  - confidence,
  - rationale/explanation,
  - risk and position-sizing suggestion.
- Persist run history and model metadata per run.

Exit criteria:
- No mock result path in production mode.
- Pipeline output includes reproducibility metadata.

### Phase 6 - Guardrails and Trading Safety
Goal: reduce user risk when moving to live trading.
- Enforce live-mode controls:
  - max order notional,
  - max daily loss,
  - kill switch,
  - market session checks,
  - cooldown after repeated rejects.
- Add execution alerts (success/fail/reject).
- Add emergency fallback to dry-run mode.

Exit criteria:
- Live mode blocked unless guardrails are healthy.
- Safety controls test suite passes.

### Phase 7 - Quality, Packaging, and Release
Goal: make release stable for personal distribution.
- Add integration/E2E test packs:
  - portfolio sync,
  - order lifecycle,
  - screener pipeline real run.
- Publish release packaging:
  - local install guide,
  - upgrade guide,
  - rollback guide.
- Define minimum quality gates for release branch.

Exit criteria:
- Release checklist passes.
- Upgrade/rollback validated on clean machine.

## Parallel Fix Pack (Execute Alongside Main Roadmap)

### Hardening-A1 — Runtime Security Middleware Wiring
- Priority: Critical
- Owner: Backend Platform + Security
- Dependency: none
- Scope:
  - Attach `RateLimitMiddleware` in application bootstrap.
  - Add authentication middleware wiring policy for sensitive REST endpoints (`orders`, `safety`, `setup`).
  - Add integration tests for unauthorized/rate-limited behavior.
- Definition of Done:
  - Middleware stack is active in runtime (verified through tests and startup logs).
  - Sensitive endpoints reject unauthorized calls in protected mode.

### Hardening-A2 — Real Data Provider Policy (No Mock in Production)
- Priority: Critical
- Owner: Data Pipeline
- Dependency: Hardening-A1 in place for endpoint abuse control
- Scope:
  - Refactor loader into explicit provider modes (`mock`, `live`).
  - Add `DATA_PROVIDER_MODE` / equivalent guard with `production => live only`.
  - Add tests to assert production mode cannot execute mock branch.
- Definition of Done:
  - Production mode rejects/mock-disables synthetic data generation path.
  - Load/Update acceptance uses real provider contract in non-mock mode.

### Hardening-A3 — Monetary Precision Migration (`Decimal`)
- Priority: Critical
- Owner: OMS + Risk
- Dependency: none
- Scope:
  - Replace `float` price handling in order request/validation with `Decimal`.
  - Normalize notional, max-notional, buying-power, and daily-loss checks to `Decimal`.
  - Add regression tests for edge decimals and rounding-sensitive values.
- Definition of Done:
  - No float-based monetary calculation remains in order-risk path.
  - Precision tests cover boundary values and pass in CI.

### Hardening-A4 — Frontend Coverage Expansion Pack
- Priority: High
- Owner: Frontend + QA
- Dependency: none
- Scope:
  - Expand tests for high-risk UI flows (order form/history, dashboard load/update state model, screener pipeline table, market board controls).
  - Add release gate threshold for frontend global statement coverage >= 80%.
  - Publish coverage trend artifact per release candidate.
- Definition of Done:
  - Frontend coverage gate passes at >= 80% statements globally.
  - Critical UI flows are covered with deterministic integration tests.

### Hardening-A5 — Safe Gate Targeting and Environment Guard
- Priority: High
- Owner: DevEx + SRE
- Dependency: none
- Scope:
  - Remove/override production default API base in local gate script.
  - Require explicit confirmation flag for production smoke runs.
  - Add environment banner + fail-fast checks for unsafe target combinations.
- Definition of Done:
  - Local `phase-gates` cannot accidentally hit production without explicit override.
  - Production smoke is still possible but controlled and auditable.

### AI-06 — Single-Provider Multi-Role Subagent Orchestration
- Priority: High
- Owner: Agents + Product AI
- Dependency: Hardening-A1/A2/A3 completed
- Scope:
  - Keep one active AI provider/engine per run (single API key context).
  - Execute contextual subroles inside one orchestrated agent (`thesis`, `valuation`, `news_catalyst`, `risk_challenge`).
  - Apply deterministic arbitration policy (`risk_veto_then_consensus`) before final AI summary is emitted.
  - Persist role metadata (`active_roles`, role outputs, arbitration action) for traceability.
- Definition of Done:
  - Single-provider run path is verifiable in metadata.
  - Role outputs are captured per symbol and linked to final action.
  - Risk veto deterministically overrides optimistic narrative when risk level is `high`/`critical`.

### Fix-01 — Dead Letter Queue for Failed Orders
- Priority: Critical
- Owner: Backend (OMS) + SRE
- Dependency: Phase 3 OMS order endpoints available
- Scope:
  - Design DLQ schema in DuckDB (`failed_orders_dlq`).
  - Add background retry worker with bounded retry/backoff.
  - Add Telegram notification for permanent failure.
  - Add admin/API query for DLQ visibility and replay.
- Definition of Done:
  - Failed broker calls are persisted to DLQ with full context.
  - Retry worker can reprocess and mark resolution state.
  - No silent order loss in live mode.

### Fix-02 — `pandas_ta` as Optional Dependency
- Priority: Medium (quick win)
- Owner: Backend (Agents)
- Dependency: none
- Scope:
  - Add `pandas_ta` as optional extra dependency in `packages/agents/pyproject.toml`.
  - Keep graceful fallback path when package is absent.
  - Update docs for optional install profile.
- Definition of Done:
  - CI passes with and without optional extra.
  - Technical agent behavior degrades gracefully if extra is missing.

### Fix-03 — OpenTelemetry Tracing for DuckDB Calls
- Priority: High (observability)
- Owner: Backend Platform
- Dependency: Phase 7 quality gates
- Scope:
  - Add instrumentation wrapper around DuckDB query execution paths.
  - Capture span metadata: query type, duration, rows, error state.
  - Expose traces to configured exporter/collector.
- Definition of Done:
  - Core DB operations emit trace spans with consistent attributes.
  - Slow/failing DB paths are observable in trace backend.

### Fix-04 — Async Factory for `DuckDBIdempotencyStore`
- Priority: Medium
- Owner: Backend (OMS)
- Dependency: after Fix-01 design freeze
- Scope:
  - Introduce async factory/init path for `DuckDBIdempotencyStore`.
  - Use non-breaking migration: keep existing constructor temporarily.
  - Migrate callers incrementally and deprecate old path.
- Definition of Done:
  - No breaking runtime change for existing callers.
  - New async init path is used in primary runtime wiring.

### Fix-05 — Refine Guardrails `bank_account` Pattern
- Priority: High (security/false-positive control)
- Owner: AI Safety + Backend
- Dependency: none
- Scope:
  - Replace broad `10-19 digits` regex with VN-specific bank-account detection strategy.
  - Add allowlist/denylist tuning to reduce false positives.
  - Add unit tests for representative VN samples.
- Definition of Done:
  - Measurable drop in false positives on benign numeric text.
  - Sensitive account-like patterns still redacted correctly.

### Suggested Parallel Execution Order
1. Fix-02 (`pandas_ta`) and Fix-05 (guardrails pattern) in parallel.
2. Deliver Phase 3 OMS API first, then execute Fix-01 (DLQ).
3. Run Fix-03 (OpenTelemetry) after core order/portfolio flows are stable.
4. Execute Fix-04 with non-breaking migration once idempotency flow is stable.
5. Execute Hardening-A1/A3 immediately before enabling real API keys.
6. Execute Hardening-A2 and Hardening-A5 before any production-like smoke from developer machines.
7. Execute AI-06 single-provider subagent orchestration to eliminate cross-provider AI conflicts.
8. Execute Hardening-A4 as release gate uplift before public/beta user expansion.

## Workstreams
- WS1: Runtime + Installer + Config
- WS2: Broker/OMS + Portfolio
- WS3: Agent Pipeline + AI Inference
- WS4: UI/UX + Safety Controls
- WS5: QA + Release Engineering

## Milestone Acceptance
1. Local-only user can setup and run without cloud dependency.
2. Keys are user-owned and securely stored.
3. Portfolio and Orders are account-specific, not placeholder.
4. Screener uses real agents/AI output in production mode.
5. Dry-run/live controls are explicit, auditable, and safe.

## Risks and Mitigations
- Risk: broker API instability.
  - Mitigation: retries, circuit breaker, cached fallback state.
- Risk: user misconfiguration of keys.
  - Mitigation: setup wizard validation + diagnostics page.
- Risk: live order mistakes.
  - Mitigation: default dry-run, two-step confirm, hard risk limits.
- Risk: model/runtime mismatch on local machines.
  - Mitigation: capability detection + graceful CPU fallback.

## Dependency Notes with CVF
- Keep CVF as control framework for process/version discipline.
- Trading-Tools release cadence should map to CVF change-control gates:
  - proposal,
  - phase implementation,
  - verification,
  - release note.
