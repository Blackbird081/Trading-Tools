param(
    [ValidateSet("dev", "local-prod", "docker")]
    [string]$Profile = "dev",
    [ValidateSet("backend", "frontend", "both")]
    [string]$Target = "both"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

function Start-BackendDev {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot'; uv run uvicorn interface.app:app --reload --port 8000"
}

function Start-BackendProd {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot'; uv run uvicorn interface.app:app --host 0.0.0.0 --port 8000"
}

function Start-FrontendDev {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot'; pnpm -C frontend dev"
}

function Start-FrontendProd {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$repoRoot'; pnpm -C frontend build; pnpm -C frontend start"
}

function Start-DockerStack {
    Set-Location $repoRoot
    docker compose up --build
}

switch ($Profile) {
    "docker" {
        Start-DockerStack
        break
    }
    "dev" {
        if ($Target -in @("backend", "both")) { Start-BackendDev }
        if ($Target -in @("frontend", "both")) { Start-FrontendDev }
        break
    }
    "local-prod" {
        if ($Target -in @("backend", "both")) { Start-BackendProd }
        if ($Target -in @("frontend", "both")) { Start-FrontendProd }
        break
    }
}

Write-Host "Profile '$Profile' started for target '$Target'."

