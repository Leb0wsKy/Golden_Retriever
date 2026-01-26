@echo off
echo ============================================
echo Vector Dashboard - Complete Setup
echo ============================================
echo.
echo This script will:
echo   1. Install backend dependencies (Node.js)
echo   2. Install frontend dependencies (React)
echo.
echo Note: This project uses Qdrant Cloud (no Docker needed)
echo Make sure you configure your Qdrant Cloud credentials in:
echo   - .env (root directory)
echo   - backend\.env
echo.
pause

REM Check Node.js
echo.
echo [Step 1/3] Checking Node.js installation...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed!
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
node --version
echo Node.js is installed!
echo.

REM Install Backend Dependencies
echo [Step 2/3] Installing Backend Dependencies...
cd backend
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install backend dependencies!
    pause
    exit /b 1
)
echo Backend dependencies installed!
cd ..
echo.

REM Install Frontend Dependencies
echo [Step 3/3] Installing Frontend Dependencies...
cd frontend
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install frontend dependencies!
    pause
    exit /b 1
)
echo Frontend dependencies installed!
cd ..
echo.

echo ============================================
echo Setup Complete!
echo ============================================
echo.
echo Next steps:
echo   1. Configure your Qdrant Cloud credentials in .env files
echo      Get credentials from: https://cloud.qdrant.io
echo   2. Run: start-all.bat to start all services
echo.
pause
