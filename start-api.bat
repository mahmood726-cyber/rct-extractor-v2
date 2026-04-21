@echo off
REM =====================================================================
REM  start-api.bat — launch the rct-extractor-v2 FastAPI server
REM
REM  Serves on 127.0.0.1:8000 so the allmeta RCT Extractor page can
REM  call POST /extract and /extract/pdf. CORS in src/api/main.py is
REM  already permissive; no extra env needed.
REM
REM  Manual use:     double-click this file
REM  Auto-start:     run install-autostart.ps1 from an Admin PowerShell
REM  Stop:           close the console window, or: taskkill /IM python.exe /F
REM =====================================================================

setlocal

REM CD to the script's own directory so relative imports work.
cd /d "%~dp0"

REM Python from the venv if one exists, else system python.
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

REM Bind to loopback only — no external access.
echo [rct-extractor] starting on http://127.0.0.1:8000
"%PY%" -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --log-level info

endlocal
