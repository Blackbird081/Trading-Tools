"""Run quantitative benchmark on a fixed historical dataset.

Metrics:
- Precision@K
- Hit-rate
- Max Drawdown (MDD)
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

try:
    from tests.evals.reliability_metrics import evaluate_quant_benchmark, load_outcomes_csv
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from reliability_metrics import evaluate_quant_benchmark, load_outcomes_csv

DEFAULT_DATASET = Path("tests/evals/data/recommendation_outcomes_fixed.csv")
DEFAULT_RESULTS_DIR = Path("tests/evals/results")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run fixed-dataset quant benchmark.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    rows = load_outcomes_csv(args.dataset)
    metrics = evaluate_quant_benchmark(rows, k=args.k)

    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset": str(args.dataset),
        "top_k": args.k,
        "metrics": metrics,
    }

    out_path = args.output
    if out_path is None:
        DEFAULT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")
        out_path = DEFAULT_RESULTS_DIR / f"quant_benchmark_{stamp}.json"

    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\nSaved benchmark report: {out_path}")


if __name__ == "__main__":
    main()
