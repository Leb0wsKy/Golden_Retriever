@echo off
echo ============================================
echo Complete System Setup for Vector Dashboard
echo ============================================
echo.

echo This script will:
echo   1. Check and start Docker Desktop (if needed)
echo   2. Start Qdrant database
echo   3. Install all dependencies
echo   4. Configure environment
echo.
pause

REM Step 1: Check Docker
echo.
echo [Step 1/4] Checking Docker Desktop
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo Docker Desktop is NOT running!
    echo.
    echo Starting Docker Desktop
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo.
    echo Waiting for Docker Desktop to start (this may take 30-60 seconds)
    echo.
    
    :docker_wait
    timeout /t 5 /nobreak >nul
    docker info >nul 2>&1
    if errorlevel 1 (
        echo Still waiting for Docker
        goto docker_wait
    )
    
    echo Docker Desktop is now running!
    echo Waiting 10 more seconds for Docker to be fully ready
    timeout /t 10 /nobreak >nul
) else (
    echo Docker Desktop is running!
)
echo.

REM Step 2: Start Qdrant
echo [Step 2/4] Starting Qdrant
call start-qdrant.bat
if errorlevel 1 (
    echo Failed to start Qdrant!
    pause
    exit /b 1
)
echo.

REM Step 3: Install Dependencies
echo [Step 3/4] Installing dependencies
call install-deps.bat
if errorlevel 1 (
    echo Failed to install dependencies!
    pause
    exit /b 1
)
echo.

REM Step 4: Configuration reminder
echo [Step 4/4] Configuration Check
echo.
echo IMPORTANT: Please configure your Qdrant API key in:
echo   - backend\.env (line: QDRANT_API_KEY=your_api_key_here)
echo   - ai-service\.env (line: QDRANT_API_KEY=your_api_key_here)
echo.
echo If you don't have a Qdrant Cloud API key, you can leave it empty for local use.
echo.
echo ============================================
echo Setup Complete!
echo ============================================
echo.
echo You can now start all services by running: start-all.bat
echo.
pause
