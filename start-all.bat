@echo off
echo ============================================
echo Starting Vector Database Dashboard Services
echo ============================================
echo.
echo Using Qdrant Cloud (no local Docker needed)
echo.

REM Start Digital Twin FastAPI Service
echo [1/6] Starting Digital Twin Service (FastAPI)
cd digital-twin
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
start "Digital Twin - Port 8000" cmd /k "venv\Scripts\activate && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
cd ..
timeout /t 5 /nobreak >nul
echo.

REM Start AI Service
echo [2/6] Starting AI Service (Flask)
cd ai-service
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
start "AI Service - Port 5001" cmd /k "venv\Scripts\activate && pip install -r requirements.txt && python app.py"
cd ..
timeout /t 5 /nobreak >nul
echo.

REM Start ML Prediction API
echo [3/6] Starting ML Prediction API (Flask)
cd ai-service
start "ML Prediction API - Port 5003" cmd /k "venv\Scripts\activate && cd conflict_prediction_model && pip install -r requirements.txt && cd .. && python ml_prediction_api.py"
cd ..
timeout /t 5 /nobreak >nul
echo.

REM Start Backend
echo [4/6] Starting Backend API (Node.js)
cd backend
if not exist node_modules (
    echo Installing backend dependencies...
    call npm install
)
start "Backend API - Port 5000" cmd /k "npm start"
cd ..
timeout /t 3 /nobreak >nul
echo.

REM Start Frontend
echo [5/6] Starting Frontend Dashboard (React)
cd frontend
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
)
start "Frontend Dashboard - Port 3000" cmd /k "set BROWSER=none && npm start"
cd ..
timeout /t 8 /nobreak >nul
echo.

REM Start ML Integration Service
echo [6/6] Starting ML Integration Service (Background Monitor)
cd ai-service
start "ML Integration - Monitoring" cmd /k "venv\Scripts\activate && python ml_integration_service.py"
cd ..
echo.

REM Wait for services to start
echo Waiting for all services to initialize...
timeout /t 5 /nobreak >nul
echo.

echo ============================================
echo All services started!
echo ============================================
echo.
echo Services running:
echo   - Qdrant Cloud: Connected (configured in .env)
echo   - Digital Twin (FastAPI): http://localhost:8000
echo   - AI Service (Flask): http://localhost:5001
echo   - ML Prediction API (Flask): http://localhost:5003
echo   - Backend API: http://localhost:5000
echo   - Frontend Dashboard: http://localhost:3000
echo   - ML Integration Service: Running (monitors networks every 30s)
echo.
echo Opening dashboard in your browser...
timeout /t 2 /nobreak >nul
start http://localhost:3000
echo.
echo NOTE: To stop services, close the terminal windows or run stop-all.bat
echo.
pause
