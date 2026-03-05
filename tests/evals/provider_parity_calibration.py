"""Provider parity calibration on rolling/fixed datasets."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from tests.evals.provider_ab_consensus import ProviderPrediction
from tests.evals.reliability_metrics import is_correct_call


def evaluate_provider_parity(rows: list[ProviderPrediction]) -> dict[str, Any]:
    """Aggregate provider quality spread for calibration decisions.

    This computes:
    - per-provider hit-rate and avg confidence
    - parity spread (best hit-rate - worst hit-rate)
    - recommended primary provider (highest hit-rate, then confidence)
    """
    hits: dict[str, list[bool]] = defaultdict(list)
    confidences: dict[str, list[float]] = defaultdict(list)

    for row in rows:
        hits[row.provider].append(is_correct_call(row.recommendation, row.realized_return))
        confidences[row.provider].append(float(row.confidence))

    provider_rows: list[dict[str, Any]] = []
    for provider in sorted(hits.keys()):
        provider_hits = hits[provider]
        provider_conf = confidences[provider]
        hit_rate = (sum(1 for ok in provider_hits if ok) / len(provider_hits)) if provider_hits else 0.0
        avg_conf = (sum(provider_conf) / len(provider_conf)) if provider_conf else 0.0
        provider_rows.append(
            {
                "provider": provider,
                "sample_size": len(provider_hits),
                "hit_rate": hit_rate,
                "avg_confidence": avg_conf,
            }
        )

    if not provider_rows:
        return {
            "providers": [],
            "best_provider": None,
            "worst_provider": None,
            "parity_spread": 0.0,
        }

    ranked = sorted(provider_rows, key=lambda item: (float(item["hit_rate"]), float(item["avg_confidence"])), reverse=True)
    best = ranked[0]
    worst = ranked[-1]
    return {
        "providers": ranked,
        "best_provider": best["provider"],
        "worst_provider": worst["provider"],
        "parity_spread": max(0.0, float(best["hit_rate"]) - float(worst["hit_rate"])),
    }

