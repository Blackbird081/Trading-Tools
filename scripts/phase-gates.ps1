param(
    [ValidateSet("p0", "p1", "phase1", "phase2", "phase3", "phase4", "phase5", "all")]
    [string]$Phase = "all",
    [string]$ApiBase = "http://localhost:8000/api",
    [switch]$StrictWarnings,
    [switch]$AllowProductionTarget
)

$ErrorActionPreference = "Stop"

function Write-Stage([string]$message) {
    Write-Host ""
    Write-Host "== $message ==" -ForegroundColor Cyan
}

function Run-Step([string]$label, [scriptblock]$action) {
    Write-Host "[RUN] $label" -ForegroundColor Yellow
    & $action
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[FAIL] $label" -ForegroundColor Red
        exit 1
    }
    Write-Host "[PASS] $label" -ForegroundColor Green
}

function Run-Pytest([string[]]$testArgs) {
    $args = @("-m", "pytest") + $testArgs
    if ($StrictWarnings) {
        $args += @("-W", "error::RuntimeWarning")
    }
    & python @args
}

function Assert-SafeApiBase() {
    $target = $ApiBase.Trim().ToLowerInvariant()
    $isProdHost = $target -match "trading-tools-production\.up\.railway\.app" -or $target -match "test-trading\.up\.railway\.app"
    if ($isProdHost -and -not $AllowProductionTarget) {
        throw "Refusing to run phase gates against production target '$ApiBase' without -AllowProductionTarget."
    }
}

function Assert-SseComplete([string]$mode, [string]$url, [int]$maxTimeSec = 180) {
    $sse = curl.exe -sS -N --max-time $maxTimeSec $url
    if ($LASTEXITCODE -ne 0) {
        throw "$mode SSE request failed"
    }
    if ($sse -match "event: error") {
        throw "$mode SSE returned error event: $sse"
    }
    if (-not ($sse -match "event: complete")) {
        throw "$mode SSE missing complete event"
    }
}

function Run-P0 {
    Write-Stage "P0 Gate - Loader UX"
    Run-Step "Frontend type-check" { pnpm -C frontend exec tsc --noEmit }
    Run-Step "P0 data-loader regression tests" {
        pnpm -C frontend exec vitest run __tests__/integration/data-loader.test.tsx
    }
}

function Run-P1 {
    Write-Stage "P1 Gate - Persistence and Update Policy"
    Assert-SafeApiBase
    Run-Step "API live health" { curl.exe -sS "$ApiBase/health/live" | Out-Null }
    Run-Step "Load full (VN30, 1Y) reaches complete" {
        Assert-SseComplete "load" "$ApiBase/load-data?preset=VN30&years=1" 180
    }
    Run-Step "Cached data restored after load" {
        $cached = curl.exe -sS "$ApiBase/cached-data?preset=VN30" | ConvertFrom-Json
        if (($cached.symbol_count | ForEach-Object {[int]$_}) -le 0) {
            throw "symbol_count <= 0 after load"
        }
    }
    Run-Step "Update incremental reaches complete" {
        Assert-SseComplete "update" "$ApiBase/update-data?preset=VN30" 120
    }
    Run-Step "Update freshness check" {
        $updates = curl.exe -sS "$ApiBase/check-updates?preset=VN30" | ConvertFrom-Json
        if ($updates.needs_update -eq $true) {
            throw "check-updates still says needs_update=true"
        }
    }
}

function Run-Phase1 {
    Write-Stage "Phase 1 Gate - Foundation and Core Domain"
    $env:PYTHONPATH = "packages/core/src;packages/adapters/src;packages/agents/src;packages/interface/src"
    Run-Step "Core unit tests" {
        Run-Pytest @("tests/unit/test_entities.py", "tests/unit/test_price_band.py", "tests/unit/test_settlement.py", "-q")
    }
}

function Run-Phase2 {
    Write-Stage "Phase 2 Gate - Market Connectivity and Data Pipeline"
    $env:PYTHONPATH = "packages/core/src;packages/adapters/src;packages/agents/src;packages/interface/src"
    Run-Step "DuckDB integration tests" {
        Run-Pytest @("tests/integration/test_duckdb_repo.py", "-q")
    }
    Run-Step "Data pipeline integration tests" {
        Run-Pytest @("tests/integration/test_data_pipeline.py", "-q")
    }
}

function Run-Phase3 {
    Write-Stage "Phase 3 Gate - Intelligence Engine"
    $env:PYTHONPATH = "packages/core/src;packages/adapters/src;packages/agents/src;packages/interface/src"
    Run-Step "Agent pipeline unit tests" {
        Run-Pytest @(
            "tests/unit/test_screener_agent.py",
            "tests/unit/test_technical_agent.py",
            "tests/unit/test_risk_agent.py",
            "tests/unit/test_supervisor_routing.py",
            "-q"
        )
    }
}

function Run-Phase4 {
    Write-Stage "Phase 4 Gate - Frontend and Real-time UI"
    Run-Step "Frontend type-check" { pnpm -C frontend exec tsc --noEmit }
    Run-Step "Frontend integration tests" {
        pnpm -C frontend exec vitest run __tests__/integration/ws-provider.test.ts __tests__/integration/price-board.test.ts __tests__/integration/data-loader.test.tsx __tests__/lib/market-sectors.test.ts
    }
}

function Run-Phase5 {
    Write-Stage "Phase 5 Gate - Execution and Order Flow"
    $env:PYTHONPATH = "packages/core/src;packages/adapters/src;packages/agents/src;packages/interface/src"
    Run-Step "Order execution tests" {
        Run-Pytest @(
            "tests/unit/test_executor_agent.py",
            "tests/unit/test_place_order.py",
            "tests/integration/test_order_sync.py",
            "-q"
        )
    }
}

$strictMsg = if ($StrictWarnings) { "on" } else { "off" }
Write-Host "CVF Phase Gates starting - target: $Phase - strict-warnings: $strictMsg" -ForegroundColor Magenta

switch ($Phase) {
    "p0" { Run-P0 }
    "p1" { Run-P1 }
    "phase1" { Run-Phase1 }
    "phase2" { Run-Phase2 }
    "phase3" { Run-Phase3 }
    "phase4" { Run-Phase4 }
    "phase5" { Run-Phase5 }
    "all" {
        Run-P0
        Run-P1
        Run-Phase1
        Run-Phase2
        Run-Phase3
        Run-Phase4
        Run-Phase5
    }
}

Write-Host ""
Write-Host "All requested CVF phase gates passed." -ForegroundColor Green
