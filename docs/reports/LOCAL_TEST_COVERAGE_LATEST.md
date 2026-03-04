# Local Test Coverage Report (Latest)

- Generated-At (local): 2026-03-04 10:06:58
- Scope: roadmap regression suite (backend integration + frontend focused tests)

## Backend Coverage
- Statements: 54.53% (638/1170)
- Key files:
  - interface/rest/orders.py: 87%
  - interface/rest/portfolio.py: 90%
  - interface/rest/setup.py: 72%
  - interface/rest/data_loader.py: 50%

## Frontend Coverage
- Statements: 8.75% (580/6622)
- Branches: 48.38% (60/124)
- Functions: 18.64% (11/59)
- Key tested files:
  - app/(dashboard)/_components/data-loader.tsx: 64.8%
  - stores/market-store.ts: 100%
  - stores/signal-store.ts: 100%
  - lib/market-sectors.ts: 99.23%

## Commands
- backend: python -m pytest tests/integration/test_setup_api.py tests/integration/test_local_product_api.py tests/integration/test_order_safety_controls.py --cov=packages/interface/src/interface/rest --cov=packages/adapters/src/adapters/vnstock --cov-report=term --cov-report=json:coverage-backend.json
- frontend: pnpm -C frontend exec vitest run __tests__/integration/data-loader.test.tsx __tests__/stores/market-store.test.ts __tests__/stores/signal-store.test.ts __tests__/lib/market-sectors.test.ts --coverage --coverage.reporter=text-summary --coverage.reporter=json-summary --coverage.reportsDirectory=coverage

## Notes
- Frontend total coverage is low because this run targets regression scope, not full test suite.
- For release-grade global coverage target, run full frontend/backend suites with coverage gates.
