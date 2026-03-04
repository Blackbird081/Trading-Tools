param(
    [string]$ApiBase = "http://localhost:8000/api",
    [string]$OutputPath = "docs/reports/LOCAL_EMERGENCY_DRILL_LATEST.md"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

$rows = New-Object System.Collections.Generic.List[object]

function Add-Row {
    param(
        [string]$Step,
        [string]$Status,
        [string]$Detail
    )
    $rows.Add([pscustomobject]@{ Step = $Step; Status = $Status; Detail = $Detail }) | Out-Null
}

function Invoke-JsonPost {
    param(
        [string]$Url,
        [object]$Payload
    )
    $body = $Payload | ConvertTo-Json -Depth 8
    return Invoke-RestMethod -Method Post -Uri $Url -ContentType "application/json" -Body $body
}

try {
    Invoke-JsonPost -Url "$ApiBase/safety/kill-switch" -Payload @{ active = $true; reason = "drill" } | Out-Null
    Add-Row -Step "Enable kill switch" -Status "PASS" -Detail "Kill switch enabled."

    try {
        Invoke-JsonPost -Url "$ApiBase/orders" -Payload @{
            symbol = "FPT"; side = "BUY"; order_type = "LO"; quantity = 100; price = 95.0;
            idempotency_key = "drill-kill-switch-1"; mode = "live"
        } | Out-Null
        Add-Row -Step "Live order blocked by kill switch" -Status "FAIL" -Detail "Expected block but order API returned success."
    } catch {
        Add-Row -Step "Live order blocked by kill switch" -Status "PASS" -Detail $_.Exception.Message
    }

    Invoke-JsonPost -Url "$ApiBase/safety/kill-switch" -Payload @{ active = $false; reason = "drill complete" } | Out-Null
    Add-Row -Step "Disable kill switch" -Status "PASS" -Detail "Kill switch disabled."

    $first = Invoke-JsonPost -Url "$ApiBase/orders" -Payload @{
        symbol = "FPT"; side = "BUY"; order_type = "LO"; quantity = 100; price = 95.0;
        idempotency_key = "drill-live-dlq-1"; mode = "live"
    }
    if (-not $first.confirm_token) {
        Add-Row -Step "Live two-step confirm challenge" -Status "FAIL" -Detail "No confirm_token returned."
    } else {
        Add-Row -Step "Live two-step confirm challenge" -Status "PASS" -Detail "confirm_token issued."
    }

    if ($first.confirm_token) {
        $second = Invoke-JsonPost -Url "$ApiBase/orders" -Payload @{
            symbol = "FPT"; side = "BUY"; order_type = "LO"; quantity = 100; price = 95.0;
            idempotency_key = "drill-live-dlq-1"; mode = "live"; confirm_token = $first.confirm_token
        }
        if ($second.status -eq "BROKER_REJECTED" -and $second.dlq_id) {
            Add-Row -Step "Emergency fallback to DLQ" -Status "PASS" -Detail "Order routed to DLQ (broker disabled)."
        } else {
            Add-Row -Step "Emergency fallback to DLQ" -Status "FAIL" -Detail "Expected BROKER_REJECTED + dlq_id."
        }
    }

    $dlq = Invoke-RestMethod -Method Get -Uri "$ApiBase/orders/dlq"
    if ($dlq.count -ge 1) {
        Add-Row -Step "DLQ visibility check" -Status "PASS" -Detail "DLQ contains failed order entries."
    } else {
        Add-Row -Step "DLQ visibility check" -Status "FAIL" -Detail "DLQ is empty."
    }
} catch {
    Add-Row -Step "Drill runner" -Status "FAIL" -Detail $_.Exception.Message
}

$hasFail = ($rows | Where-Object { $_.Status -eq "FAIL" }).Count -gt 0
$result = if ($hasFail) { "FAIL" } else { "PASS" }
$generatedAt = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

$lines = @(
    "# Local Emergency Fallback Drill (Latest)",
    "",
    "- Generated-At (local): $generatedAt",
    "- API Base: $ApiBase",
    "- Result: $result",
    "",
    "| Step | Status | Detail |",
    "|---|---|---|"
)

foreach ($r in $rows) {
    $detail = ($r.Detail -replace "\|", "/")
    $lines += "| $($r.Step) | $($r.Status) | $detail |"
}

$outputAbs = Join-Path $repoRoot $OutputPath
$outputDir = Split-Path -Parent $outputAbs
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}
$lines | Set-Content -Path $outputAbs -Encoding UTF8

Write-Host "Drill report written to: $OutputPath"
Write-Host "Result: $result"
