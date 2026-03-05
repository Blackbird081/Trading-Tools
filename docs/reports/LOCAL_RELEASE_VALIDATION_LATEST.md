# Local Release Validation (Latest)

- Generated-At (local): 2026-03-05 08:36:28
- Overall: PASS

| Step | Status | Exit Code | Seconds | Command |
|---|---|---:|---:|---|
| Frontend type check | PASS | 0 | 4.34 | pnpm -C frontend exec tsc --noEmit |
| Pre-live API quality gate | PASS | 0 | 24.46 | powershell -ExecutionPolicy Bypass -File scripts/pre-live-api-gate.ps1 -StrictWarnings -WithFrontend -BackendCoverageThreshold 90 |
| Weekly reliability pack artifact | PASS | 0 | 0.67 | powershell -ExecutionPolicy Bypass -File scripts/run-weekly-reliability-pack.ps1 -MinPrecisionAtK 0.55 -MinHitRate 0.45 -MinConsensusHitRate 0.35 -MinAgreementRate 0.3 -MaxDrawdown 0.25 -FailOnDriftSeverity none |
| Setup API integration | PASS | 0 | 1.79 | python -m pytest tests/integration/test_setup_api.py -q |
| Local product API integration | PASS | 0 | 2.27 | python -m pytest tests/integration/test_local_product_api.py -q |
| Backend compile check | PASS | 0 | 0.12 | python -m py_compile packages/interface/src/interface/rest/setup.py packages/interface/src/interface/rest/data_loader.py packages/interface/src/interface/rest/orders.py packages/adapters/src/adapters/vnstock/news.py |
| Frontend coverage gate | PASS | 0 | 0.07 | frontend lines >= 80% (target 90%) from frontend/coverage/coverage-summary.json (actual: 97.36%) |
