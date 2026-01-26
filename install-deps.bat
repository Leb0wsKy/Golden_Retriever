@echo off
echo ============================================
echo Installing Dependencies for All Services
echo ============================================
echo.

REM Check Node.js
echo Checking Node.js installation
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed!
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
echo Node.js found: 
node --version
echo.

REM Check Python
echo Checking Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)
echo Python found:
python --version
echo.

REM Install Backend Dependencies
echo [1/4] Installing Backend dependencies
cd backend
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install backend dependencies
    pause
    exit /b 1
)
cd ..
echo Backend dependencies installed successfully!
echo.

REM Install Frontend Dependencies
echo [2/4] Installing Frontend dependencies
cd frontend
call npm install
if errorlevel 1 (
    echo ERROR: Failed to install frontend dependencies
    pause
    exit /b 1
)
cd ..
echo Frontend dependencies installed successfully!
echo.

REM Install AI Service Dependencies
echo [3/4] Installing AI Service dependencies
cd ai-service
if not exist venv (
    echo Creating virtual environment
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install AI service dependencies
    pause
    exit /b 1
)
call venv\Scripts\deactivate.bat
cd ..
echo AI Service dependencies installed successfully!
echo.

REM Install Digital Twin Dependencies
echo [4/4] Installing Digital Twin dependencies
cd digital-twin
if not exist venv (
    echo Creating virtual environment
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install digital twin dependencies
    pause
    exit /b 1
)
call venv\Scripts\deactivate.bat
cd ..
echo Digital Twin dependencies installed successfully!
echo.

echo ============================================
echo All dependencies installed successfully!
echo ============================================
echo.
echo You can now run: start-all.bat
echo.
pause
