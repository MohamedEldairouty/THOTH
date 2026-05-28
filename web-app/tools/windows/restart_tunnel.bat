@echo off
REM Kills cloudflared. The start_cloudflared.bat auto-restart loop will
REM respawn it within ~5 s with the current config.

echo Killing cloudflared...
taskkill /F /IM cloudflared.exe /T >nul 2>&1

echo Waiting 10 s for auto-restart loop + tunnel reconnect...
timeout /t 10 /nobreak >nul

echo Checking...
tasklist | findstr cloudflared
if errorlevel 1 (
    echo [WARN] cloudflared not running. Check D:\Prog\Thoth\cloudflared.log
) else (
    echo [OK] cloudflared is back. URL should resolve within ~10 s.
)
pause
