@echo off
echo ============================================
echo Starting Digital Twin FastAPI Service
echo ============================================
echo.

REM Check if virtual environment exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate
echo.

REM Install/update requirements
echo Installing/updating dependencies...
pip install -r requirements.txt
echo.

REM Start FastAPI with uvicorn
echo ============================================
echo Starting FastAPI server on port 8000...
echo ============================================
echo.
echo API Documentation: http://localhost:8000/docs
echo Health Check: http://localhost:8000/health
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
