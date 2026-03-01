# Market Board Mobile Refactor Roadmap (v2)

## CVF Traceability
- CVF-Doc-ID: CVF-MB-MOBILE-20260301-R2
- Owner: Frontend
- Last-Updated: 2026-03-01
- Status: Draft for approval
- Related files:
  - frontend/app/market-board/page.tsx
  - frontend/components/sector-column.tsx
  - frontend/app/(dashboard)/_components/data-loader.tsx
  - frontend/components/market-index-bar.tsx
  - frontend/components/top-nav.tsx

## Confirmed Decisions
1. Keep symbol popup when user taps any ticker code (no regression).
2. Mobile market-board must show one category per screen (vertical scroll for full list).
3. Add/keep swipe left-right on mobile header to switch category.
4. Dashboard is main tab; data controls stay there and should be compacted.
5. Market-board should hide duplicated data controls (Market Data, VN30/Top100, years, Load).
6. Remove duplicate LIVE indicator in top area to reduce visual noise.
7. Add color intensity scale for gain/loss with neutral amber for 0%.

## Problem Summary
- Current market-board categories are hard-coded to 6 blocks; not auto-generated from loaded Top100 data.
- Swipe left-right exists but difficult to validate when tabs fit exactly in viewport and threshold is strict.
- Vertical read flow is improved but still needs stricter mobile-first interaction polish.
- Data controls are duplicated between Dashboard and Market Board.
- Top area shows LIVE twice (TopNav + IndexBar), causing redundancy.

## Scope
### In scope
- Mobile UX for Dashboard + Market Board only.
- Category generation logic for Market Board from loaded symbol universe.
- Gesture behavior (vertical scroll + horizontal swipe).
- Visual encoding for performance intensity (red/amber/green gradient).

### Out of scope
- Portfolio/Screener/Orders behavior changes.
- Backend API contract changes unless strictly required.

## Phase Plan

### Phase 1 - Mobile Board Interaction Baseline (P1)
Goal: stable gesture behavior + decluttered board screen.
- Keep one category per screen on mobile.
- Ensure vertical scroll always works inside long category lists.
- Keep swipe left-right on header area only (avoid collision with vertical list scroll).
- Lower swipe threshold for iPhone usability.
- Keep desktop layout unchanged (3 columns + pagination).

Deliverables:
- Market board mobile can always scroll to bottom symbols.
- Swipe left-right works with normal finger movement.

### Phase 2 - Remove Duplicate Controls on Market Board (P2)
Goal: market-board becomes data-consumer screen only.
- Hide/collapse `DataLoader` section on `/market-board` (mobile-first, and optionally full page).
- Keep only category chips + sector table on Market Board.
- Preserve current data source from shared store (loaded from Dashboard).

Deliverables:
- Market board screen is cleaner and gains more usable content height.

### Phase 3 - Dynamic Category Generation (P3)
Goal: category list is not fixed to 6 hard-coded groups.
- Replace static `SECTORS` constant with generated categories from loaded symbol set.
- Build sector mapping strategy:
  - First choice: use available sector metadata if already present in data flow.
  - Fallback: local classification map for known symbols + `Khac` bucket.
- Render horizontal category rail as scrollable when category count > viewport width.
- Keep tap-to-open popup unchanged.

Deliverables:
- Category count adapts to VN30/Top100 dataset.
- User can access all categories via horizontal scroll and swipe.

### Phase 4 - Dashboard Mobile Control Compaction (P4)
Goal: dashboard keeps full control with less vertical space.
- In `DataLoader` mobile layout, place `VN30`, `Top100`, and `Load/Update` in one row.
- Keep years slider on next row.
- Keep current behavior for loading/cancel/update unchanged.

Deliverables:
- Dashboard control panel uses one less row on mobile.
- No loss of function.

### Phase 5 - Remove Duplicate LIVE in Top Area (P5)
Goal: reduce redundant status text.
- Keep LIVE indicator in `TopNav` as primary status indicator.
- Hide LIVE label in `MarketIndexBar` on mobile (or remove fully by feature flag).
- Keep connection logic unchanged; only UI label location changes.

Impact analysis:
- Functional impact: none (status source remains `connectionStatus`).
- UX impact: cleaner top area, less duplicate text.

### Phase 6 - Color Scale and Sort Readability (P6)
Goal: richer visual hierarchy for up/down/neutral moves.
- Introduce intensity levels by `changePct` magnitude.
- Use neutral amber style when `% = 0` to separate green and red zones.
- Apply gradient intensity for both directions:
  - Red zone: light red -> medium red -> deep red.
  - Green zone: light green -> medium green -> deep green.
- Apply same scale consistently on row background tint + price text + `%` text.
- Validate contrast on dark theme for iPhone screens.

Proposed bands:
- Strong down: <= -3.0% (deep red)
- Medium down: -3.0% to -1.0% (medium red)
- Light down: -1.0% to < 0% (light red)
- Neutral: 0% (light amber)
- Light up: > 0% to 1.0% (light green)
- Medium up: > 1.0% to 3.0% (medium green)
- Strong up: > 3.0% (deep green)
### Phase 7 - QA, Coverage, and Release (P7)
Goal: confirm stability and standards.
- Test viewports: 390x844, 393x852, 430x932.
- Verify no regression for ticker popup interaction.
- Run: lint, type-check, unit test, coverage.
- Add tests for:
  - swipe navigation behavior,
  - market-board without DataLoader controls,
  - dynamic category rendering,
  - color band mapping.

Target:
- Frontend tests pass.
- Coverage meets project baseline (report exact value in release note).

## Risks and Mitigations
- Risk: Missing reliable sector metadata for all Top100 symbols.
  - Mitigation: local classification map + fallback `Khac` category.
- Risk: Gesture conflict (horizontal swipe vs vertical scroll).
  - Mitigation: detect direction lock and handle swipe only in header area.
- Risk: Visual noise if color intensity too strong.
  - Mitigation: use alpha-based gradients and contrast checks.

## Acceptance Criteria
1. Market Board mobile shows one category at a time and can scroll to all symbols.
2. Market Board no longer duplicates Dashboard data controls.
3. Category list can exceed 6 and still be navigable (scrollable chips + swipe).
4. Ticker tap still opens symbol popup.
5. Dashboard mobile control panel is more compact (`VN30 | Top100 | Load` same row).
6. Top area no longer shows duplicated LIVE on mobile.
7. Red/green zones use gradient intensity (light -> medium -> deep) tied to % change magnitude.
8. 0% rows are visually neutral (amber), clearly separated from red/green ranges.

## Execution Order
1. P2 (remove duplicate controls) + P1 (gesture baseline)
2. P4 (dashboard compact row)
3. P5 (remove duplicate LIVE)
4. P3 (dynamic categories)
5. P6 (color intensity)
6. P7 (QA + coverage + release)

