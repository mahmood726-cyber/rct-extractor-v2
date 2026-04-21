# start-api-hidden.ps1 — start the rct-extractor FastAPI server hidden.
# Called by the Task Scheduler entry created by install-autostart.ps1.
# Logs go to %LOCALAPPDATA%\allmeta-rct-extractor\server.log so you can
# diagnose startup failures without a visible console.
$ErrorActionPreference = "Stop"
$logDir = Join-Path $env:LOCALAPPDATA "allmeta-rct-extractor"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$logFile = Join-Path $logDir "server.log"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$python = "python"
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path $venvPython) { $python = $venvPython }

# Launch python/uvicorn hidden, redirecting stdout+stderr to the log.
$args = @("-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8000", "--log-level", "info")
Start-Process -FilePath $python -ArgumentList $args `
    -WorkingDirectory $root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError (Join-Path $logDir "server.err.log")
