param(
    [string]$ApiBase = "http://localhost:8000/api",
    [string]$DuckDbPath = "data/trading.duckdb",
    [switch]$IncludeInstall,
    [string]$OutputPath = "docs/reports/LOCAL_ONBOARDING_BENCHMARK_LATEST.md"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$results = New-Object System.Collections.Generic.List[object]

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $status = "PASS"
    $detail = "ok"
    try {
        & $Action
    } catch {
        $status = "FAIL"
        $detail = $_.Exception.Message
    } finally {
        $sw.Stop()
    }

    $results.Add([pscustomobject]@{
        Step = $Name
        Status = $status
        Seconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        Detail = $detail
    }) | Out-Null
}

if ($IncludeInstall) {
    Invoke-Step -Name "Install backend deps (uv sync)" -Action { uv sync | Out-Null }
    Invoke-Step -Name "Install frontend deps (pnpm install)" -Action { pnpm -C frontend install | Out-Null }
}

Invoke-Step -Name "API health" -Action { Invoke-RestMethod -Uri "$ApiBase/health" -Method Get | Out-Null }
Invoke-Step -Name "Setup status" -Action { Invoke-RestMethod -Uri "$ApiBase/setup/status" -Method Get | Out-Null }
Invoke-Step -Name "Setup validate draft" -Action {
    $payload = @{
        trading_mode = "dry-run"
        duckdb_path = $DuckDbPath
        vnstock_api_key = "benchmark_vnstock_key_12345"
        ssi_consumer_id = "benchmark_consumer"
        ssi_consumer_secret = "benchmark_secret_123"
        ssi_account_no = "12345678"
        ssi_private_key_b64 = "dGVzdA=="
        ai_model_path = "data/models/phi-3-mini-int4"
    } | ConvertTo-Json
    Invoke-RestMethod -Uri "$ApiBase/setup/validate" -Method Post -ContentType "application/json" -Body $payload | Out-Null
}
Invoke-Step -Name "Init local DB path" -Action {
    $payload = @{ duckdb_path = $DuckDbPath } | ConvertTo-Json
    Invoke-RestMethod -Uri "$ApiBase/setup/init-local" -Method Post -ContentType "application/json" -Body $payload | Out-Null
}
Invoke-Step -Name "Probe external connections" -Action {
    $payload = @{ timeout_seconds = 3.0 } | ConvertTo-Json
    Invoke-RestMethod -Uri "$ApiBase/setup/probe-external" -Method Post -ContentType "application/json" -Body $payload | Out-Null
}

$totalSeconds = [math]::Round((($results | Measure-Object -Property Seconds -Sum).Sum), 2)
$totalMinutes = [math]::Round($totalSeconds / 60, 2)
$allPassed = ($results | Where-Object { $_.Status -eq "FAIL" }).Count -eq 0
$withinTarget = $totalSeconds -le 900
$timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# Local Onboarding Benchmark (Latest)") | Out-Null
$lines.Add("") | Out-Null
$lines.Add("- Generated-At (local): $timestamp") | Out-Null
$lines.Add("- API Base: `$ApiBase`") | Out-Null
$lines.Add("- IncludeInstall: $IncludeInstall") | Out-Null
$lines.Add("- Total Time: $totalMinutes minutes ($totalSeconds seconds)") | Out-Null
$lines.Add("- Result: " + ($(if ($allPassed -and $withinTarget) { "PASS" } else { "FAIL" }))) | Out-Null
$lines.Add("- Target (<= 15 min): " + ($(if ($withinTarget) { "met" } else { "not met" }))) | Out-Null
$lines.Add("") | Out-Null
$lines.Add("| Step | Status | Seconds | Detail |") | Out-Null
$lines.Add("|---|---|---:|---|") | Out-Null
foreach ($row in $results) {
    $safeDetail = ($row.Detail -replace "\|", "/")
    $lines.Add("| $($row.Step) | $($row.Status) | $($row.Seconds) | $safeDetail |") | Out-Null
}

$outputAbs = Join-Path $repoRoot $OutputPath
$outputDir = Split-Path -Parent $outputAbs
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}
$lines | Set-Content -Path $outputAbs -Encoding UTF8

Write-Host "Benchmark written to: $OutputPath"
Write-Host "Total: $totalMinutes min | AllPassed=$allPassed | Target<=15m=$withinTarget"
