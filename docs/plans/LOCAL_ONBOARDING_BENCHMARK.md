# Local Onboarding Benchmark

## CVF Traceability
- CVF-Doc-ID: CVF-TT-LOCAL-ONBOARD-20260304-R1
- Last-Updated: 2026-03-04
- Plan Mapping: `LOCAL_PERSONAL_TRADING_ROADMAP.md` -> Phase 1 exit criteria

## Objective
Measure first-time local onboarding time and verify target:
- New user can run app locally in `<= 15 minutes`.

## Benchmark Command
Prerequisite: backend API is running at `http://localhost:8000`.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/benchmark-onboarding.ps1 -ApiBase http://localhost:8000/api -DuckDbPath data/trading.duckdb
```

Optional full install timing:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/benchmark-onboarding.ps1 -IncludeInstall
```

## Output Artifact
- Generated report path:
  - `docs/reports/LOCAL_ONBOARDING_BENCHMARK_LATEST.md`

## Acceptance Rule
- `Result = PASS`
- `Target (<= 15 min) = met`
- No failed steps in benchmark table.
