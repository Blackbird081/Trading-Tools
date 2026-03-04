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
| Hardening-A4 Frontend Coverage Expansion | `PARTIAL (in progress)` | Expanded integration packs for dashboard/order/screener/market-board (`frontend/__tests__/integration/{data-loader,order-form,pipeline-runner,market-board-mobile}.test.tsx`), fixed stale preset/year race in loader stream (`frontend/app/(dashboard)/_components/data-loader.tsx`), and widened gate scope in `scripts/pre-live-api-gate.ps1`; latest release-validation frontend critical snapshot: lines/statements `82.45%` (expanded scope). | Lift expanded critical-flow snapshot from `82.45%` to sustained `>=90%` while keeping release minimum `>=80%` green. |
| REL-01 Release Quality Gate Uplift (financial-safe) | `DONE (gated)` | `scripts/pre-live-api-gate.ps1` now supports configurable backend threshold and risk-based frontend coverage scope; `scripts/release-validation.ps1` enforces backend + frontend critical gates; latest run passed with backend critical `97.51%` and expanded frontend critical lines/statements `82.45%`. | Keep release-minimum gate `>=80%` green while driving expanded critical-flow suite to `>=90%` target. |
| UX-01 Setup Save/Apply Clarity | `DONE (gated)` | `frontend/app/settings/_components/setup-wizard.tsx` now uses explicit `Save Draft`, `Apply Draft`, `Revert` actions with `Saved/Unsaved` status + last-saved timestamp; added integration test `frontend/__tests__/integration/setup-wizard.test.tsx`. | Extend UX consistency to profile import/export rotate flows with same dirty-state semantics. |
| DATA-01 DuckDB Migration + Backup/Restore + Integrity Gate | `DONE (gated)` | Added cache schema marker + migration metadata + startup integrity probe (`interface.rest.data_loader`, `interface.app`, `interface.rest.setup`) and backup/restore scripts (`scripts/data-cache-backup.ps1`, `scripts/data-cache-restore.ps1`). | Maintain migration marker policy for future schema upgrades. |
| SEC-01 Secret Redaction Hardening | `DONE (gated)` | Added shared redaction utilities (`interface.redaction`) and applied redaction in setup/data-loader runtime errors, profile decrypt response, and diagnostics paths with tests (`tests/unit/test_redaction.py`, setup/data-loader test updates). | Extend redaction policy to any new external adapter error path. |
| Hardening-A5 Safe Gate Targeting | `DONE (gated)` | `scripts/phase-gates.ps1` default API base changed to local (`http://localhost:8000/api`) and production targets now require explicit `-AllowProductionTarget` override with fail-fast guard. | Add CI usage examples for guarded production smoke execution. |
| AI-06 Single-Provider Multi-Role Subagent Orchestration | `DONE (gated)` | `FundamentalAgent` now runs contextual subroles (`thesis`, `valuation`, `news_catalyst`, `risk_challenge`) via a single AI engine/API key and applies deterministic arbitration (`risk_veto_then_consensus`); pipeline emits role metadata (`ai_role_outputs`, `ai_subroles`, `ai_final_action`). | Add strict JSON schema per role and provider-level benchmark calibration (OpenAI/Claude/Gemini parity). |
| AI-07 Quant Benchmark Pack (`Precision@K`, `Hit-rate`, `MDD`) | `DONE (baseline)` | Added fixed-dataset benchmark artifacts (`tests/evals/data/recommendation_outcomes_fixed.csv`, `tests/evals/reliability_metrics.py`, `tests/evals/benchmark_fixed_dataset.py`) and unit coverage (`tests/unit/test_reliability_eval_pack.py`). | Promote fixed dataset to versioned rolling snapshots from production-like history. |
| AI-08 Provider A/B + Consensus Check | `DONE (baseline)` | Added provider A/B dataset and evaluator (`tests/evals/data/provider_ab_consensus_fixed.csv`, `tests/evals/provider_ab_consensus.py`) with agreement/per-provider/consensus metrics and tests. | Extend from offline benchmark to runtime dual-provider experiment mode with strict cost controls. |
| AI-09 Weekly Drift Monitoring (Recommendation vs Outcome) | `DONE (baseline)` | Added weekly drift evaluator (`tests/evals/weekly_drift_monitor.py`) and unified runner (`tests/evals/run_reliability_pack.py`) producing per-week summary + alerts. | Add scheduled weekly CI/job execution and threshold-based release gate integration. |
| AI-10 Native Multi-Provider Runtime (OpenAI + Anthropic + Gemini + Alibaba) | `DONE (baseline)` | Added native provider wiring in runtime/setup/settings (`interface.rest.data_loader`, `interface.rest.setup`, `frontend/app/settings/_components/setup-wizard.tsx`) with provider-specific API key/model fields/validation and task-router model mapping (`coder/reasoning/writing`) across providers. | Add profile-level provider failover policy and runtime cost controls. |
| AI-11 Task/Role Model Recommendation Matrix | `DONE (baseline)` | Added setup recommendation API (`GET /api/setup/model-recommendations`) and Settings matrix UI for per-task/per-role provider-model guidance. | Keep matrix calibrated with rolling provider eval results. |
| AI-12 Provider Failover + Cost Control Policy | `DONE (baseline)` | Added configurable policy (`AGENT_AI_FALLBACK_ORDER`, `AGENT_AI_TIMEOUT_SECONDS`, `AGENT_AI_BUDGET_USD_PER_RUN`, `AGENT_AI_MAX_REMOTE_CALLS`) with runtime failover/budget enforcement in screener AI engine. | Add per-profile UI presets and tighter cost telemetry thresholds. |
| OBS-01 Correlation-ID + Pipeline Observability | `DONE (baseline)` | Added correlation-id middleware/headers, SSE+REST payload propagation, and observability event API (`/api/observability/events`) wired from load/update/screener/order failure paths. | Expand event coverage to broker adapter and websocket pipeline internals. |
| OPS-01 Local Runbook and Incident Playbook Closure | `DONE (baseline)` | Added consolidated operator runbook (`docs/plans/LOCAL_OPERATOR_RUNBOOK.md`) and bound it to release checklist + reliability artifact gate. | Keep incident templates and escalation contacts synchronized per release. |

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
- Frontend critical-flow gate baseline is now `>=80%`; target uplift to `>=90%` is still open.
- Database operational safeguards (schema migration marker, backup/restore/integrity gate) are not yet formalized.
- Secret redaction hardening in runtime diagnostics/log paths still needs explicit test-backed enforcement.
- Provider parity calibration across OpenAI/Anthropic/Gemini/Alibaba is not automated yet.
- Role outputs are currently narrative text; schema-locked role JSON contract is not yet enforced.
- AI reliability pack automation exists; next step is enforce threshold-based release rejection on alert severity.
- Correlation-id observability exists for REST/SSE/order failures; websocket/broker deep-path coverage remains open.
- Consolidated local operator runbook is in place; continue runbook drills on each release candidate.

## Target State (To-Be)
- One-command local bootstrap and setup wizard.
- Secure local key storage with profile-based config.
- Real broker sync for portfolio/order status.
- Real agent pipeline execution with explainable outputs.
- Single active AI provider per run with contextual subroles and deterministic conflict arbitration.
- Native user-selectable providers in Settings/profile vault (`OpenAI`, `Anthropic`, `Gemini`, `Alibaba`) on local runtime.
- Measurable reliability governance via benchmark metrics, A/B consensus validation, and weekly drift alerts.
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

## Immediate Expert Completion Pack (Locked, 2026-03-04)
1. `E1` - `REL-01` + `UX-01`
2. `E2` - `DATA-01` + `SEC-01`
3. `E3` - `AI-11` + `AI-12` + automated `AI-09` weekly runner integration
4. `E4` - `OBS-01` + `OPS-01`

Execution update (2026-03-04):
- `E1` completed with gate evidence (`release-validation` PASS, explicit settings Save/Apply UX shipped).
- `E2` completed (cache schema marker/integrity + backup/restore + secret redaction hardening with tests).
- `E3` completed baseline (model recommendation matrix + provider failover/cost policy + weekly reliability runner automation).
- `E4` completed baseline (correlation-id propagation + observability events API + consolidated operator runbook).
- `Hardening-A4` is now in progress across dashboard/order/screener/market-board; expanded critical snapshot currently at `82.45%` lines/statements.
- Next focus: continue raising expanded Hardening-A4 suite from `82.45%` to sustained `>=90%` critical-flow confidence.

Exit policy:
- Do not move to broader real API-key onboarding until `E1` and `E2` are complete.
- Do not promote to wider local distribution until `E3` and `E4` are complete.

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
