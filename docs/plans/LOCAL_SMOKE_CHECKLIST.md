# Local Smoke Checklist

## CVF Traceability
- CVF-Doc-ID: CVF-TT-LOCAL-SMOKE-20260303-R1
- Last-Updated: 2026-03-03
- Owner: QA + Engineering
- Plan Mapping: `LOCAL_PERSONAL_TRADING_ROADMAP.md` -> Phase 0 exit criteria

## Pre-Run
1. `uv sync` completed.
2. `pnpm -C frontend install` completed.
3. `.env` exists and minimum runtime variables are present.
4. Local data path exists or can be initialized:
   - default: `data/trading.duckdb`

## Backend Smoke
1. Start API:
   - `uv run uvicorn interface.app:app --reload --port 8000`
2. Health checks:
   - `GET /api/health` => `200`
   - `GET /api/health/live` => `200`
   - `GET /api/health/ready` => `200`
3. Setup status:
   - `GET /api/setup/status` => `200`
4. Local init:
   - `POST /api/setup/init-local` => `status=initialized`

## Data Loader Smoke
1. Open stream:
   - `GET /api/load-data?preset=VN30&years=1`
2. Verify completion event:
   - SSE includes `event: complete`
3. Verify cache:
   - `GET /api/cached-data?preset=VN30` has `symbol_count > 0`
4. Incremental update:
   - `GET /api/update-data?preset=VN30` ends with `event: complete`

## Frontend Smoke
1. Start web:
   - `pnpm -C frontend dev`
2. Dashboard:
   - App opens without auto-load.
   - `Load` button triggers load explicitly.
3. Setup Wizard (`/settings`):
   - Can input config.
   - Can run `Validate`.
   - Can run `Refresh Runtime Status`.
   - Can run `Initialize Local Data Path`.

## Trading UI Smoke
1. Orders page renders form + history.
2. Portfolio page renders without crash.
3. Screener page can start pipeline stream and show progress.

## Result Record
- Date-Time (UTC+7):
- Environment:
- Passed items:
- Failed items:
- Notes:
- Baseline snapshot updated:
  - `docs/plans/LOCAL_UI_BASELINE_SNAPSHOTS.md`
