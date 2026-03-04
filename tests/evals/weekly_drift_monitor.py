"""Weekly drift monitor for recommendation quality vs realized outcomes."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

try:
    from tests.evals.reliability_metrics import (
        RecommendationOutcome,
        evaluate_quant_benchmark,
        load_outcomes_csv,
        strategy_return,
    )
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from reliability_metrics import (  # type: ignore[no-redef]
        RecommendationOutcome,
        evaluate_quant_benchmark,
        load_outcomes_csv,
        strategy_return,
    )

DEFAULT_DATASET = Path("tests/evals/data/recommendation_outcomes_fixed.csv")
DEFAULT_RESULTS_DIR = Path("tests/evals/results")


def _week_key(row: RecommendationOutcome) -> str:
    iso = row.dt.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def summarize_weekly(rows: list[RecommendationOutcome], *, k: int = 5) -> list[dict[str, float | str]]:
    grouped: dict[str, list[RecommendationOutcome]] = defaultdict(list)
    for row in rows:
        grouped[_week_key(row)].append(row)

    out: list[dict[str, float | str]] = []
    for wk in sorted(grouped):
        seq = grouped[wk]
        metrics = evaluate_quant_benchmark(seq, k=min(k, len(seq)))
        avg_strategy_return = sum(strategy_return(r) for r in seq) / len(seq) if seq else 0.0
        out.append(
            {
                "week": wk,
                "sample_size": metrics["sample_size"],
                "hit_rate": metrics["hit_rate"],
                "precision_at_k": metrics["precision_at_k"],
                "max_drawdown": metrics["max_drawdown"],
                "avg_strategy_return": avg_strategy_return,
            }
        )
    return out


def detect_drift(
    weekly: list[dict[str, float | str]],
    *,
    baseline_weeks: int = 4,
    hit_drop_threshold: float = 0.20,
) -> list[dict[str, float | str]]:
    alerts: list[dict[str, float | str]] = []
    if len(weekly) <= baseline_weeks:
        return alerts

    for idx in range(baseline_weeks, len(weekly)):
        baseline = weekly[idx - baseline_weeks:idx]
        current = weekly[idx]
        base_hit = sum(float(x["hit_rate"]) for x in baseline) / baseline_weeks
        current_hit = float(current["hit_rate"])
        drop = base_hit - current_hit
        if drop >= hit_drop_threshold:
            alerts.append(
                {
                    "week": str(current["week"]),
                    "baseline_hit_rate": base_hit,
                    "current_hit_rate": current_hit,
                    "hit_rate_drop": drop,
                    "severity": "high" if drop >= 0.35 else "medium",
                }
            )
    return alerts


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly recommendation drift report.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--baseline-weeks", type=int, default=4)
    parser.add_argument("--hit-drop-threshold", type=float, default=0.20)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    rows = load_outcomes_csv(args.dataset)
    weekly = summarize_weekly(rows)
    drift_alerts = detect_drift(
        weekly,
        baseline_weeks=args.baseline_weeks,
        hit_drop_threshold=args.hit_drop_threshold,
    )

    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset": str(args.dataset),
        "baseline_weeks": args.baseline_weeks,
        "hit_drop_threshold": args.hit_drop_threshold,
        "weekly_summary": weekly,
        "drift_alerts": drift_alerts,
    }

    out_path = args.output
    if out_path is None:
        DEFAULT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")
        out_path = DEFAULT_RESULTS_DIR / f"weekly_drift_{stamp}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\nSaved weekly drift report: {out_path}")


if __name__ == "__main__":
    main()
