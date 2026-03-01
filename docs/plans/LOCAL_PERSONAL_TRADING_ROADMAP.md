# Local Personal Trading Product Roadmap

## CVF Traceability
- CVF-Doc-ID: CVF-TT-LOCAL-20260302-R1
- Owner: Product + Engineering
- Last-Updated: 2026-03-02
- Status: Draft Approved for Execution
- Scope: Turn Trading-Tools from demo/mixed-mock to local personal trading product.

## Product Direction
- User downloads and runs app locally on personal machine.
- User manages own API keys (`VNStock`, `SSI`, `AI/Agent`) locally.
- Portfolio is personal and persistent per user.
- Screener pipeline runs real agents/AI (not mock SSE).
- Default trading mode is `dry-run`; `live` requires explicit confirmation and safeguards.

## Current Gaps (As-Is)
- Portfolio API/UI is still stub/placeholder in multiple paths.
- Order flow is mostly local UI state, not full backend OMS broker execution flow.
- Screener `/run-screener` currently streams simulated pipeline events/results.
- Local installer/setup flow for non-technical users is not complete.

## Target State (To-Be)
- One-command local bootstrap and setup wizard.
- Secure local key storage with profile-based config.
- Real broker sync for portfolio/order status.
- Real agent pipeline execution with explainable outputs.
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
