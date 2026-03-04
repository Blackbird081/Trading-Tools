# AI Reliability Eval Pack

## CVF Traceability
- CVF-Doc-ID: CVF-TT-AI-REL-20260304-R1
- Last-Updated: 2026-03-04
- Owner: Agents + QA
- Scope: Quant benchmark, provider A/B consensus validation, and weekly drift monitoring.

## Objective
Add three evidence-grade quality layers before live API-key rollout:
1. Quant benchmark on fixed historical dataset (`Precision@K`, `Hit-rate`, `MDD`).
2. Provider A/B comparison with consensus validation.
3. Weekly drift monitoring (`AI recommendation` vs realized outcome).

## Artifacts
- Fixed dataset: `tests/evals/data/recommendation_outcomes_fixed.csv`
- A/B dataset: `tests/evals/data/provider_ab_consensus_fixed.csv`
- Shared metrics: `tests/evals/reliability_metrics.py`
- Benchmark runner: `tests/evals/benchmark_fixed_dataset.py`
- A/B consensus runner: `tests/evals/provider_ab_consensus.py`
- Drift runner: `tests/evals/weekly_drift_monitor.py`
- Unified pack runner: `tests/evals/run_reliability_pack.py`

## Runbook
```powershell
uv run python tests/evals/benchmark_fixed_dataset.py
uv run python tests/evals/provider_ab_consensus.py
uv run python tests/evals/weekly_drift_monitor.py
uv run python tests/evals/run_reliability_pack.py
```

Output reports are written to `tests/evals/results/`.

## Acceptance
- Quant benchmark report includes all mandatory metrics: `precision_at_k`, `hit_rate`, `max_drawdown`.
- A/B report includes `agreement_rate`, per-provider hit-rate, and `consensus_hit_rate`.
- Drift report includes per-week summary and explicit `drift_alerts`.
- Unit validation: `tests/unit/test_reliability_eval_pack.py` passes.

## Next Step (Post-baseline)
- Replace fixed datasets with rolling production snapshots (versioned by week).
- Add CI weekly job to auto-run drift monitor and fail on severe drift.
- Wire metrics to Screener history endpoint for in-app observability.

