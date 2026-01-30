@echo off
echo ============================================
echo Stopping Vector Database Dashboard Services
echo ============================================
echo.

echo Stopping Python processes (Digital Twin, AI Service, ML Services)...
taskkill /F /FI "WINDOWTITLE eq Digital Twin - Port 8000" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq AI Service - Port 5001" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq ML Prediction API - Port 5003" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq ML Integration - Monitoring" >nul 2>&1

echo Stopping Node.js processes (Backend and Frontend)...
taskkill /F /IM node.exe >nul 2>&1

if errorlevel 1 (
    echo No services running.
) else (
    echo All services stopped successfully!
)

echo.
echo All services stopped!
echo.
pause
