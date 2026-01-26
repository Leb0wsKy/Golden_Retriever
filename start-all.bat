@echo off
echo ============================================
echo Starting Vector Database Dashboard Services
echo ============================================
echo.
echo Using Qdrant Cloud (no local Docker needed)
echo.

REM Start Backend
echo [1/2] Starting Backend API (Node.js)
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
echo [2/2] Starting Frontend Dashboard (React)
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
