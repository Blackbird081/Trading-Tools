# Local Operator Runbook

## CVF Traceability
- CVF-Doc-ID: CVF-TT-LOCAL-OPS-20260304-R1
- Last-Updated: 2026-03-04
- Plan Mapping: `LOCAL_PERSONAL_TRADING_ROADMAP.md` -> `OPS-01`

## 1. Incident Triage (First 10 Minutes)
1. Capture current `X-Correlation-ID` from browser/API response.
2. Check health:
   - `GET /api/health/live`
   - `GET /api/health/ready`
3. Query failed-flow events:
   - `GET /api/observability/events?flow=screener&limit=50`
   - `GET /api/observability/events?flow=orders&limit=50`
4. Identify blast radius:
   - data loader (`/api/cached-data`, `/api/check-updates`)
   - screener pipeline (`/api/run-screener`)
   - order flow (`/api/orders`)

## 2. Immediate Containment
1. Toggle kill-switch if live trading is impacted:
   - `POST /api/safety/kill-switch` with `{"active":true,"reason":"incident"}`
2. Force dry-run fallback:
   - set `TRADING_MODE=dry-run`
3. Pause optional external AI/news dependencies if unstable:
   - set `SCREENER_USE_EXTERNAL=false`

## 3. Recovery Procedures
### 3.1 Data Cache Recovery
1. Backup current DB:
   - `powershell -ExecutionPolicy Bypass -File scripts/data-cache-backup.ps1`
2. Restore known-good backup if needed:
   - `powershell -ExecutionPolicy Bypass -File scripts/data-cache-restore.ps1`
3. Validate:
   - `GET /api/setup/status` (`cache_integrity` should be `ok`)

### 3.2 Key Rotation
1. Rotate profile passphrase in Settings or API:
   - `POST /api/setup/profiles/rotate`
2. Revoke compromised profile:
   - `POST /api/setup/profiles/revoke`
3. Create new encrypted profile and activate.

### 3.3 Reliability Check
1. Run weekly reliability pack:
   - `powershell -ExecutionPolicy Bypass -File scripts/run-weekly-reliability-pack.ps1`
2. Review:
   - `docs/reports/AI_RELIABILITY_WEEKLY_LATEST.md`

## 4. Rollback
1. Follow `docs/plans/LOCAL_UPGRADE_ROLLBACK_GUIDE.md`.
2. Verify core APIs after rollback:
   - `/api/health`
   - `/api/orders`
   - `/api/portfolio`
3. Re-run emergency drill:
   - `powershell -ExecutionPolicy Bypass -File scripts/emergency-fallback-drill.ps1`

## 5. Closure Checklist
1. Kill-switch status restored intentionally (`active=false`) after verification.
2. Observability events reviewed by correlation-id for root cause.
3. CVF trace entry updated with:
   - root cause,
   - evidence commands,
   - recovery/rollback outcome.
