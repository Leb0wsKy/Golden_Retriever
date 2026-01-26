@echo off
echo ============================================
echo Stopping Vector Database Dashboard Services
echo ============================================
echo.

echo Stopping all services...
echo.

REM Stop Node.js processes (Backend and Frontend)
echo Stopping Backend and Frontend...
taskkill /F /FI "WINDOWTITLE eq Backend API - Port 5000*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Frontend Dashboard - Port 3000*" >nul 2>&1

REM Stop Python processes (AI Service and Digital Twin)
echo Stopping AI Service and Digital Twin...
taskkill /F /FI "WINDOWTITLE eq AI Service - Port 5001*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Digital Twin - Port 5002*" >nul 2>&1

REM Alternative: Kill by port if window title doesn't work
echo Cleaning up any remaining processes on ports...
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5000" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5001" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":5002" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":3000" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

echo.
echo ============================================
echo All services stopped!
echo ============================================
echo.
pause
