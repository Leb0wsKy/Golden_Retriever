@echo off
REM Golden Retriever - Complete System Test Runner
REM This batch file runs comprehensive tests on all system components

echo ========================================
echo Golden Retriever - System Test Runner
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo Installing test dependencies...
pip install requests >nul 2>&1

echo.
echo ========================================
echo IMPORTANT: Ensure all services are running!
echo ========================================
echo.
echo Required services:
echo   - Digital Twin (port 8000)
echo   - Backend (port 5000)
echo   - AI Service (port 3001)
echo.
echo If not running, press Ctrl+C and run start-all.bat first
echo.
pause

echo.
echo Running complete system tests...
echo.

python test_complete_system.py

echo.
echo ========================================
echo Test run complete!
echo ========================================
echo.
pause
