@echo off
echo ============================================
echo Starting Vector Database Dashboard Services
echo ============================================
echo.
echo Using Qdrant Cloud (no local Docker needed)
echo.

REM Start Digital Twin FastAPI Service
echo [1/4] Starting Digital Twin Service (FastAPI)
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
echo [2/4] Starting AI Service (Flask)
cd ai-service
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)
start "AI Service - Port 5001" cmd /k "venv\Scripts\activate && pip install -r requirements.txt && python app.py"
cd ..
timeout /t 5 /nobreak >nul
echo.

REM Start Backend
echo [3/4] Starting Backend API (Node.js)
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
echo [4/4] Starting Frontend Dashboard (React)
cd frontend
if not exist node_modules (
    echo Installing frontend dependencies...
    call npm install
)
start "Frontend Dashboard - Port 3000" cmd /k "set BROWSER=none && npm start"
cd ..
echo.

REM Wait for services to start
echo Waiting for services to initialize...
timeout /t 8 /nobreak >nul
echo.

echo ============================================
echo All services started!
echo ============================================
echo.
echo Services running:
echo   - Qdrant Cloud: Connected (configured in .env)
echo   - Digital Twin (FastAPI): http://localhost:8000
echo   - AI Service (Flask): http://localhost:5001
echo   - Backend API: http://localhost:5000
echo   - Frontend Dashboard: http://localhost:3000
echo.
echo Opening dashboard in your browser...
timeout /t 2 /nobreak >nul
start http://localhost:3000
echo.
echo NOTE: To stop services, close the terminal windows or run stop-all.bat
echo.
pause
