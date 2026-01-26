@echo off
echo ============================================
echo Stopping Vector Database Dashboard Services
echo ============================================
echo.

echo Stopping Node.js processes (Backend and Frontend)...
taskkill /F /IM node.exe >nul 2>&1

if errorlevel 1 (
    echo No Node.js services running.
) else (
    echo Node.js services stopped successfully!
)

echo.
echo All services stopped!
echo.
pause
