# AI Reliability Weekly Report (Latest)

- Generated-At (UTC): 2026-03-05T03:46:48.289837+00:00
- Source Artifact: tests/evals/results/reliability_pack_2026-03-05-034648.json
- Precision@K: 0.6
- Hit-rate: 0.5
- MDD: 0.1554240955666563
- Provider agreement: 0.4
- Consensus hit-rate: 0.4
- Provider parity spread: 0.2
- Best provider: gemini
- Worst provider: openai
- Drift alerts: 4
- Strict gate: PASS (FailOnDriftSeverity=none)

## Threshold Checks

| Metric | Actual | Comparator | Threshold | Status |
|---|---:|:---:|---:|---|
| Precision@K | 0.6 | >= | 0.55 | PASS |
| Hit-rate | 0.5 | >= | 0.45 | PASS |
| MDD | 0.1554 | <= | 0.25 | PASS |
| Provider agreement | 0.4 | >= | 0.3 | PASS |
| Consensus hit-rate | 0.4 | >= | 0.35 | PASS |

## Drift Alerts


## Provider Parity

| Provider | Sample Size | Hit-rate | Avg Confidence |
|---|---:|---:|---:|
| gemini | 10 | 0.8 | 0.79 |
| openai | 10 | 0.6 | 0.9 |
- week=2026-W06 severity=high hit_drop=1 baseline=1 current=0
- week=2026-W07 severity=high hit_drop=0.75 baseline=0.75 current=0
- week=2026-W08 severity=high hit_drop=0.5 baseline=0.5 current=0
- week=2026-W09 severity=medium hit_drop=0.25 baseline=0.25 current=0
