# Local UI Baseline Snapshots

## CVF Traceability
- CVF-Doc-ID: CVF-TT-LOCAL-UI-BASELINE-20260303-R1
- Last-Updated: 2026-03-03
- Plan Mapping: `LOCAL_PERSONAL_TRADING_ROADMAP.md` -> Phase 0
- Purpose: Lock baseline UI behavior before deeper local-product refactor.

## Snapshot Log (Baseline R1)

1. Dashboard
- Route: `/dashboard`
- Baseline behavior:
  - Data loader is user-triggered (`Load`/`Update`), no auto-load.
  - Market data table renders from cache/store.
  - Desktop includes session overview panel.

2. Market Board
- Route: `/market-board`
- Baseline behavior:
  - Mobile shows one sector at a time with swipe/category rail.
  - Desktop shows paged 3-column sector board.
  - No duplicate data-loader controls on this screen.

3. Portfolio
- Route: `/portfolio`
- Baseline behavior:
  - Page renders placeholder NAV/Cash/PnL values.
  - Positions and PnL chart are UI-first placeholders, not broker-synced.

4. Orders
- Route: `/orders`
- Baseline behavior:
  - Order form validates lot-size and local fields.
  - Actions remain frontend-local (not yet wired to backend order API).

5. Screener
- Route: `/screener`
- Baseline behavior:
  - Pipeline runner streams staged events.
  - Current backend path still includes simulated result stream.

6. Settings
- Route: `/settings`
- Baseline behavior:
  - Setup wizard can draft config, validate input format, check runtime setup status, and initialize local data path.

## Notes
- This artifact is a behavior baseline log; visual image attachments can be stored in external release notes if required.
- Any intentional behavior change from this baseline should reference this doc in CVF trace entry.

