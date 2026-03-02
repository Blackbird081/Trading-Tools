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
