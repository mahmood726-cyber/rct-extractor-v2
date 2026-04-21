# install-autostart.ps1
#
# Creates a Startup-folder shortcut that starts the rct-extractor-v2 FastAPI
# server silently on user login. Plus a one-time launch so you don't have to
# log out / in to start using it immediately.
#
# Startup-folder shortcut is the most reliable path on Windows for user-context
# background servers — Task Scheduler has stdio / environment quirks that often
# bite pythonw-based processes.
#
# Usage:
#   Right-click -> Run with PowerShell        (preferred)
#   or in a PowerShell session:
#       powershell -ExecutionPolicy Bypass -File install-autostart.ps1
#
# Uninstall:
#       powershell -ExecutionPolicy Bypass -File install-autostart.ps1 -Uninstall

param(
    [switch]$Uninstall
)

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
if (-not $Root) { $Root = Split-Path -Parent $MyInvocation.MyCommand.Path }
$StartupFolder = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupFolder "allmeta-rct-extractor.lnk"
$LauncherPath = Join-Path $Root "_autostart_launcher.py"

# ----- Uninstall path -----
if ($Uninstall) {
    # Kill any running instance first.
    Get-Process pythonw -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
            if ($cmd -and $cmd -match "_autostart_launcher\.py") {
                Stop-Process -Id $_.Id -Force
                Write-Host "Stopped running launcher (PID $($_.Id))." -ForegroundColor Gray
            }
        } catch {}
    }
    # Old task-scheduler entry, if it existed.
    try { Unregister-ScheduledTask -TaskName "allmeta-rct-extractor" -Confirm:$false -ErrorAction Stop }
    catch {}
    if (Test-Path $ShortcutPath) {
        Remove-Item $ShortcutPath -Force
        Write-Host "Removed Startup shortcut." -ForegroundColor Green
    } else {
        Write-Host "No Startup shortcut to remove." -ForegroundColor Yellow
    }
    if (Test-Path $LauncherPath) {
        Remove-Item $LauncherPath -Force
        Write-Host "Removed launcher script." -ForegroundColor Gray
    }
    Write-Host "Uninstalled." -ForegroundColor Green
    exit 0
}

# ----- Install path -----

# Probe Python deps.
Write-Host "Checking dependencies..." -ForegroundColor Cyan
$check = & python -c "import fastapi, uvicorn; print('OK')" 2>&1
if ($LASTEXITCODE -ne 0 -or -not ($check -match "OK")) {
    Write-Host "fastapi / uvicorn not importable:" -ForegroundColor Red
    Write-Host "    $check" -ForegroundColor Red
    Write-Host "Run:  pip install fastapi uvicorn python-multipart" -ForegroundColor Yellow
    exit 1
}
Write-Host "Python deps present." -ForegroundColor Green

# Locate pythonw.exe next to python.exe (runs hidden, no console flash).
$pythonw = & python -c "import sys, os; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))" 2>$null
if (-not $pythonw -or -not (Test-Path $pythonw)) {
    Write-Host "ERROR: pythonw.exe not found alongside python.exe" -ForegroundColor Red
    exit 1
}

# Drop a tiny launcher script that logs to %LOCALAPPDATA%.
@"
import os, sys, datetime
log_dir = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'allmeta-rct-extractor')
os.makedirs(log_dir, exist_ok=True)
log = os.path.join(log_dir, 'server.log')
sys.stdout = sys.stderr = open(log, 'a', encoding='utf-8', buffering=1)
print('--- launch', datetime.datetime.now().isoformat(), flush=True)
import uvicorn
uvicorn.run('src.api.main:app', host='127.0.0.1', port=8000, log_level='info')
"@ | Set-Content -Encoding UTF8 -Path $LauncherPath
Write-Host "Launcher written to $LauncherPath" -ForegroundColor Gray

# Create a .lnk in the Startup folder pointing at pythonw + launcher.
$wsh = New-Object -ComObject WScript.Shell
$lnk = $wsh.CreateShortcut($ShortcutPath)
$lnk.TargetPath = $pythonw
$lnk.Arguments = "`"$LauncherPath`""
$lnk.WorkingDirectory = $Root
$lnk.WindowStyle = 7      # Minimised (closest to hidden for pythonw, which has no console anyway)
$lnk.Description = "allmeta rct-extractor-v2 FastAPI server"
$lnk.Save()
Write-Host "Startup shortcut created at $ShortcutPath" -ForegroundColor Green

# Start it NOW so the user doesn't have to sign out.
# Stop any existing instance on port 8000 first.
$portUser = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($portUser) {
    try { Stop-Process -Id $portUser.OwningProcess -Force -ErrorAction SilentlyContinue } catch {}
    Start-Sleep -Seconds 1
}
Start-Process -FilePath $pythonw -ArgumentList "`"$LauncherPath`"" -WorkingDirectory $Root -WindowStyle Hidden | Out-Null

# Verify the health endpoint.
Start-Sleep -Seconds 4
try {
    $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 8
    Write-Host ""
    Write-Host "rct-extractor is running at http://127.0.0.1:8000 (status: $($resp.status), version: $($resp.version))" -ForegroundColor Cyan
    Write-Host "It will auto-start on every user login." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Logs:        $env:LOCALAPPDATA\allmeta-rct-extractor\server.log" -ForegroundColor Gray
    Write-Host "Uninstall:   powershell -ExecutionPolicy Bypass -File install-autostart.ps1 -Uninstall" -ForegroundColor Gray
    Write-Host "Manual kill: Get-Process pythonw | Stop-Process" -ForegroundColor Gray
} catch {
    Write-Host "WARNING: server did not respond on :8000 within 4s." -ForegroundColor Yellow
    Write-Host "Tail the log: Get-Content $env:LOCALAPPDATA\allmeta-rct-extractor\server.log -Tail 30" -ForegroundColor Yellow
}
