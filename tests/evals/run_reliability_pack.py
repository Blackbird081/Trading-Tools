"""Run all three reliability layers in one command."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

try:
    from tests.evals.benchmark_fixed_dataset import DEFAULT_DATASET as BENCH_DATASET
    from tests.evals.provider_ab_consensus import (
        DEFAULT_DATASET as AB_DATASET,
        evaluate_provider_ab,
        load_predictions,
    )
    from tests.evals.provider_parity_calibration import evaluate_provider_parity
    from tests.evals.reliability_metrics import evaluate_quant_benchmark, load_outcomes_csv
    from tests.evals.weekly_drift_monitor import detect_drift, summarize_weekly
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from benchmark_fixed_dataset import DEFAULT_DATASET as BENCH_DATASET  # type: ignore[no-redef]
    from provider_ab_consensus import (  # type: ignore[no-redef]
        DEFAULT_DATASET as AB_DATASET,
        evaluate_provider_ab,
        load_predictions,
    )
    from provider_parity_calibration import evaluate_provider_parity  # type: ignore[no-redef]
    from reliability_metrics import evaluate_quant_benchmark, load_outcomes_csv  # type: ignore[no-redef]
    from weekly_drift_monitor import detect_drift, summarize_weekly  # type: ignore[no-redef]

RESULTS_DIR = Path("tests/evals/results")


def main() -> None:
    outcomes = load_outcomes_csv(BENCH_DATASET)
    benchmark = evaluate_quant_benchmark(outcomes, k=10)

    ab_rows = load_predictions(AB_DATASET)
    ab_metrics = evaluate_provider_ab(ab_rows)
    parity = evaluate_provider_parity(ab_rows)

    weekly = summarize_weekly(outcomes)
    drift = detect_drift(weekly, baseline_weeks=4, hit_drop_threshold=0.20)

    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "benchmark_quant": benchmark,
        "provider_ab_consensus": ab_metrics,
        "provider_parity": parity,
        "weekly_drift": {
            "weeks": weekly,
            "alerts": drift,
        },
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")
    out = RESULTS_DIR / f"reliability_pack_{stamp}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\nSaved reliability pack report: {out}")


if __name__ == "__main__":
    main()
