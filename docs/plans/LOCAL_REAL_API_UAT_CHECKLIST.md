# Local Real API UAT Checklist (Pre-Release)

## CVF Traceability
- CVF-Doc-ID: CVF-TT-LOCAL-UAT-REALKEY-20260305-R1
- Last-Updated: 2026-03-05
- Plan Mapping: `LOCAL_PERSONAL_TRADING_ROADMAP.md` -> Phase 3/4 + `AI-09` + `OPS-01`
- Goal: Validate real credentials/runtime behavior before allowing wider user rollout.

## 0. Rules (Mandatory)
1. Start with very small test size only (minimum lot) and test account if available.
2. Keep `TRADING_MODE=dry-run` by default; switch to `live` only for controlled steps.
3. Keep kill-switch ready before first live order:
   - `POST /api/safety/kill-switch` with `{"active":true,"reason":"pre-live guard"}`
4. All failures must be logged with `X-Correlation-ID` and captured in CVF trace.

## 1. Pre-UAT Environment Gate
1. Confirm build is up to date:
   - `git rev-parse HEAD`
2. Run release validation bundle:
   - `powershell -ExecutionPolicy Bypass -File scripts/release-validation.ps1`
3. Confirm latest artifacts are `PASS`:
   - `docs/reports/LOCAL_RELEASE_VALIDATION_LATEST.md`
   - `docs/reports/AI_RELIABILITY_WEEKLY_LATEST.md`
4. Confirm runtime storage:
   - `DUCKDB_PATH` points to persistent path.
   - Backup completed:
     - `powershell -ExecutionPolicy Bypass -File scripts/data-cache-backup.ps1`

## 2. Real Key Injection and Setup Validation
1. In Settings, fill and save real keys:
   - `VNSTOCK_API_KEY`
   - `SSI_CONSUMER_ID`, `SSI_CONSUMER_SECRET`, `SSI_ACCOUNT_NO`, `SSI_PRIVATE_KEY_B64` (or configured secure tier)
   - AI provider key(s) and model mapping
2. Validate setup API:
   - `GET /api/setup/status`
   - Expected:
     - `ssi_credentials = ok`
     - selected `agent_ai_provider = ok`
     - `cache_integrity = ok`
3. Validate external probes:
   - `POST /api/setup/probe-external`
   - Capture latency and warning details.

## 3. Market Data and Cache UAT
1. Run manual load (no auto-load):
   - Dashboard -> `Load` with VN30 (1Y), then TOP100 (3Y or selected target).
2. Refresh browser (`F5`) and verify cache restore:
   - symbol count and rows are retained.
3. Run incremental update:
   - Dashboard -> `Update`
4. Validate endpoints:
   - `GET /api/cached-data?preset=VN30`
   - `GET /api/check-updates?preset=VN30`
5. Pass criteria:
   - No stream interruption/error status.
   - Cached symbol count consistent across desktop/mobile.

## 4. Live Order UAT (Controlled)
1. Keep kill-switch active; verify live block:
   - Submit one `live` order -> must be blocked.
2. Disable kill-switch for controlled live test:
   - `POST /api/safety/kill-switch` with `{"active":false,"reason":"uat-live-order"}`
3. Place one minimum-lot `BUY` live order:
   - confirm 2-step token flow works.
   - expected status: `PENDING`/`PARTIAL_FILL`/`MATCHED` (broker dependent).
4. Cancel one live pending order:
   - `POST /api/orders/{order_id}/cancel`
5. Validate idempotency:
   - repeat same `idempotency_key` request -> `was_duplicate=true`.
6. Negative path:
   - submit one order exceeding notional guard -> must reject with clear reason.
7. Pass criteria:
   - No silent failure.
   - Broker errors route safely (DLQ and observability events recorded).

## 5. Portfolio Real Sync UAT
1. Query:
   - `GET /api/portfolio`
   - `GET /api/portfolio/positions`
   - `POST /api/portfolio/refresh`
   - `POST /api/portfolio/reconcile`
2. Expected:
   - `source=broker` when live broker is enabled and credentials are valid.
   - reconcile returns deterministic mismatch list if any.
3. Cross-check:
   - Compare `cash`, `purchasing_power`, and one sample position with broker terminal/UI.

## 6. Screener + AI Runtime UAT
1. Run screener in `dry-run`, then `live` mode.
2. Validate result payload has:
   - `fundamental_summary`
   - `ai_subroles`
   - `ai_final_action`
   - `data_sources`
3. Validate role schema behavior:
   - role outputs should be structured and not free-form only.
4. Validate reliability artifacts regenerated after UAT run:
   - `powershell -ExecutionPolicy Bypass -File scripts/run-weekly-reliability-pack.ps1`

## 7. Observability and Incident Drill
1. Capture `X-Correlation-ID` from one successful and one failed request.
2. Query events:
   - `GET /api/observability/events?flow=orders&limit=50`
   - `GET /api/observability/events?flow=ws&limit=50`
   - `GET /api/observability/events?flow=screener&limit=50`
3. Execute emergency drill:
   - `powershell -ExecutionPolicy Bypass -File scripts/emergency-fallback-drill.ps1`
4. Pass criteria:
   - failed flows traceable by correlation-id.
   - kill-switch + dry-run fallback verified.

## 8. Security and Redaction Check
1. Review logs around setup/order failures.
2. Verify no plaintext secrets are emitted in logs/API errors.
3. Verify profile vault operations:
   - create/activate/export/import/rotate/revoke.

## 9. Go / No-Go Criteria
Release is **GO** only when all are true:
1. Release validation artifact is `PASS`.
2. Real key setup/status checks are `ok`.
3. At least one controlled live order lifecycle is successful.
4. Portfolio source/reconcile is verified against broker UI.
5. Observability + emergency drill pass.
6. CVF trace entry includes full evidence and decision.

Release is **NO-GO** if any below occurs:
1. Live order cannot be traced end-to-end by correlation-id.
2. Secret leakage in log/error payload.
3. Portfolio broker values cannot be validated.
4. High-severity drift gate policy fails and is not signed off.

## 10. Evidence Template (Fill During UAT)
- Build/Commit:
- UAT Date-Time (UTC+7):
- Tester:
- Environment (local/railway):
- Broker Provider:
- AI Provider + Model:
- Result:
  - Data Load/Update:
  - Live Order Lifecycle:
  - Portfolio Sync/Reconcile:
  - Screener/AI:
  - Observability/Drill:
- Go/No-Go:
- Notes / Risk Acceptance:
- CVF Trace ID:
