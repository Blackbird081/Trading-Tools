# Local Test Coverage Report (Latest)

- Generated-At (local): 2026-03-04 10:35
- Scope: pre-live API-key safety gate + frontend regression snapshot

## Backend Critical Gate Coverage
- Gate result: PASS (`--cov-fail-under=90`)
- Total (critical modules): 96% (722/756)
- Module breakdown:
  - `interface.rest.data_loader`: 94%
  - `interface.profile_vault`: 99%
  - `adapters.vnstock.news`: 98%

## Frontend Regression Snapshot
- Statements: 8.75% (580/6622)
- Branches: 48.38% (60/124)
- Functions: 18.64% (11/59)
- Key tested files:
  - `app/(dashboard)/_components/data-loader.tsx`: 64.8%
  - `stores/market-store.ts`: 100%
  - `stores/signal-store.ts`: 100%
  - `lib/market-sectors.ts`: 99.23%

## Commands
- backend critical gate:
  - `python -m pytest tests/integration/test_setup_profiles_api.py tests/integration/test_data_loader_api.py tests/unit/test_data_loader_helpers.py tests/unit/test_vnstock_news_adapter.py tests/unit/test_profile_vault.py --cov=interface.profile_vault --cov=interface.rest.data_loader --cov=adapters.vnstock.news --cov-fail-under=90 --cov-report=term -q`
- frontend regression snapshot:
  - `pnpm -C frontend exec vitest run __tests__/integration/data-loader.test.tsx __tests__/stores/market-store.test.ts __tests__/stores/signal-store.test.ts __tests__/lib/market-sectors.test.ts --coverage --coverage.reporter=text-summary --coverage.reporter=json-summary --coverage.reportsDirectory=coverage`

## Notes
- Pre-live gate now enforces >90% for backend modules directly involved in data loading, cache persistence, and profile vault handling.
- Frontend global total is still below 90%; additional test expansion is required before claiming full-stack 90% coverage.
