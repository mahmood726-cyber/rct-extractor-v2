# install-autostart.ps1
#
# Creates a Startup-folder shortcut that starts the rct-extractor-v2 FastAPI
# server silently on user login. Plus a one-time launch so you don't have to
# log out / in to start using it immediately.
#
# Startup-folder shortcut is the most reliable path on Windows for user-context
# background servers -- Task Scheduler has stdio / environment quirks that often
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
    [switch]$Uninstall,
    [switch]$NoStart       # test mode: write launcher + shortcut but skip dep check and server start
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
    # Leave the launcher script in place -- it's checked in with the repo and a user may have
    # edited it. The Startup .lnk is what actually triggers autostart, so removing it is enough.
    Write-Host "Uninstalled. (Launcher script left at $LauncherPath -- delete manually if desired.)" -ForegroundColor Green
    exit 0
}

# ----- Install path -----

# Probe Python deps (skipped in -NoStart test mode, which is only concerned with artifact creation).
if (-not $NoStart) {
    Write-Host "Checking dependencies..." -ForegroundColor Cyan
    $check = & python -c "import fastapi, uvicorn; print('OK')" 2>&1
    if ($LASTEXITCODE -ne 0 -or -not ($check -match "OK")) {
        Write-Host "fastapi / uvicorn not importable:" -ForegroundColor Red
        Write-Host "    $check" -ForegroundColor Red
        Write-Host "Run:  pip install fastapi uvicorn python-multipart" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "Python deps present." -ForegroundColor Green
}

# Locate pythonw.exe next to python.exe (runs hidden, no console flash).
$pythonw = & python -c "import sys, os; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))" 2>$null
if (-not $pythonw -or -not (Test-Path $pythonw)) {
    if ($NoStart) {
        # In test mode, synthesise a plausible pythonw path — the lnk won't be executed.
        $pythonw = Join-Path $env:TEMP "pythonw.exe"
    } else {
        Write-Host "ERROR: pythonw.exe not found alongside python.exe" -ForegroundColor Red
        exit 1
    }
}

# Drop a tiny launcher script that logs to %LOCALAPPDATA%.
# Single-quoted here-string (@'..'@) -- no PowerShell variable expansion, so future edits
# that happen to contain $ or backticks stay literal.
$launcherBody = @'
import os, sys, datetime
log_dir = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'allmeta-rct-extractor')
os.makedirs(log_dir, exist_ok=True)
log = os.path.join(log_dir, 'server.log')
sys.stdout = sys.stderr = open(log, 'a', encoding='utf-8', buffering=1)
print('--- launch', datetime.datetime.now().isoformat(), flush=True)
import uvicorn
uvicorn.run('src.api.main:app', host='127.0.0.1', port=8000, log_level='info')
'@

# Don't blow away a user-edited launcher: only overwrite if the existing file is
# byte-identical to a previously-generated launcher (matches the canonical body, possibly
# with a leading BOM).
if (Test-Path $LauncherPath) {
    $existing = Get-Content -Raw -Path $LauncherPath
    $normalised = ($existing -replace "^\uFEFF", "") -replace "\r\n", "`n"
    $canonical  = ($launcherBody -replace "\r\n", "`n").TrimEnd("`n")
    if ($normalised.TrimEnd("`n") -ne $canonical) {
        Write-Host "WARNING: $LauncherPath exists and has been edited. Keeping your version; skipping template write." -ForegroundColor Yellow
    } else {
        Set-Content -Encoding UTF8 -Path $LauncherPath -Value $launcherBody
        Write-Host "Launcher refreshed at $LauncherPath" -ForegroundColor Gray
    }
} else {
    Set-Content -Encoding UTF8 -Path $LauncherPath -Value $launcherBody
    Write-Host "Launcher written to $LauncherPath" -ForegroundColor Gray
}

# Fail closed on path that would break shortcut argument quoting.
if ($LauncherPath -match '"') {
    Write-Host "ERROR: the install path contains a double-quote character, which can't be safely quoted into a Startup shortcut. Move the repo to a path without quotes." -ForegroundColor Red
    exit 1
}

# Create a .lnk in the Startup folder pointing at pythonw + launcher.
$wsh = New-Object -ComObject WScript.Shell
$lnk = $wsh.CreateShortcut($ShortcutPath)
$lnk.TargetPath = $pythonw
$lnk.Arguments = '"' + $LauncherPath + '"'
$lnk.WorkingDirectory = $Root
$lnk.WindowStyle = 7      # Minimised (closest to hidden for pythonw, which has no console anyway)
$lnk.Description = "allmeta rct-extractor-v2 FastAPI server"
$lnk.Save()
Write-Host "Startup shortcut created at $ShortcutPath" -ForegroundColor Green

if ($NoStart) {
    Write-Host "NoStart mode: skipped server start + health check. Artifacts only." -ForegroundColor Gray
    exit 0
}

# Start it NOW so the user doesn't have to sign out.
# Stop any existing instance on port 8000 -- but only if it's in the current user's session.
$mySession = (Get-Process -Id $PID).SessionId
$portUser = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($portUser) {
    $owner = Get-Process -Id $portUser.OwningProcess -ErrorAction SilentlyContinue
    if ($owner -and $owner.SessionId -eq $mySession -and $owner.ProcessName -match '^python') {
        try {
            Stop-Process -Id $owner.Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 1
        } catch {}
    } else {
        Write-Host "WARNING: port 8000 is held by $($owner.ProcessName) (PID $($owner.Id)) in a different session or a non-python process -- not touching it. The new launcher may fail to bind." -ForegroundColor Yellow
    }
}
# Use -ArgumentList array form to avoid string-concat quoting issues.
Start-Process -FilePath $pythonw -ArgumentList $LauncherPath -WorkingDirectory $Root -WindowStyle Hidden | Out-Null

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
