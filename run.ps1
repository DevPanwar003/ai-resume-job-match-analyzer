# Run from any working directory; never silently select a different port.
$ErrorActionPreference = 'Stop'
$projectDirectory = $PSScriptRoot
$pythonExecutable = Join-Path $projectDirectory '.venv\Scripts\python.exe'
$applicationFile = Join-Path $projectDirectory 'app.py'
if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw 'Project virtual environment is missing. Follow README setup instructions.'
}
$occupied = [System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() |
    Where-Object { $_.Port -eq 8502 }
if ($occupied) {
    throw 'Port 8502 is already occupied. Stop the existing app in its terminal before restarting; no second instance was started.'
}
Push-Location -LiteralPath $projectDirectory
try {
    Write-Host "Project: $projectDirectory"
    Write-Host "Python: $pythonExecutable"
    & $pythonExecutable -m streamlit run $applicationFile --server.address 127.0.0.1 --server.port 8502
} finally {
    Pop-Location
}
