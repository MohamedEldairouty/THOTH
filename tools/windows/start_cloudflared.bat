@echo off
REM ────────────────────────────────────────────────────────────────────
REM  Cloudflare Tunnel auto-start + auto-restart launcher.
REM
REM  Loops forever: if cloudflared exits for any reason (network change,
REM  sleep wake, SIGTERM, transient failure), wait 5 s and relaunch.
REM  Stops only when you manually close the cmd window or kill the bat.
REM ────────────────────────────────────────────────────────────────────

set LOGFILE=D:\Prog\Thoth\cloudflared.log

REM Wait for network to be ready after boot
timeout /t 15 /nobreak >nul

:restart_loop
echo. >> "%LOGFILE%"
echo ===== Started %DATE% %TIME% ===== >> "%LOGFILE%"

cloudflared --config C:\Users\dairo\.cloudflared\config.yml tunnel run thoth >> "%LOGFILE%" 2>&1

echo ===== Exited %DATE% %TIME% (will restart in 5s) ===== >> "%LOGFILE%"
timeout /t 5 /nobreak >nul
goto restart_loop
