@echo off
echo ============================================
echo Quick Start - Vector Database Dashboard
echo ============================================
echo.
echo This is a simplified startup script.
echo It assumes Docker Desktop is already running.
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Desktop is not running!
    echo Please start Docker Desktop first, then run this script again.
    echo.
    pause
    exit /b 1
)

REM Check if Qdrant container exists
docker ps -a --filter name=qdrant-vector-db --format "{{.Names}}" | findstr qdrant-vector-db >nul 2>&1
if errorlevel 1 (
    echo Qdrant container does not exist. Creating it now
    
    if not exist qdrant_storage mkdir qdrant_storage
    
    docker run -d --name qdrant-vector-db -p 6333:6333 -p 6334:6334 -v "%cd%\qdrant_storage:/qdrant/storage" qdrant/qdrant:latest
    
    if errorlevel 1 (
        echo Failed to create Qdrant container
        pause
        exit /b 1
    )
    
    echo Waiting for Qdrant to start
    timeout /t 5 /nobreak >nul
) else (
    REM Container exists, check if it's running
    docker ps --filter name=qdrant-vector-db --format "{{.Names}}" | findstr qdrant-vector-db >nul 2>&1
    if errorlevel 1 (
        echo Starting existing Qdrant container
        docker start qdrant-vector-db
        timeout /t 3 /nobreak >nul
    ) else (
        echo Qdrant is already running
    )
)

REM Wait for Qdrant to be ready
echo Checking if Qdrant is ready
:wait_qdrant
curl -s http://localhost:6333/health >nul 2>&1
if errorlevel 1 (
    echo Waiting for Qdrant
    timeout /t 2 /nobreak >nul
    goto wait_qdrant
)

echo.
echo Qdrant is ready!
echo.

REM Now start all other services
echo Starting application services
echo.

REM Backend
echo [1/4] Starting Backend API
cd backend
if not exist node_modules call npm install
start "Backend API - Port 5000" cmd /k "npm start"
cd ..
timeout /t 2 /nobreak >nul

REM AI Service
echo [2/4] Starting AI Service
cd ai-service
if not exist venv (
    python -m venv venv
    call venv\Scripts\activate.bat && pip install -r requirements.txt
)
start "AI Service - Port 5001" cmd /k "venv\Scripts\activate.bat && python app.py"
cd ..
timeout /t 2 /nobreak >nul

REM Digital Twin
echo [3/4] Starting Digital Twin
cd digital-twin
if not exist venv (
    python -m venv venv
    call venv\Scripts\activate.bat && pip install -r requirements.txt
)
start "Digital Twin - Port 5002" cmd /k "venv\Scripts\activate.bat && python app.py"
cd ..
timeout /t 2 /nobreak >nul

REM Frontend
echo [4/4] Starting Frontend
cd frontend
if not exist node_modules call npm install
start "Frontend Dashboard - Port 3000" cmd /k "npm start"
cd ..

echo.
echo ============================================
echo All services started!
echo ============================================
echo.
echo Opening dashboard in 5 seconds
timeout /t 5 /nobreak >nul
start http://localhost:3000
echo.
echo To stop: Run stop-all.bat
echo.
pause
