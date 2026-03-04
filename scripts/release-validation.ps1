param(
    [string]$OutputPath = "docs/reports/LOCAL_RELEASE_VALIDATION_LATEST.md",
    [ValidateRange(1, 100)]
    [int]$BackendCoverageThreshold = 90,
    [ValidateRange(1, 100)]
    [int]$FrontendCoverageThreshold = 80,
    [ValidateRange(1, 100)]
    [int]$FrontendTargetCoverage = 90
)

$ErrorActionPreference = "Continue"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot
$env:PYTHONPATH = "packages/core/src;packages/adapters/src;packages/agents/src;packages/interface/src"

$rows = New-Object System.Collections.Generic.List[object]

function Add-Result {
    param(
        [string]$Step,
        [string]$Command,
        [int]$ExitCode,
        [double]$Seconds
    )
    $rows.Add([pscustomobject]@{
        Step = $Step
        Command = $Command
        Status = $(if ($ExitCode -eq 0) { "PASS" } else { "FAIL" })
        ExitCode = $ExitCode
        Seconds = [math]::Round($Seconds, 2)
    }) | Out-Null
}

function Run-Step {
    param(
        [string]$Step,
        [string]$Command
    )
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    cmd /c $Command
    $code = $LASTEXITCODE
    $sw.Stop()
    Add-Result -Step $Step -Command $Command -ExitCode $code -Seconds $sw.Elapsed.TotalSeconds
}

Run-Step -Step "Frontend type check" -Command "pnpm -C frontend exec tsc --noEmit"
Run-Step -Step "Pre-live API quality gate" -Command "powershell -ExecutionPolicy Bypass -File scripts/pre-live-api-gate.ps1 -StrictWarnings -WithFrontend -BackendCoverageThreshold $BackendCoverageThreshold"
Run-Step -Step "Weekly reliability pack artifact" -Command "powershell -ExecutionPolicy Bypass -File scripts/run-weekly-reliability-pack.ps1"
Run-Step -Step "Setup API integration" -Command "python -m pytest tests/integration/test_setup_api.py -q"
Run-Step -Step "Local product API integration" -Command "python -m pytest tests/integration/test_local_product_api.py -q"
Run-Step -Step "Backend compile check" -Command "python -m py_compile packages/interface/src/interface/rest/setup.py packages/interface/src/interface/rest/data_loader.py packages/interface/src/interface/rest/orders.py packages/adapters/src/adapters/vnstock/news.py"

$coverageGateStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$frontendCoveragePath = Join-Path $repoRoot "frontend/coverage/coverage-summary.json"
$frontendCoverageCode = 0
$frontendCoveragePct = 0.0
$coverageGateCommand = "frontend lines >= $FrontendCoverageThreshold% (target $FrontendTargetCoverage%) from frontend/coverage/coverage-summary.json"

if (-not (Test-Path $frontendCoveragePath)) {
    $frontendCoverageCode = 1
} else {
    try {
        $coverageJson = Get-Content $frontendCoveragePath -Raw | ConvertFrom-Json
        $frontendCoveragePct = [double]$coverageJson.total.lines.pct
        if ($frontendCoveragePct -lt $FrontendCoverageThreshold) {
            $frontendCoverageCode = 1
        }
    } catch {
        $frontendCoverageCode = 1
    }
}

$coverageGateStopwatch.Stop()
Add-Result -Step "Frontend coverage gate" -Command "$coverageGateCommand (actual: $([math]::Round($frontendCoveragePct, 2))%)" -ExitCode $frontendCoverageCode -Seconds $coverageGateStopwatch.Elapsed.TotalSeconds

if ($frontendCoverageCode -eq 0 -and $frontendCoveragePct -lt $FrontendTargetCoverage) {
    Write-Host "Frontend coverage $([math]::Round($frontendCoveragePct, 2))% meets release minimum $FrontendCoverageThreshold% but is below target $FrontendTargetCoverage%." -ForegroundColor Yellow
}

$failCount = ($rows | Where-Object { $_.Status -eq "FAIL" }).Count
$overall = if ($failCount -eq 0) { "PASS" } else { "FAIL" }
$generatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

$lines = @(
    "# Local Release Validation (Latest)",
    "",
    "- Generated-At (local): $generatedAt",
    "- Overall: $overall",
    "",
    "| Step | Status | Exit Code | Seconds | Command |",
    "|---|---|---:|---:|---|"
)

foreach ($row in $rows) {
    $safeCommand = ($row.Command -replace "\|", "/")
    $lines += "| $($row.Step) | $($row.Status) | $($row.ExitCode) | $($row.Seconds) | $safeCommand |"
}

$outputAbs = Join-Path $repoRoot $OutputPath
$outputDir = Split-Path -Parent $outputAbs
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}
$lines | Set-Content -Path $outputAbs -Encoding UTF8

Write-Host "Release validation report written to: $OutputPath"
Write-Host "Overall: $overall"

if ($overall -eq "FAIL") {
    exit 1
}
