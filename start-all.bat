@echo off
echo ============================================
echo Starting Vector Database Dashboard Services
echo ============================================
echo.

REM Check if Qdrant is running
echo [1/5] Checking Qdrant connection
curl -s http://localhost:6333/health >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: Qdrant is not running on port 6333!
    echo.
    echo Would you like to start Qdrant now? (Y/N)
    set /p start_qdrant="Start Qdrant? (Y/N): "
    if /i "%start_qdrant%"=="Y" (
        echo.
        echo Starting Qdrant
        call start-qdrant.bat
        if errorlevel 1 (
            echo Failed to start Qdrant. Exiting
            exit /b 1
        )
    ) else (
        echo.
        echo Please start Qdrant manually using: start-qdrant.bat
        echo Or: docker run -d --name qdrant-vector-db -p 6333:6333 qdrant/qdrant
        echo.
        pause
        exit /b 1
    )
)
echo Qdrant is running!
echo.

REM Start Backend
echo [2/5] Starting Backend API (Node.js)
cd backend
if not exist node_modules (
    echo Installing backend dependencies
    call npm install
)
start "Backend API - Port 5000" cmd /k "npm start"
cd ..
timeout /t 3 /nobreak >nul
echo.

REM Start AI Service
echo [3/5] Starting AI Service (Python Flask)
cd ai-service
if not exist venv (
    echo Creating Python virtual environment
    python -m venv venv
    echo Installing AI service dependencies
    call venv\Scripts\activate.bat && pip install -r requirements.txt
)
start "AI Service - Port 5001" cmd /k "venv\Scripts\activate.bat && python app.py"
cd ..
timeout /t 3 /nobreak >nul
echo.

REM Start Digital Twin
echo [4/5] Starting Digital Twin (Python Flask)
cd digital-twin
if not exist venv (
    echo Creating Python virtual environment
    python -m venv venv
    echo Installing Digital Twin dependencies
    call venv\Scripts\activate.bat && pip install -r requirements.txt
)
start "Digital Twin - Port 5002" cmd /k "venv\Scripts\activate.bat && python app.py"
cd ..
timeout /t 3 /nobreak >nul
echo.

REM Start Frontend
echo [5/5] Starting Frontend Dashboard (React)
cd frontend
if not exist node_modules (
    echo Installing frontend dependencies
    call npm install
)
start "Frontend Dashboard - Port 3000" cmd /k "npm start"
cd ..
echo.

echo ============================================
echo All services started successfully!
echo ============================================
echo.
echo Services are running on:
echo   - Frontend:     http://localhost:3000
echo   - Backend API:  http://localhost:5000
echo   - AI Service:   http://localhost:5001
echo   - Digital Twin: http://localhost:5002
echo   - Qdrant:       http://localhost:6333
echo.
echo Press any key to open the dashboard in your browser...
pause >nul
start http://localhost:3000
echo.
echo NOTE: To stop all services, close all the terminal windows.
echo.
pause
