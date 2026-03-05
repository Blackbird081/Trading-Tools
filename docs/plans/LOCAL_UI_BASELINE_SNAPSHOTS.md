# Local UI Baseline Snapshots

## CVF Traceability
- CVF-Doc-ID: CVF-TT-LOCAL-UI-BASELINE-20260305-R2
- Last-Updated: 2026-03-05
- Plan Mapping: `UI_EVALUATION_ROADMAP.md` -> `UI-P0`, `UI-P1`, `UI-P2`
- Purpose: Lock post-hardening UI baseline before release validation.

## Snapshot Log (Baseline R2)

1. Dashboard
- Route: `/dashboard`
- Baseline behavior:
  - `MarketIndexBar` and data-loader flow are active.
  - Desktop right panel shows session overview stats.
  - Legacy dashboard `trading-chart.tsx` path is removed from active UI bundle.

2. Market Board
- Route: `/market-board`
- Baseline behavior:
  - Mobile sector buttons keep normalized fixed height (`h-14`) and consistent width behavior.
  - Desktop shows paged 3-column sector board.
  - Mobile supports swipe + button navigation by sector.

3. Portfolio
- Route: `/portfolio`
- Baseline behavior:
  - Portfolio summary and PnL sections follow shared spacing tokens (`p-3 sm:p-4` outer shell).
  - Data remains sourced from backend portfolio endpoints.

4. Orders
- Route: `/orders`
- Baseline behavior:
  - Runtime safety badges are visible above order controls (mode, kill-switch, provider, session).
  - Order form supports lot-size validation and explicit dry-run/live mode selection.
  - Order list is wired to backend order APIs.

5. Screener
- Route: `/screener`
- Baseline behavior:
  - Runtime safety badges are visible before pipeline execution.
  - Pipeline run mode selection (`dry-run`/`live`) is explicit.
  - Expanded result details display current selected run mode.

6. Settings
- Route: `/settings`
- Baseline behavior:
  - Setup Wizard keeps explicit `Save Draft` / `Apply Draft` / `Revert` actions.
  - Inline action hint appears after save/apply/revert to reduce operator mistakes.
  - Page spacing and heading scale match cross-page layout tokens.

## Notes
- This artifact tracks behavior baseline for release-gate evidence.
- Any intentional UI behavior changes after R2 must append CVF trace references.
