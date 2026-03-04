# Local Upgrade and Rollback Guide

## CVF Traceability
- CVF-Doc-ID: CVF-TT-LOCAL-UPG-20260304-R1
- Last-Updated: 2026-03-04
- Plan Mapping: `LOCAL_PERSONAL_TRADING_ROADMAP.md` -> Phase 7

## Upgrade Procedure
1. Backup runtime artifacts:
   - `.env`
   - DuckDB file (`DUCKDB_PATH`)
   - profile vault directory (`TRADING_PROFILE_DIR` or `~/.trading/profiles`)
2. Save current commit/tag:
   - `git rev-parse HEAD`
3. Pull latest release:
   - `git fetch --tags`
   - `git checkout <release-tag>`
4. Start app and run smoke:
   - `/api/health`
   - `/api/setup/status`
   - `/api/portfolio`
   - `/api/orders`
5. Validate key flows:
   - place dry-run order
   - portfolio refresh + reconcile
   - run screener once

## Rollback Procedure
1. Stop app.
2. Switch back to previous known-good tag:
   - `git checkout <previous-release-tag>`
3. Keep runtime data/profile files unchanged.
4. Start app and verify:
   - `/api/health` returns healthy/degraded but online
   - `/api/orders` can list historical orders
   - `/api/portfolio` returns non-error response
5. Record rollback outcome in CVF trace log.

## Compatibility Notes
- DuckDB schemas for orders/portfolio/screener run tables are additive and backward-friendly.
- Profile vault stores encrypted blobs; passphrase is required after upgrade/rollback.
- If live broker adapter is disabled, live orders are routed to DLQ by design.
