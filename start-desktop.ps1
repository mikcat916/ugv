# Local desktop startup helper.

param(
    [string]$BackendUrl = ""
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$DesktopDir = Join-Path $Root "desktop"
$EnvFile = Join-Path $Root ".env"

function Info($msg) { Write-Host "[INFO] $msg" -ForegroundColor Cyan }
function Ok($msg) { Write-Host "[ OK ] $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "[ERR ] $msg" -ForegroundColor Red }

function Read-DotEnv($path) {
    $values = @{}
    if (-not (Test-Path $path)) { return $values }
    Get-Content $path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
        $parts = $line.Split("=", 2)
        $values[$parts[0].Trim()] = $parts[1].Trim()
    }
    return $values
}

if (Test-Path $EnvFile) {
    $envValues = Read-DotEnv $EnvFile
    foreach ($key in $envValues.Keys) {
        if (-not [Environment]::GetEnvironmentVariable($key, "Process")) {
            [Environment]::SetEnvironmentVariable($key, $envValues[$key], "Process")
        }
    }
}

if (-not $BackendUrl) {
    $BackendUrl = [Environment]::GetEnvironmentVariable("UGV_BACKEND_URL", "Process")
}
if (-not $BackendUrl) {
    $BackendUrl = [Environment]::GetEnvironmentVariable("BACKEND_URL", "Process")
}
if (-not $BackendUrl) {
    $hostValue = [Environment]::GetEnvironmentVariable("BACKEND_HOST", "Process")
    if (-not $hostValue) { $hostValue = "127.0.0.1" }
    $portValue = [Environment]::GetEnvironmentVariable("BACKEND_PORT", "Process")
    if (-not $portValue) { $portValue = "8000" }
    $BackendUrl = "http://${hostValue}:$portValue"
}
[Environment]::SetEnvironmentVariable("UGV_BACKEND_URL", $BackendUrl.TrimEnd("/"), "Process")

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Fail "Python not found. Activate the desktop environment first."
    exit 1
}
$Python = $pythonCmd.Source
Ok "Using Python: $Python"

Info "Checking backend: $BackendUrl/api/health"
try {
    $response = Invoke-RestMethod -Uri "$BackendUrl/api/health" -TimeoutSec 3
    if ($response.status -eq "ok") {
        Ok "Backend is online. MySQL ready: $($response.mysqlReady)"
    } else {
        Warn "Backend responded but status is $($response.status). Detail: $($response.detail)"
    }
} catch {
    Warn "Backend check failed: $($_.Exception.Message)"
    Warn "Start backend first with: .\start-dev.ps1"
}

Info "Starting desktop app..."
Set-Location $DesktopDir
& $Python main.py
