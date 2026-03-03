# CVF Change Trace Log

## Purpose
Canonical ledger for change traceability under CVF governance.  
All code/config/docs/test changes must be logged here with validation evidence and plan mapping.

## Entry Template

```
CVF-Trace-ID:
Date-Time (UTC+7):
Type:
Scope:
Impact:
Root Cause:
Files Changed:
Validation Evidence:
Deployment Target:
Deployment Status:
Commit SHA:
Plan Mapping:
Owner:
Notes:
```

---

## Entries

### CVF-TT-20260302-001
- Date-Time (UTC+7): 2026-03-02
- Type: docs
- Scope: Add mandatory CVF traceability governance into master implementation plan.
- Impact: Standardize post-change auditability beyond Git commit history.
- Root Cause: Change/fix/test history was previously scattered and hard to trace consistently.
- Files Changed: `docs/plans/IMPLEMENTATION_PLAN.md`, `docs/reports/CVF_CHANGE_TRACE_LOG.md`
- Validation Evidence: Manual review of policy section and schema completeness.
- Deployment Target: repository documentation
- Deployment Status: completed (local update)
- Commit SHA: N/A (pending next commit)
- Plan Mapping: Implementation governance baseline (global, cross-phase)
- Owner: Codex + project owner
- Notes: Effective immediately for all subsequent fixes/bugs/tests.

### CVF-TT-20260302-002
- Date-Time (UTC+7): 2026-03-02
- Type: bugfix
- Scope: Desktop dashboard redesign to remove Agent Signals empty panel and replace with session overview statistics panel.
- Impact: Dashboard desktop now always shows two useful areas (price board + session overview) without empty right-side space.
- Root Cause: Agent Signals placeholder had no consistent runtime data and created a visually empty sidebar.
- Files Changed: `frontend/app/(dashboard)/page.tsx`, `frontend/app/(dashboard)/_components/session-overview-panel.tsx`
- Validation Evidence: `pnpm -C frontend exec tsc --noEmit` pass; `pnpm -C frontend exec vitest run __tests__/integration/ws-provider.test.ts` pass (3/3).
- Deployment Target: frontend (web / Railway)
- Deployment Status: pending push/deploy
- Commit SHA: N/A (pending next commit)
- Plan Mapping: Phase 4 (Frontend & Real-time UI) — dashboard composition refinement
- Owner: Codex + project owner
- Notes: Mini chart intentionally excluded per product direction; Screener tab remains the location for agent-driven insights.

### CVF-TT-20260302-003
- Date-Time (UTC+7): 2026-03-02
- Type: hotfix
- Scope: Prioritize P0/P1 roadmap and implement manual `Load` vs incremental `Update` data flow with no auto-load.
- Impact: Prevents automatic long-running load on app open; improves clarity of loader states and separates full load from update policy.
- Root Cause: Auto-load caused slow startup, repeated refresh confusion, and ambiguous status text (`Connecting...`).
- Files Changed: `frontend/app/(dashboard)/_components/data-loader.tsx`, `packages/interface/src/interface/rest/data_loader.py`, `packages/interface/src/interface/app.py`, `docs/plans/IMPLEMENTATION_PLAN.md`
- Validation Evidence: `python -m py_compile packages/interface/src/interface/rest/data_loader.py packages/interface/src/interface/app.py` pass; `pnpm -C frontend exec vitest run __tests__/stores/market-store.test.ts __tests__/stores/signal-store.test.ts` pass (9/9); `pnpm -C frontend exec tsc --noEmit` pass.
- Deployment Target: frontend + backend (Railway)
- Deployment Status: pending push/deploy
- Commit SHA: N/A (pending next commit)
- Plan Mapping: Section 0.6 P0/P1 priority execution roadmap
- Owner: Codex + project owner
- Notes: Railway persistent volume on `/app/data` is still required operationally for redeploy persistence acceptance.

### CVF-TT-20260302-004
- Date-Time (UTC+7): 2026-03-02
- Type: ops
- Scope: Enforce Railway deploy requirement for persistent mount path `/app/data`.
- Impact: Prevents deployments from proceeding without configured persistent mount path.
- Root Cause: Redeploys without mounted volume cause DuckDB cache loss.
- Files Changed: `railway.json`
- Validation Evidence: Railway CLI installed (`railway 4.30.5`); attempted `railway volume add -m /app/data --json` returned unauthorized (no CLI auth token/session in this environment).
- Deployment Target: Railway service config
- Deployment Status: partial (config-as-code enforced; runtime volume attach pending auth)
- Commit SHA: N/A (pending next commit)
- Plan Mapping: Section 0.6 P1 — Data Persistence & Update Policy
- Owner: Codex + project owner
- Notes: Runtime attach can be executed immediately after setting `RAILWAY_TOKEN` or running interactive `railway login` on this machine.

### CVF-TT-20260302-005
- Date-Time (UTC+7): 2026-03-02
- Type: hotfix
- Scope: Fix "Loading stuck at 0/100" by hardening DuckDB path fallback and stream interruption handling.
- Impact: Data loader no longer hangs silently when backend stream stops unexpectedly; Railway volume path works with fallback when `/app/data/db` cannot be created.
- Root Cause: Backend stream terminated at first symbol due DB path/mount write-path mismatch; frontend remained in loading state because no terminal SSE event was received.
- Files Changed: `packages/interface/src/interface/rest/data_loader.py`, `packages/interface/src/interface/app.py`, `frontend/app/(dashboard)/_components/data-loader.tsx`, `Dockerfile`, `README.md`
- Validation Evidence: `python -m py_compile packages/interface/src/interface/rest/data_loader.py packages/interface/src/interface/app.py` pass; `pnpm -C frontend exec tsc --noEmit` pass; `pnpm -C frontend exec vitest run __tests__/integration/ws-provider.test.ts __tests__/stores/market-store.test.ts __tests__/stores/signal-store.test.ts` pass (12/12).
- Deployment Target: frontend + backend (Railway)
- Deployment Status: pending push/deploy
- Commit SHA: N/A (pending next commit)
- Plan Mapping: Section 0.6 P0/P1 priority roadmap
- Owner: Codex + project owner
- Notes: Recommended Railway variable `DUCKDB_PATH=/app/data/trading.duckdb` for volume-root write compatibility.

### CVF-TT-20260302-006
- Date-Time (UTC+7): 2026-03-02 13:40
- Type: ops
- Scope: Add production Railway incident evidence for DuckDB permission failure into implementation governance.
- Impact: Established auditable root-cause record for loader interruption and production `ERROR` state.
- Root Cause: Runtime attempted non-writable fallback path `data/db`, causing `[Errno 13] Permission denied` during DB initialization in data loader stream.
- Files Changed: `docs/plans/IMPLEMENTATION_PLAN.md`, `docs/reports/CVF_CHANGE_TRACE_LOG.md`
- Validation Evidence: Matched Railway production log stack trace (`RuntimeError: Unable to initialize data loader DB: [Errno 13] Permission denied: 'data/db'`) with UI failure state and loader interruption behavior.
- Deployment Target: documentation governance (CVF trace artifacts)
- Deployment Status: completed (local update)
- Commit SHA: N/A (pending next commit)
- Plan Mapping: Section 0.7 `INC-RW-20260302-DUCKDB-PERMISSION` + Section 0.6 P1 persistence policy
- Owner: Codex + project owner
- Notes: This is a trace-evidence update; code fix and redeploy validation remain required before closing incident.

### CVF-TT-20260302-007
- Date-Time (UTC+7): 2026-03-02 14:00
- Type: hotfix
- Scope: Resolve persistent Dashboard `ERROR` by hardening data-loader DB path strategy and SSE failure handling for Railway runtime.
- Impact: Cache read endpoint no longer hard-fails UI on DB init error; load/update streams now emit explicit `error` event; runtime can write DB using root user and fallback `/tmp` path.
- Root Cause: Production runtime hit permission-denied path during DuckDB initialization, causing uncaught exceptions and interrupted streams.
- Files Changed: `packages/interface/src/interface/rest/data_loader.py`, `Dockerfile`
- Validation Evidence: `python -m py_compile packages/interface/src/interface/rest/data_loader.py packages/interface/src/interface/app.py` pass; `pnpm -C frontend exec tsc --noEmit` pass; `pnpm -C frontend exec vitest run __tests__/integration/ws-provider.test.ts __tests__/stores/market-store.test.ts __tests__/stores/signal-store.test.ts` pass (12/12).
- Deployment Target: backend + frontend on Railway
- Deployment Status: pending push/deploy
- Commit SHA: N/A (pending next commit)
- Plan Mapping: Section 0.6 P0/P1 + Section 0.7 `INC-RW-20260302-DUCKDB-PERMISSION`
- Owner: Codex + project owner
- Notes: Canonical Railway env remains `DUCKDB_PATH=/app/data/trading.duckdb`; `/tmp/trading.duckdb` is emergency fallback to keep app operational.

### CVF-TT-20260302-008
- Date-Time (UTC+7): 2026-03-02 14:32
- Type: bugfix
- Scope: Normalize mobile Market Board sector tab button sizing for consistent visual layout.
- Impact: Sector tabs (`VN30`, `Bất động sản`, `Chứng khoán`, ...) now render with equal frame size, eliminating mixed button heights/widths.
- Root Cause: Variable label lengths combined with unconstrained button sizing caused uneven mobile tab dimensions.
- Files Changed: `frontend/app/market-board/page.tsx`
- Validation Evidence: `pnpm -C frontend exec tsc --noEmit` pass; `pnpm -C frontend exec vitest run __tests__/lib/market-sectors.test.ts` pass (5/5).
- Deployment Target: frontend (Railway web)
- Deployment Status: pending push/deploy
- Commit SHA: N/A (pending next commit)
- Plan Mapping: Phase 4 (Frontend & Real-time UI) — mobile usability polish
- Owner: Codex + project owner
- Notes: Implemented fixed-size horizontal grid tabs (`auto-cols-[92px]`, `h-14`) with centered wrapped label text.

### CVF-TT-20260302-009
- Date-Time (UTC+7): 2026-03-02 16:36
- Type: test
- Scope: Add phase-gate test coverage for Data Loader to enforce P0 acceptance before moving to next roadmap phase.
- Impact: Prevents regression where app auto-loads on mount; ensures load stream only starts by explicit user action.
- Root Cause: P0 acceptance criteria previously relied mainly on manual verification, with no direct automated test for auto-load behavior.
- Files Changed: `frontend/__tests__/integration/data-loader.test.tsx`, `docs/plans/IMPLEMENTATION_PLAN.md`, `docs/reports/CVF_CHANGE_TRACE_LOG.md`
- Validation Evidence: `pnpm -C frontend exec tsc --noEmit` pass; `pnpm -C frontend exec vitest run __tests__/integration/data-loader.test.tsx` pass (2/2); `pnpm -C frontend exec vitest run __tests__/integration/data-loader.test.tsx __tests__/integration/ws-provider.test.ts __tests__/stores/market-store.test.ts __tests__/stores/signal-store.test.ts __tests__/lib/market-sectors.test.ts` pass (19/19).
- Deployment Target: frontend + CVF governance docs
- Deployment Status: pending push/deploy
- Commit SHA: N/A (pending next commit)
- Plan Mapping: Section 0.6 P0 + Section 0.8 Phase Execution Status
- Owner: Codex + project owner
- Notes: P0 marked gated-complete; P1 remains in-progress pending Railway production smoke validation.

### CVF-TT-20260303-010
- Date-Time (UTC+7): 2026-03-03 07:20
- Type: test
- Scope: Continue all phases under CVF by implementing and executing end-to-end phase gates (P0/P1 + Phase 1-5) with strict pass-before-next sequencing.
- Impact: Project now has a repeatable gate runner (`scripts/phase-gates.ps1`) and verified pass snapshot across roadmap phases, including Railway production smoke for P1.
- Root Cause: Phase progression previously depended on ad-hoc command runs; lacked one deterministic gate command and formal status closure for P1/Phase 1-5.
- Files Changed: `scripts/phase-gates.ps1`, `packages/adapters/src/adapters/duckdb/connection.py`, `docs/plans/IMPLEMENTATION_PLAN.md`, `docs/reports/CVF_CHANGE_TRACE_LOG.md`
- Validation Evidence: `powershell -ExecutionPolicy Bypass -File scripts/phase-gates.ps1 -Phase all` pass; includes P1 production API smoke on Railway backend (`health/live`, `load-data`, `cached-data`, `update-data`, `check-updates`) and local test gates for Phase 1-5. Added compatibility function `create_connection()` and verified with `python -m pytest tests/integration/test_duckdb_repo.py -q` (10/10).
- Deployment Target: backend/frontend workflow + CVF governance docs
- Deployment Status: pending push/deploy
- Commit SHA: N/A (pending next commit)
- Plan Mapping: Section 0.8 Phase Execution Status + Phase 1/2/3/4/5 gate workflow
- Owner: Codex + project owner
- Notes: Phase 3 test run reported 2 runtime warnings in `test_risk_agent.py` (`AsyncMock` coroutine not awaited); non-blocking for current gate but should be cleaned in next test-hardening cycle.

### CVF-TT-20260303-011
- Date-Time (UTC+7): 2026-03-03 08:50
- Type: bugfix
- Scope: Remove Phase 3 runtime warnings by hardening `RiskAgent` repository-call execution for both sync and async adapters, then re-run full CVF gates.
- Impact: Eliminated `AsyncMock coroutine was never awaited` warnings in risk-agent tests; improved adapter compatibility without changing gate behavior.
- Root Cause: `RiskAgent` previously executed repository callables via `asyncio.to_thread` unconditionally, which can return awaitables for async mocks/functions and trigger unawaited coroutine warnings.
- Files Changed: `packages/agents/src/agents/risk_agent.py`, `docs/plans/IMPLEMENTATION_PLAN.md`, `docs/reports/CVF_CHANGE_TRACE_LOG.md`
- Validation Evidence: `python -m py_compile packages/agents/src/agents/risk_agent.py` pass; `python -m pytest tests/unit/test_risk_agent.py tests/unit/test_supervisor_routing.py -q` pass (13/13); `powershell -ExecutionPolicy Bypass -File scripts/phase-gates.ps1 -Phase phase3` pass; `powershell -ExecutionPolicy Bypass -File scripts/phase-gates.ps1 -Phase all` pass (P0/P1 + Phase 1-5).
- Deployment Target: backend agent runtime + CVF governance docs
- Deployment Status: pending push/deploy
- Commit SHA: N/A (pending next commit)
- Plan Mapping: Section 0.8 Core Phase 1-5 status snapshot (hardening update)
- Owner: Codex + project owner
- Notes: Phase gates remain deterministic through `scripts/phase-gates.ps1`.
