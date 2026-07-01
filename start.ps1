# Robot Inspection System - Start Script
# Usage: Double-click start.bat, or run .\start.ps1 in PowerShell

$ROOT = $PSScriptRoot
$CONDA_PYTHON = "$ROOT\.conda\python.exe"
$BACKEND_DIR = "$ROOT\backend"

function Info($msg)    { Write-Host "  [INFO] $msg" -ForegroundColor Cyan }
function Success($msg) { Write-Host "  [ OK ] $msg" -ForegroundColor Green }
function Warn($msg)    { Write-Host "  [WARN] $msg" -ForegroundColor Yellow }
function Err($msg)     { Write-Host "  [ERR ] $msg" -ForegroundColor Red }

Write-Host ""
Write-Host "  ==========================================" -ForegroundColor Blue
Write-Host "   Robot Inspection System - Starting..." -ForegroundColor Blue
Write-Host "  ==========================================" -ForegroundColor Blue
Write-Host ""

# Check Python
if (Test-Path $CONDA_PYTHON) {
    Success "Found local conda env: .conda\python.exe"
    $PYTHON = $CONDA_PYTHON
} else {
    Warn "Local .conda not found, trying system Python..."
    $PYTHON = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PYTHON) {
        Err "Python not found. Please install conda env or add Python to PATH."
        Read-Host "Press Enter to exit"
        exit 1
    }
    Info "Using system Python: $PYTHON"
}

# Check uvicorn, install deps if missing
$UVICORN_MODULE = & $PYTHON -c "import uvicorn; print('ok')" 2>$null
if ($UVICORN_MODULE -ne "ok") {
    Info "Installing dependencies..."
    & $PYTHON -m pip install -r "$BACKEND_DIR\requirements.txt" -q
    if ($LASTEXITCODE -ne 0) {
        Err "Failed to install dependencies."
        Read-Host "Press Enter to exit"
        exit 1
    }
    Success "Dependencies installed."
}

# Start backend
Info "Starting backend server..."
Info "Open in browser: http://localhost:8000"
Info "Login: admin / admin123"
Write-Host ""
Write-Host "  Press Ctrl+C to stop" -ForegroundColor DarkGray
Write-Host ""

Set-Location $BACKEND_DIR
& $PYTHON -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
