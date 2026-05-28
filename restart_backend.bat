@echo off
REM Kills uvicorn (whatever PID holds port 8001). The start_thoth_backend.bat
REM auto-restart loop will respawn it within ~5 s with your new code.

echo Killing uvicorn on port 8001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001 ^| findstr LISTENING') do (
    echo   PID %%a
    taskkill /PID %%a /F >nul 2>&1
)

echo Waiting 20 s for auto-restart loop (uvicorn + Whisper preload)...
timeout /t 20 /nobreak >nul

echo Checking...
netstat -ano | findstr :8001
if errorlevel 1 (
    echo [WARN] Backend not listening. Check D:\Prog\Thoth\thoth_backend.log
) else (
    echo [OK] Backend is back up.
)
pause
