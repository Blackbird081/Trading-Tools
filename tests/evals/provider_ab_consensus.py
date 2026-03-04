"""Provider A/B comparison + consensus validation on fixed outcomes."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

try:
    from tests.evals.reliability_metrics import is_correct_call, normalize_action
except ModuleNotFoundError:  # pragma: no cover - direct script execution fallback
    from reliability_metrics import is_correct_call, normalize_action

DEFAULT_DATASET = Path("tests/evals/data/provider_ab_consensus_fixed.csv")
DEFAULT_RESULTS_DIR = Path("tests/evals/results")


@dataclass(frozen=True)
class ProviderPrediction:
    dt: str
    symbol: str
    provider: str
    recommendation: str
    confidence: float
    realized_return: float


def load_predictions(path: Path) -> list[ProviderPrediction]:
    rows: list[ProviderPrediction] = []
    with path.open(encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(
                ProviderPrediction(
                    dt=row["date"],
                    symbol=row["symbol"].strip().upper(),
                    provider=row["provider"].strip().lower(),
                    recommendation=normalize_action(row["recommendation"]),
                    confidence=float(row.get("confidence", 0.0)),
                    realized_return=float(row["realized_return"]),
                )
            )
    return rows


def _key(item: ProviderPrediction) -> tuple[str, str]:
    return item.dt, item.symbol


def _consensus_action(items: list[ProviderPrediction]) -> str:
    counts = Counter(row.recommendation for row in items)
    if not counts:
        return "HOLD"
    top = counts.most_common()
    if len(top) > 1 and top[0][1] == top[1][1]:
        return "HOLD"
    return top[0][0]


def evaluate_provider_ab(rows: list[ProviderPrediction]) -> dict[str, object]:
    by_key: dict[tuple[str, str], list[ProviderPrediction]] = defaultdict(list)
    for row in rows:
        by_key[_key(row)].append(row)

    agreements = 0
    total_keys = 0
    provider_hits: dict[str, list[bool]] = defaultdict(list)
    consensus_hits: list[bool] = []

    for _, group in by_key.items():
        if len(group) < 2:
            continue
        total_keys += 1
        actions = {row.recommendation for row in group}
        if len(actions) == 1:
            agreements += 1

        # same realized return per (date, symbol) by dataset construction
        realized = group[0].realized_return
        for row in group:
            provider_hits[row.provider].append(is_correct_call(row.recommendation, realized))

        consensus = _consensus_action(group)
        consensus_hits.append(is_correct_call(consensus, realized))

    per_provider_hit_rate = {
        provider: (sum(1 for ok in hits if ok) / len(hits) if hits else 0.0)
        for provider, hits in provider_hits.items()
    }

    return {
        "sample_pairs": total_keys,
        "agreement_rate": (agreements / total_keys) if total_keys else 0.0,
        "provider_hit_rate": per_provider_hit_rate,
        "consensus_hit_rate": (sum(1 for ok in consensus_hits if ok) / len(consensus_hits)) if consensus_hits else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run provider A/B + consensus evaluation.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    rows = load_predictions(args.dataset)
    metrics = evaluate_provider_ab(rows)
    payload = {
        "timestamp": datetime.now(UTC).isoformat(),
        "dataset": str(args.dataset),
        "metrics": metrics,
    }

    out_path = args.output
    if out_path is None:
        DEFAULT_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y-%m-%d-%H%M%S")
        out_path = DEFAULT_RESULTS_DIR / f"provider_ab_consensus_{stamp}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\nSaved A/B consensus report: {out_path}")


if __name__ == "__main__":
    main()
