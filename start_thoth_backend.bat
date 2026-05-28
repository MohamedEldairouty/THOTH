@echo off
REM ────────────────────────────────────────────────────────────────────
REM  THOTH backend auto-start + auto-restart launcher.
REM
REM  Loops forever: if uvicorn exits (crash, sleep wake, Postgres
REM  hiccup), wait 5 s and relaunch.
REM ────────────────────────────────────────────────────────────────────

set LOGFILE=D:\Prog\Thoth\thoth_backend.log

REM Give Postgres + Cloudflared services time to come online after boot
timeout /t 15 /nobreak >nul

cd /d D:\Prog\Thoth\web-app\backend

REM Activate the runtime venv (NOT .venv-train)
call .venv\Scripts\activate.bat

REM Force UTF-8 so prints with em-dash / arrow / ellipsis don't crash when
REM stdout is redirected to the log file (Windows cp1252 default would fail).
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

:restart_loop
echo. >> "%LOGFILE%"
echo ===== Started %DATE% %TIME% ===== >> "%LOGFILE%"

REM --host 0.0.0.0 so the LAN can reach it too (phones on same wifi)
REM No --reload because we're not actively coding when auto-started
uvicorn app.main:app --host 0.0.0.0 --port 8001 >> "%LOGFILE%" 2>&1

echo ===== Exited %DATE% %TIME% (will restart in 5s) ===== >> "%LOGFILE%"
timeout /t 5 /nobreak >nul
goto restart_loop
