param(
    [ValidateSet("prepare", "stop-docker")]
    [string]$Action = "prepare",
    [switch]$NoDocker,
    [switch]$NoInstall,
    [switch]$NoSeed
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

. (Join-Path $PSScriptRoot "dev_common.ps1")

function Test-DockerReady {
    try {
        $null = & docker ps 2>&1
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Ensure-DockerReady {
    if (Test-DockerReady) {
        return
    }

    $dockerDesktop = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path -LiteralPath $dockerDesktop)) {
        throw "Docker engine is not running and Docker Desktop was not found at $dockerDesktop."
    }

    Write-Host "Docker engine is not running; starting Docker Desktop..."
    Start-Process -FilePath $dockerDesktop | Out-Null

    $deadline = (Get-Date).AddSeconds(150)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 3
        if (Test-DockerReady) {
            return
        }
    }

    throw "Docker Desktop did not become ready within 150 seconds."
}

Push-Location $Root
try {
    if ($Action -eq "stop-docker") {
        Invoke-Native "docker" @("compose", "stop", "db", "redis")
        exit 0
    }

    $postgresHost = Get-DotEnvValue "POSTGRES_HOST" "localhost"
    $postgresPort = Get-DotEnvValue "POSTGRES_PORT" "5432"

    if ($NoDocker) {
        Write-Host "Skipping Docker startup; expecting PostgreSQL and Redis to be managed separately."
    } else {
        Write-Host "Starting PostgreSQL and Redis..."
        Ensure-DockerReady
        Invoke-Native "docker" @("compose", "up", "-d", "db", "redis")

        if (-not (Wait-Tcp $postgresHost $postgresPort 75)) {
            throw "PostgreSQL did not become reachable at ${postgresHost}:${postgresPort}."
        }
    }

    if (-not (Test-Path -LiteralPath $Python)) {
        Write-Host "Creating Python virtual environment..."
        Invoke-Native "python" @("-m", "venv", ".venv")
    }

    if (-not $NoInstall) {
        Write-Host "Installing Python dependencies..."
        Invoke-Native $Python @("-m", "pip", "install", "-r", "app\requirements.txt")

        Write-Host "Installing root and browser dependencies..."
        Invoke-Native "npm" @("install")
        Invoke-Native "npm" @("--prefix", "surfaces/browser", "install")
    }

    if (-not $NoSeed) {
        Write-Host "Preparing PostgreSQL schema and demo seed data..."
        Invoke-Native $Python @("scripts\setup_database.py", "--require-postgres", "--seed-demo")
    }

    Write-Host "Dev prepare complete. Start apps with: npm run dev"
} finally {
    Pop-Location
}
