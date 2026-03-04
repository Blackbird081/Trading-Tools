# Local Release Validation (Latest)

- Generated-At (local): 2026-03-04 09:43:23
- Overall: PASS

| Step | Status | Exit Code | Seconds | Command |
|---|---|---:|---:|---|
| Frontend type check | PASS | 0 | 3.98 | pnpm -C frontend exec tsc --noEmit |
| Frontend core tests | PASS | 0 | 5.53 | pnpm -C frontend exec vitest run __tests__/integration/data-loader.test.tsx __tests__/stores/market-store.test.ts __tests__/stores/signal-store.test.ts __tests__/lib/market-sectors.test.ts |
| Setup API integration | PASS | 0 | 2.23 | python -m pytest tests/integration/test_setup_api.py -q |
| Local product API integration | PASS | 0 | 2.78 | python -m pytest tests/integration/test_local_product_api.py -q |
| Safety controls integration | PASS | 0 | 2.33 | python -m pytest tests/integration/test_order_safety_controls.py -q |
| Backend compile check | PASS | 0 | 0.11 | python -m py_compile packages/interface/src/interface/rest/setup.py packages/interface/src/interface/rest/data_loader.py packages/interface/src/interface/rest/orders.py packages/adapters/src/adapters/vnstock/news.py |
