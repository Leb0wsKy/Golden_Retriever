@echo off
echo ============================================
echo Starting Qdrant Vector Database
echo ============================================
echo.

REM Check if Docker is running - try multiple times
echo Checking Docker status
set docker_check_count=0
:docker_check_loop
docker info >nul 2>&1
if not errorlevel 1 goto docker_ready

set /a docker_check_count+=1
if %docker_check_count% geq 3 (
    echo.
    echo ERROR: Docker Desktop is not responding!
    echo.
    echo Please ensure Docker Desktop is fully started:
    echo   1. Check Docker Desktop is running (whale icon in system tray)
    echo   2. Wait for it to show "Docker Desktop is running"
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
)

echo Docker not ready yet, waiting 5 seconds (attempt %docker_check_count%/3)
timeout /t 5 /nobreak >nul
goto docker_check_loop

:docker_ready

echo Docker is running!
echo.

REM Check if Qdrant is already running
echo Checking if Qdrant is already running
curl -s http://localhost:6333/health >nul 2>&1
if not errorlevel 1 (
    echo Qdrant is already running on port 6333!
    echo.
    pause
    exit /b 0
)

REM Create storage directory if it does not exist
if not exist qdrant_storage (
    echo Creating Qdrant storage directory
    mkdir qdrant_storage
)

echo Starting Qdrant container
echo This may take a minute if the image needs to be downloaded
echo.

REM Check if image exists, if not pull it first
docker image inspect qdrant/qdrant:latest >nul 2>&1
if errorlevel 1 (
    echo Downloading Qdrant image (this only happens once)
    docker pull qdrant/qdrant:latest
    if errorlevel 1 (
        echo Failed to download Qdrant image
        pause
        exit /b 1
    )
)

REM Start Qdrant with persistent storage
docker run -d ^
  --name qdrant-vector-db ^
  -p 6333:6333 ^
  -p 6334:6334 ^
  -v "%cd%\qdrant_storage:/qdrant/storage" ^
  qdrant/qdrant:latest

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start Qdrant!
    echo.
    echo This might be because a container with this name already exists.
    echo Trying to start the existing container
    docker start qdrant-vector-db
    if errorlevel 1 (
        echo.
        echo Still failed. Try removing the old container:
        echo   docker rm qdrant-vector-db
        echo Then run this script again.
        echo.
        pause
        exit /b 1
    )
)

echo.
echo Waiting for Qdrant to start
timeout /t 3 /nobreak >nul

REM Wait for Qdrant to be ready
:wait_loop
curl -s http://localhost:6333/health >nul 2>&1
if errorlevel 1 (
    echo Still waiting
    timeout /t 2 /nobreak >nul
    goto wait_loop
)

echo.
echo ============================================
echo Qdrant is running successfully!
echo ============================================
echo.
echo Qdrant Dashboard: http://localhost:6333/dashboard
echo Qdrant API:       http://localhost:6333
echo.
echo To stop Qdrant: docker stop qdrant-vector-db
echo To remove:      docker rm qdrant-vector-db
echo.
pause
