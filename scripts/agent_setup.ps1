$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$condaPython = Join-Path $root ".conda\\python.exe"

if (Test-Path $condaPython) {
    $python = $condaPython
} else {
    $python = (Get-Command python -ErrorAction Stop).Source
}

$backendRequirements = Join-Path $root "backend\\requirements.txt"
$desktopRequirements = Join-Path $root "desktop\\requirements.txt"

Write-Host "[agent-setup] python: $python"
& $python -m pip install -q -r $backendRequirements

try {
    & $python -c "import PyQt5" | Out-Null
} catch {
    & $python -m pip install -q -r $desktopRequirements
}

Write-Host "[agent-setup] environment ready"
