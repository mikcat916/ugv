$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$condaPython = Join-Path $root ".conda\\python.exe"

if (Test-Path $condaPython) {
    $python = $condaPython
} else {
    $python = (Get-Command python -ErrorAction Stop).Source
}

$backendRequirements = Join-Path $root "apps\\backend\\requirements.txt"

Write-Host "[agent-setup] python: $python"
& $python -m pip install -q -r $backendRequirements

Write-Host "[agent-setup] environment ready"
