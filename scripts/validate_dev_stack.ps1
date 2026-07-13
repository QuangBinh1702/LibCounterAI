param(
    [switch]$NoInstall
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$DevScript = Join-Path $PSScriptRoot "dev.ps1"

. (Join-Path $PSScriptRoot "dev_common.ps1")

$backendPort = Get-DotEnvValue "BACKEND_PORT" "8000"
$frontendPort = Get-DotEnvValue "FRONTEND_PORT" "5173"
$backendUrl = "http://localhost:$backendPort"
$frontendUrl = "http://localhost:$frontendPort"

Push-Location $Root
$devProcess = $null
try {
    if ($NoInstall) {
        & $DevScript prepare -NoInstall
    } else {
        & $DevScript prepare
    }

    $npmCmd = if (Get-Command npm.cmd -ErrorAction SilentlyContinue) { "npm.cmd" } else { "npm" }
    $devProcess = Start-Process `
        -FilePath $npmCmd `
        -ArgumentList @("run", "dev") `
        -WorkingDirectory $Root `
        -WindowStyle Hidden `
        -PassThru

    if (-not (Wait-Http "$backendUrl/api/health" 90)) {
        throw "Backend did not become healthy at $backendUrl/api/health."
    }
    if (-not (Wait-Http $frontendUrl 90)) {
        throw "Frontend did not become reachable at $frontendUrl."
    }

    $health = Invoke-RestMethod -Uri "$backendUrl/api/health" -TimeoutSec 10
    if ($health.status -ne "healthy") {
        throw "Backend health check returned '$($health.status)'."
    }

    $today = (Get-Date).ToString('yyyy-MM-dd')
    $sessions = Invoke-RestMethod -Uri "$backendUrl/api/sessions?date=$today" -TimeoutSec 10
    $items = if ($sessions.items) { $sessions.items } else { $sessions }
    if (-not $items -or $items.Count -lt 1) {
        throw "Demo sessions endpoint did not return seeded rows for $today."
    }

    $frontend = Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 10
    if ($frontend.StatusCode -lt 200 -or $frontend.StatusCode -ge 500) {
        throw "Frontend returned HTTP $($frontend.StatusCode)."
    }

    Write-Host "Dev stack validation passed."
    Write-Host "Backend:  $backendUrl"
    Write-Host "Frontend: $frontendUrl"
    Write-Host "Sessions: $($items.Count)"
} finally {
    if ($devProcess -and -not $devProcess.HasExited) {
        Stop-Process -Id $devProcess.Id -Force -ErrorAction SilentlyContinue
        Get-CimInstance Win32_Process |
            Where-Object { $_.ParentProcessId -eq $devProcess.Id } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    }

    $backendPid = Get-ListeningPid $backendPort
    if ($backendPid) {
        Stop-Process -Id $backendPid -Force -ErrorAction SilentlyContinue
    }
    $frontendPid = Get-ListeningPid $frontendPort
    if ($frontendPid) {
        Stop-Process -Id $frontendPid -Force -ErrorAction SilentlyContinue
    }

    Pop-Location
}
