param(
    [string]$OutputPath = "docs/reports/AI_RELIABILITY_WEEKLY_LATEST.md"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$env:PYTHONPATH = "packages/core/src;packages/adapters/src;packages/agents/src;packages/interface/src;."

Write-Host "[RUN] Reliability pack runner" -ForegroundColor Yellow
python tests/evals/run_reliability_pack.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Reliability pack runner" -ForegroundColor Red
    exit 1
}

$resultsDir = Join-Path $repoRoot "tests/evals/results"
$latest = Get-ChildItem $resultsDir -Filter "reliability_pack_*.json" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $latest) {
    Write-Error "No reliability pack result found under tests/evals/results."
}

$payload = Get-Content $latest.FullName -Raw | ConvertFrom-Json
$alerts = @($payload.weekly_drift.alerts)
$alertCount = $alerts.Count

$lines = @(
    "# AI Reliability Weekly Report (Latest)",
    "",
    "- Generated-At (UTC): $($payload.timestamp)",
    "- Source Artifact: tests/evals/results/$($latest.Name)",
    "- Precision@K: $($payload.benchmark_quant.precision_at_k)",
    "- Hit-rate: $($payload.benchmark_quant.hit_rate)",
    "- MDD: $($payload.benchmark_quant.mdd)",
    "- Provider agreement: $($payload.provider_ab_consensus.agreement_rate)",
    "- Consensus hit-rate: $($payload.provider_ab_consensus.consensus_hit_rate)",
    "- Drift alerts: $alertCount",
    "",
    "## Drift Alerts",
    ""
)

if ($alertCount -eq 0) {
    $lines += "- None"
} else {
    foreach ($alert in $alerts) {
        $lines += "- week=$($alert.week) reason=$($alert.reason)"
    }
}

$outputAbs = Join-Path $repoRoot $OutputPath
$outputDir = Split-Path -Parent $outputAbs
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}
$lines | Set-Content -Path $outputAbs -Encoding UTF8

Write-Host "Weekly reliability report written to: $OutputPath" -ForegroundColor Green
