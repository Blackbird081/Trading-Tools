# UI Evaluation Roadmap (Reality-Aligned)

## CVF Traceability
- CVF-Doc-ID: CVF-TT-UI-EVAL-20260305-R2
- Last-Updated: 2026-03-05
- Evaluation basis: current codebase state at commit window around `e4287fc`
- Single source note: this file supersedes former root `Plan.md`.

## A. Current UI Reality (Verified)

### Dashboard
1. `MarketIndexBar` is rendered at top of page.
2. `TradingChart` is not rendered on dashboard flow; symbol popup chart path is used.
3. Desktop right panel now shows session overview stats (replacing empty agent panel).

### Market Board
1. Desktop uses paged 3-column sector layout.
2. Mobile sector buttons are normalized (`h-14`, fixed auto-column width) for consistent size.
3. Mobile has swipe + button navigation across sectors.

### Settings / AI Provider UX
1. Setup wizard supports explicit provider fields for `OpenAI`, `Anthropic`, `Gemini`, `Alibaba`.
2. Per-task model mapping (coder/reasoning/writing) is exposed.
3. Save/Apply/Revert semantics exist (no ambiguous implicit-only save flow).

## B. Product Execution Snapshot (Merged from former Plan.md)

### Completed (gated baseline)
1. P0/P1 loader UX + persistence policy.
2. Core phases 1-5 baseline.
3. Local product phases 1-7 baseline.
4. Security/precision/provider hardening (`AR-1/2/3/5`).
5. AI reliability baseline pack (`AI-R1..AI-R5`).
6. Native provider runtime in Settings (`OpenAI`, `Anthropic`, `Gemini`, `Alibaba`).

### In progress / operational closure
1. Real-key UAT execution with broker credentials (checklist prepared).
2. Rolling dataset calibration for strict AI drift/reliability thresholds.
3. Release-cycle clean-machine validation evidence refresh.

### Next locked execution order
1. Execute `docs/plans/LOCAL_REAL_API_UAT_CHECKLIST.md` end-to-end and record evidence.
2. Run strict release gate:
   - `powershell -ExecutionPolicy Bypass -File scripts/release-validation.ps1 -StrictReliability`
3. Update CVF trace log with GO/NO-GO decision and residual risks.

### Explicit non-goals (current cycle)
1. No unattended live trading before real-account UAT passes.
2. No broad user rollout without completed UAT evidence attachment.

## C. Gaps to Close (UI/Product Readiness)
1. Remove dead code file `frontend/app/(dashboard)/_components/trading-chart.tsx`.
2. Add explicit inline hint/toast after draft save/apply to reduce operator mistakes.
3. Add UI badges for `dry-run/live` and kill-switch status in screener/order views.
4. Add cross-page consistency pass for spacing/typography tokens (desktop vs mobile).

## D. Priority Execution
1. `UI-P0`: dead-code cleanup + message clarity for setup save/apply.
2. `UI-P1`: runtime safety state indicators (`dry-run`, kill-switch, provider).
3. `UI-P2`: visual consistency pass + snapshot update in `docs/plans/LOCAL_UI_BASELINE_SNAPSHOTS.md`.

## E. Acceptance Criteria
1. No orphaned dashboard chart component in production bundle path.
2. Operator can always identify current runtime safety mode in <= 2 clicks.
3. Mobile and desktop critical navigation/components keep consistent sizing and affordance.
