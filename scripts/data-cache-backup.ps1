param(
    [string]$SourcePath = "",
    [string]$BackupDir = "data/backups",
    [string]$Tag = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not $SourcePath) {
    $SourcePath = $env:DUCKDB_PATH
}
if (-not $SourcePath) {
    $SourcePath = "data/trading.duckdb"
}

$sourceAbs = if ([System.IO.Path]::IsPathRooted($SourcePath)) { $SourcePath } else { Join-Path $repoRoot $SourcePath }
if (-not (Test-Path $sourceAbs)) {
    Write-Error "DuckDB source not found: $sourceAbs"
    exit 1
}

$backupAbs = if ([System.IO.Path]::IsPathRooted($BackupDir)) { $BackupDir } else { Join-Path $repoRoot $BackupDir }
if (-not (Test-Path $backupAbs)) {
    New-Item -ItemType Directory -Path $backupAbs -Force | Out-Null
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$safeTag = ($Tag -replace "[^a-zA-Z0-9_-]", "").Trim()
$name = if ($safeTag) { "trading-cache-$stamp-$safeTag.duckdb" } else { "trading-cache-$stamp.duckdb" }
$dest = Join-Path $backupAbs $name

Copy-Item -Path $sourceAbs -Destination $dest -Force

Write-Host "Backup created:"
Write-Host "  Source: $sourceAbs"
Write-Host "  Backup: $dest"
