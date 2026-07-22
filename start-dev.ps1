# Local development startup script.
# Runs the FastAPI backend on 127.0.0.1 with reload enabled.

param(
    [string]$HostName = "",
    [int]$Port = 0,
    [switch]$SkipInstall,
    [switch]$SkipDbInit
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$BackendDir = Join-Path $Root "apps\backend"
$BackendSrc = Join-Path $BackendDir "src"
$EnvFile = Join-Path $Root ".env"
$EnvExample = Join-Path $Root ".env.example"
$Python = $null

function Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Ok($msg) { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "[ERR ] $msg" -ForegroundColor Red }

function Read-DotEnv($path) {
    $values = @{}
    if (-not (Test-Path $path)) {
        return $values
    }
    Get-Content $path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $parts = $line.Split("=", 2)
        $values[$parts[0].Trim()] = $parts[1].Trim()
    }
    return $values
}

function Set-EnvFromFile($path) {
    $values = Read-DotEnv $path
    foreach ($key in $values.Keys) {
        if (-not [Environment]::GetEnvironmentVariable($key, "Process")) {
            [Environment]::SetEnvironmentVariable($key, $values[$key], "Process")
        }
    }
}

Write-Host ""
Write-Host "=========================================="
Write-Host " Project4 local dev startup"
Write-Host "=========================================="
Write-Host ""

if (-not (Test-Path $EnvFile)) {
    if (Test-Path $EnvExample) {
        Copy-Item $EnvExample $EnvFile
        Ok "Created .env from .env.example"
    } else {
        Fail ".env and .env.example are both missing."
        exit 1
    }
}

Set-EnvFromFile $EnvFile
$envValues = Read-DotEnv $EnvFile

if (-not $HostName) {
    $HostName = $envValues["BACKEND_HOST"]
    if (-not $HostName) { $HostName = "127.0.0.1" }
}
if (-not $Port) {
    $portValue = $envValues["BACKEND_PORT"]
    if ($portValue) { $Port = [int]$portValue } else { $Port = 8000 }
}

$LocalPython = Join-Path $Root ".venv\Scripts\python.exe"
$LegacyCondaPython = Join-Path $Root ".conda\python.exe"
if (Test-Path $LocalPython) {
    $Python = $LocalPython
    Ok "Using .venv Python: $Python"
} elseif (Test-Path $LegacyCondaPython) {
    $Python = $LegacyCondaPython
    Ok "Using .conda Python: $Python"
} else {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Fail "Python not found. Install Python 3.11 or activate your venv first."
        exit 1
    }
    $Python = $cmd.Source
    Ok "Using system Python: $Python"
}

$version = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
Info "Python version: $version"
$majorMinor = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
if ($majorMinor -ne "3.11") {
    Warn "Recommended Python version is 3.11. Current: $version"
}

if (-not $SkipInstall) {
    $depsOk = & $Python -c "import fastapi, uvicorn, pymysql; print('ok')" 2>$null
    if ($depsOk -ne "ok") {
        Info "Installing backend dependencies..."
        & $Python -m pip install -r (Join-Path $BackendDir "requirements.txt")
        if ($LASTEXITCODE -ne 0) {
            Fail "Dependency installation failed."
            exit 1
        }
    }
    Ok "Backend dependencies are available."
}

Info "Checking MySQL and schema..."
& $Python (Join-Path $Root "tools\dev\create_database.py") --dry-run
if ($LASTEXITCODE -ne 0) {
    Fail "Unable to read MySQL configuration. Check .env."
    exit 1
}

if (-not $SkipDbInit) {
    & $Python (Join-Path $Root "tools\dev\create_database.py")
    if ($LASTEXITCODE -ne 0) {
        Fail "Database initialization failed."
        Write-Host ""
        Write-Host "Common causes:"
        Write-Host "  - MySQL service is not running"
        Write-Host "  - MYSQL_USER / MYSQL_PASSWORD in .env is wrong"
        Write-Host "  - The user cannot create databases or tables"
        exit 1
    }
    Ok "Database is ready."
}

$defaultUser = $env:ADMIN_USERNAME
if (-not $defaultUser) { $defaultUser = "admin" }
$defaultPassword = $env:ADMIN_PASSWORD
if (-not $defaultPassword) { $defaultPassword = "admin123" }

Write-Host ""
Ok "Backend address: http://${HostName}:$Port"
Info "Default local account: $defaultUser / $defaultPassword"
Info "Health check: http://${HostName}:$Port/api/health"
Info "Press Ctrl+C to stop."
Write-Host ""

Set-Location $Root
& $Python -m uvicorn ugv_backend.main:app --app-dir $BackendSrc --host $HostName --port $Port --reload
