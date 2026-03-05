# Local Release Validation (Latest)

- Generated-At (local): 2026-03-05 08:04:05
- Overall: PASS

| Step | Status | Exit Code | Seconds | Command |
|---|---|---:|---:|---|
| Frontend type check | PASS | 0 | 4.24 | pnpm -C frontend exec tsc --noEmit |
| Pre-live API quality gate | PASS | 0 | 23.37 | powershell -ExecutionPolicy Bypass -File scripts/pre-live-api-gate.ps1 -StrictWarnings -WithFrontend -BackendCoverageThreshold 90 |
| Weekly reliability pack artifact | PASS | 0 | 0.66 | powershell -ExecutionPolicy Bypass -File scripts/run-weekly-reliability-pack.ps1 |
| Setup API integration | PASS | 0 | 1.72 | python -m pytest tests/integration/test_setup_api.py -q |
| Local product API integration | PASS | 0 | 2.16 | python -m pytest tests/integration/test_local_product_api.py -q |
| Backend compile check | PASS | 0 | 0.11 | python -m py_compile packages/interface/src/interface/rest/setup.py packages/interface/src/interface/rest/data_loader.py packages/interface/src/interface/rest/orders.py packages/adapters/src/adapters/vnstock/news.py |
| Frontend coverage gate | PASS | 0 | 0.07 | frontend lines >= 80% (target 90%) from frontend/coverage/coverage-summary.json (actual: 94.57%) |
