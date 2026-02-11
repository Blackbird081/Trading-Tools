# CI Pipeline Script (PowerShell)
# Ref: 06_Development_Standards_Rules.md §10
# Runs all quality gates sequentially. Any failure stops the pipeline.

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CI PIPELINE — Enterprise Algo-Trading" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── Stage 1: Lint + Format Check ──────────────────────────────
Write-Host "[Stage 1/4] Lint + Format Check" -ForegroundColor Yellow
uv run ruff check packages/ tests/
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: ruff check" -ForegroundColor Red; exit 1 }
uv run ruff format --check packages/ tests/
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: ruff format" -ForegroundColor Red; exit 1 }
Write-Host "[Stage 1/4] PASSED" -ForegroundColor Green
Write-Host ""

# ── Stage 2: Type Check ──────────────────────────────────────
Write-Host "[Stage 2/4] Type Check (mypy --strict)" -ForegroundColor Yellow
uv run mypy packages/ --strict
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: mypy" -ForegroundColor Red; exit 1 }
Write-Host "[Stage 2/4] PASSED" -ForegroundColor Green
Write-Host ""

# ── Stage 3: Unit Tests ──────────────────────────────────────
Write-Host "[Stage 3/4] Unit Tests" -ForegroundColor Yellow
uv run pytest tests/unit/ -v --tb=short -x
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: unit tests" -ForegroundColor Red; exit 1 }
Write-Host "[Stage 3/4] PASSED" -ForegroundColor Green
Write-Host ""

# ── Stage 4: Integration Tests + Coverage ─────────────────────
Write-Host "[Stage 4/4] Integration Tests + Coverage" -ForegroundColor Yellow
uv run pytest tests/ --cov=packages --cov-report=term-missing --tb=short
if ($LASTEXITCODE -ne 0) { Write-Host "FAILED: integration tests / coverage" -ForegroundColor Red; exit 1 }
Write-Host "[Stage 4/4] PASSED" -ForegroundColor Green
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "  ALL STAGES PASSED" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
