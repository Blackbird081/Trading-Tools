from __future__ import annotations

from pathlib import Path

from tests.evals.provider_ab_consensus import evaluate_provider_ab, load_predictions
from tests.evals.provider_parity_calibration import evaluate_provider_parity
from tests.evals.reliability_metrics import evaluate_quant_benchmark, load_outcomes_csv
from tests.evals.weekly_drift_monitor import detect_drift, summarize_weekly


OUTCOMES_DATASET = Path("tests/evals/data/recommendation_outcomes_fixed.csv")
AB_DATASET = Path("tests/evals/data/provider_ab_consensus_fixed.csv")


def test_quant_benchmark_metrics_from_fixed_dataset() -> None:
    rows = load_outcomes_csv(OUTCOMES_DATASET)
    metrics = evaluate_quant_benchmark(rows, k=10)
    assert metrics["sample_size"] == 24.0
    assert 0.0 <= metrics["precision_at_k"] <= 1.0
    assert 0.0 <= metrics["hit_rate"] <= 1.0
    assert metrics["max_drawdown"] >= 0.0


def test_provider_ab_consensus_metrics() -> None:
    rows = load_predictions(AB_DATASET)
    metrics = evaluate_provider_ab(rows)
    assert metrics["sample_pairs"] == 10
    assert 0.0 <= float(metrics["agreement_rate"]) <= 1.0
    assert 0.0 <= float(metrics["consensus_hit_rate"]) <= 1.0
    provider_rates = metrics["provider_hit_rate"]
    assert isinstance(provider_rates, dict)
    assert "openai" in provider_rates
    assert "gemini" in provider_rates

    parity = evaluate_provider_parity(rows)
    assert isinstance(parity["providers"], list)
    assert parity["best_provider"] is not None
    assert 0.0 <= float(parity["parity_spread"]) <= 1.0


def test_weekly_drift_detection_reports_alerts() -> None:
    rows = load_outcomes_csv(OUTCOMES_DATASET)
    weekly = summarize_weekly(rows, k=3)
    alerts = detect_drift(weekly, baseline_weeks=4, hit_drop_threshold=0.20)
    assert len(weekly) == 8
    assert len(alerts) >= 1
