param(
    [string]$OutputPath = "docs/reports/AI_RELIABILITY_WEEKLY_LATEST.md",
    [ValidateRange(0, 1)]
    [double]$MinPrecisionAtK = 0.0,
    [ValidateRange(0, 1)]
    [double]$MinHitRate = 0.0,
    [ValidateRange(0, 1)]
    [double]$MinConsensusHitRate = 0.0,
    [ValidateRange(0, 1)]
    [double]$MinAgreementRate = 0.0,
    [ValidateRange(0, 10)]
    [double]$MaxDrawdown = 1.0,
    [ValidateSet("none", "medium", "high")]
    [string]$FailOnDriftSeverity = "none"
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
$benchmark = $payload.benchmark_quant
$consensus = $payload.provider_ab_consensus
$parity = $payload.provider_parity
$alerts = @($payload.weekly_drift.alerts)
$alertCount = $alerts.Count

function Get-SeverityRank([string]$severity) {
    switch ($severity.ToLowerInvariant()) {
        "high" { return 2 }
        "medium" { return 1 }
        default { return 0 }
    }
}

$thresholdRows = @(
    [pscustomobject]@{
        Metric = "Precision@K"
        Actual = [double]$benchmark.precision_at_k
        Threshold = $MinPrecisionAtK
        Comparator = ">="
        Pass = ([double]$benchmark.precision_at_k -ge $MinPrecisionAtK)
    },
    [pscustomobject]@{
        Metric = "Hit-rate"
        Actual = [double]$benchmark.hit_rate
        Threshold = $MinHitRate
        Comparator = ">="
        Pass = ([double]$benchmark.hit_rate -ge $MinHitRate)
    },
    [pscustomobject]@{
        Metric = "MDD"
        Actual = [double]$benchmark.max_drawdown
        Threshold = $MaxDrawdown
        Comparator = "<="
        Pass = ([double]$benchmark.max_drawdown -le $MaxDrawdown)
    },
    [pscustomobject]@{
        Metric = "Provider agreement"
        Actual = [double]$consensus.agreement_rate
        Threshold = $MinAgreementRate
        Comparator = ">="
        Pass = ([double]$consensus.agreement_rate -ge $MinAgreementRate)
    },
    [pscustomobject]@{
        Metric = "Consensus hit-rate"
        Actual = [double]$consensus.consensus_hit_rate
        Threshold = $MinConsensusHitRate
        Comparator = ">="
        Pass = ([double]$consensus.consensus_hit_rate -ge $MinConsensusHitRate)
    }
)

$driftThresholdRank = Get-SeverityRank $FailOnDriftSeverity
$driftViolations = if ($driftThresholdRank -eq 0) {
    @()
} else {
    @($alerts | Where-Object { (Get-SeverityRank $_.severity) -ge $driftThresholdRank })
}

$failedMetricCount = @($thresholdRows | Where-Object { -not $_.Pass }).Count
$strictFailures = $failedMetricCount + $driftViolations.Count
$strictStatus = if ($strictFailures -eq 0) { "PASS" } else { "FAIL" }

$lines = @(
    "# AI Reliability Weekly Report (Latest)",
    "",
    "- Generated-At (UTC): $($payload.timestamp)",
    "- Source Artifact: tests/evals/results/$($latest.Name)",
    "- Precision@K: $($benchmark.precision_at_k)",
    "- Hit-rate: $($benchmark.hit_rate)",
    "- MDD: $($benchmark.max_drawdown)",
    "- Provider agreement: $($consensus.agreement_rate)",
    "- Consensus hit-rate: $($consensus.consensus_hit_rate)",
    "- Provider parity spread: $([math]::Round([double]$parity.parity_spread, 4))",
    "- Best provider: $($parity.best_provider)",
    "- Worst provider: $($parity.worst_provider)",
    "- Drift alerts: $alertCount",
    "- Strict gate: $strictStatus (FailOnDriftSeverity=$FailOnDriftSeverity)",
    "",
    "## Threshold Checks",
    "",
    "| Metric | Actual | Comparator | Threshold | Status |",
    "|---|---:|:---:|---:|---|"
)

foreach ($row in $thresholdRows) {
    $status = if ($row.Pass) { "PASS" } else { "FAIL" }
    $lines += "| $($row.Metric) | $([math]::Round([double]$row.Actual, 4)) | $($row.Comparator) | $([math]::Round([double]$row.Threshold, 4)) | $status |"
}

$lines += @(
    "",
    "## Drift Alerts",
    ""
)

$lines += @(
    "",
    "## Provider Parity",
    "",
    "| Provider | Sample Size | Hit-rate | Avg Confidence |",
    "|---|---:|---:|---:|"
)

foreach ($providerRow in @($parity.providers)) {
    $lines += "| $($providerRow.provider) | $($providerRow.sample_size) | $([math]::Round([double]$providerRow.hit_rate, 4)) | $([math]::Round([double]$providerRow.avg_confidence, 4)) |"
}

if ($alertCount -eq 0) {
    $lines += "- None"
} else {
    foreach ($alert in $alerts) {
        $lines += "- week=$($alert.week) severity=$($alert.severity) hit_drop=$([math]::Round([double]$alert.hit_rate_drop, 4)) baseline=$([math]::Round([double]$alert.baseline_hit_rate, 4)) current=$([math]::Round([double]$alert.current_hit_rate, 4))"
    }
}

$outputAbs = Join-Path $repoRoot $OutputPath
$outputDir = Split-Path -Parent $outputAbs
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}
$lines | Set-Content -Path $outputAbs -Encoding UTF8

Write-Host "Weekly reliability report written to: $OutputPath" -ForegroundColor Green

if ($strictFailures -gt 0) {
    if ($failedMetricCount -gt 0) {
        Write-Host "[FAIL] Reliability metric threshold check failed." -ForegroundColor Red
    }
    if ($driftViolations.Count -gt 0) {
        Write-Host "[FAIL] Drift alert severity gate failed ($($driftViolations.Count) violation(s))." -ForegroundColor Red
    }
    exit 1
}
