param(
    [string]$BackupFile = "",
    [string]$TargetPath = "",
    [switch]$UseLatest
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$backupRoot = Join-Path $repoRoot "data/backups"

if ($UseLatest) {
    if (-not (Test-Path $backupRoot)) {
        Write-Error "Backup directory not found: $backupRoot"
        exit 1
    }
    $latest = Get-ChildItem -Path $backupRoot -Filter "*.duckdb" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($null -eq $latest) {
        Write-Error "No backup files found in: $backupRoot"
        exit 1
    }
    $BackupFile = $latest.FullName
}

if (-not $BackupFile) {
    Write-Error "Provide -BackupFile <path> or use -UseLatest."
    exit 1
}

$backupAbs = if ([System.IO.Path]::IsPathRooted($BackupFile)) { $BackupFile } else { Join-Path $repoRoot $BackupFile }
if (-not (Test-Path $backupAbs)) {
    Write-Error "Backup file not found: $backupAbs"
    exit 1
}

if (-not $TargetPath) {
    $TargetPath = $env:DUCKDB_PATH
}
if (-not $TargetPath) {
    $TargetPath = "data/trading.duckdb"
}

$targetAbs = if ([System.IO.Path]::IsPathRooted($TargetPath)) { $TargetPath } else { Join-Path $repoRoot $TargetPath }
$targetDir = Split-Path -Parent $targetAbs
if (-not (Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

if (Test-Path $targetAbs) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $preRestore = "$targetAbs.pre-restore-$stamp.bak"
    Copy-Item -Path $targetAbs -Destination $preRestore -Force
    Write-Host "Previous DB snapshot saved: $preRestore"
}

Copy-Item -Path $backupAbs -Destination $targetAbs -Force

Write-Host "Restore completed:"
Write-Host "  Backup: $backupAbs"
Write-Host "  Target: $targetAbs"
