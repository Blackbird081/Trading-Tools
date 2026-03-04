# Local Release Checklist

## CVF Traceability
- CVF-Doc-ID: CVF-TT-LOCAL-REL-20260304-R1
- Last-Updated: 2026-03-04
- Plan Mapping: `LOCAL_PERSONAL_TRADING_ROADMAP.md` -> Phase 7

## 1. Pre-Release Gate
1. `pnpm -C frontend exec tsc --noEmit` passes.
2. Frontend core tests pass:
   - `pnpm -C frontend exec vitest run __tests__/integration/data-loader.test.tsx __tests__/stores/market-store.test.ts __tests__/stores/signal-store.test.ts __tests__/lib/market-sectors.test.ts`
3. Backend integration smoke passes:
   - `python -m pytest tests/integration/test_fastapi.py tests/integration/test_setup_api.py tests/integration/test_local_product_api.py -q`
4. `python -m py_compile` passes for changed backend files.
5. `docs/reports/CVF_CHANGE_TRACE_LOG.md` updated with validation evidence.
6. One-shot validation script passes:
   - `powershell -ExecutionPolicy Bypass -File scripts/release-validation.ps1`
   - Output artifact: `docs/reports/LOCAL_RELEASE_VALIDATION_LATEST.md`

## 2. Local Packaging Validation (Clean Machine)
1. Clone fresh repo on clean machine.
2. Install Python + Node toolchain.
3. Install dependencies.
4. Start backend + frontend.
5. Execute `docs/plans/LOCAL_SMOKE_CHECKLIST.md`.
6. Verify setup wizard + encrypted profile vault flow:
   - create profile
   - activate profile
   - export/import profile
   - rotate passphrase
   - revoke profile

## 3. Upgrade Validation
1. Prepare baseline runtime data:
   - at least one cached dataset in DuckDB
   - at least one dry-run order
2. Pull new release branch/tag.
3. Run API startup and smoke:
   - `/api/health`
   - `/api/portfolio`
   - `/api/orders`
   - `/api/screener/history`
4. Verify data compatibility:
   - old orders still readable
   - cached market data still loadable
   - setup profiles remain decryptable

## 4. Rollback Validation
1. Keep previous release tag available.
2. Roll back code to previous tag without deleting data/profile files.
3. Start app and verify:
   - health endpoint available
   - read-only operations (`portfolio/orders/list`) still work
4. Document rollback result in CVF trace entry.
5. Run emergency fallback drill before final sign-off:
   - `powershell -ExecutionPolicy Bypass -File scripts/emergency-fallback-drill.ps1`
   - Output artifact: `docs/reports/LOCAL_EMERGENCY_DRILL_LATEST.md`

## 5. Release Output
1. Release notes include:
   - major feature/fix list
   - known limitations
   - migration notes
2. CVF trace entry has:
   - commands run
   - pass/fail status
   - commit SHA
   - deployment target
