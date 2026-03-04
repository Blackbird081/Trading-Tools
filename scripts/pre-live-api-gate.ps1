param(
    [switch]$StrictWarnings,
    [switch]$WithFrontend,
    [ValidateRange(1, 100)]
    [int]$BackendCoverageThreshold = 90
)

$ErrorActionPreference = "Stop"

function Run-Step([string]$label, [scriptblock]$action) {
    Write-Host "[RUN] $label" -ForegroundColor Yellow
    & $action
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] $label" -ForegroundColor Red
        exit 1
    }
    Write-Host "[PASS] $label" -ForegroundColor Green
}

$env:PYTHONPATH = "packages/core/src;packages/adapters/src;packages/agents/src;packages/interface/src"

$pytestArgs = @(
    "-m", "pytest",
    "tests/integration/test_setup_profiles_api.py",
    "tests/integration/test_data_loader_api.py",
    "tests/unit/test_data_loader_helpers.py",
    "tests/unit/test_vnstock_news_adapter.py",
    "tests/unit/test_profile_vault.py",
    "--cov=interface.profile_vault",
    "--cov=interface.rest.data_loader",
    "--cov=adapters.vnstock.news",
    "--cov-fail-under=$BackendCoverageThreshold",
    "--cov-report=term",
    "-q"
)

if ($StrictWarnings) {
    $pytestArgs += @("-W", "error::RuntimeWarning")
}

Write-Host "Pre-live API quality gate starting (critical backend coverage >= $BackendCoverageThreshold%)" -ForegroundColor Magenta
Run-Step "Critical backend coverage gate" { python @pytestArgs }
Run-Step "Order safety integration regression" { python -m pytest tests/integration/test_order_safety_controls.py -q }

if ($WithFrontend) {
    Run-Step "Frontend regression coverage snapshot" {
        pnpm -C frontend exec vitest run `
            __tests__/integration/data-loader.test.tsx `
            __tests__/stores/market-store.test.ts `
            __tests__/stores/signal-store.test.ts `
            __tests__/lib/market-sectors.test.ts `
            --coverage `
            --coverage.include="app/(dashboard)/_components/data-loader.tsx" `
            --coverage.include="stores/market-store.ts" `
            --coverage.include="stores/signal-store.ts" `
            --coverage.include="lib/market-sectors.ts" `
            --coverage.reporter=text-summary `
            --coverage.reporter=json-summary `
            --coverage.reportsDirectory=coverage
    }
}

Write-Host ""
Write-Host "Pre-live API quality gate passed." -ForegroundColor Green
