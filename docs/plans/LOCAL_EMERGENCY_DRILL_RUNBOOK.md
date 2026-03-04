# Local Emergency Drill Runbook

## CVF Traceability
- CVF-Doc-ID: CVF-TT-LOCAL-DRILL-20260304-R1
- Last-Updated: 2026-03-04
- Plan Mapping: `LOCAL_PERSONAL_TRADING_ROADMAP.md` -> Phase 6 exit criteria

## Objective
Verify live trading safety controls and emergency fallback behavior:
- kill switch blocks live order placement,
- live flow requires two-step confirmation,
- broker-disabled live order is routed to DLQ (no silent order loss),
- DLQ visibility endpoint remains healthy.

## Drill Command
Prerequisite: backend API running and `ENABLE_LIVE_BROKER=false`.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/emergency-fallback-drill.ps1 -ApiBase http://localhost:8000/api
```

## Output Artifact
- `docs/reports/LOCAL_EMERGENCY_DRILL_LATEST.md`

## Acceptance
- Report `Result = PASS`
- No failed row in drill table
- Evidence contains all steps:
  - kill switch block
  - confirm token challenge
  - DLQ fallback
  - DLQ visibility.
