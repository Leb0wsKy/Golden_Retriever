@echo off
echo ============================================================
echo   POPULATE PRE-CONFLICT MEMORY
echo ============================================================
echo.
echo This will generate synthetic pre-conflict states and store
echo them in Qdrant's pre_conflict_memory collection.
echo.
echo Default: 50 states
echo Custom: populate-pre-conflict.bat --count 100
echo.
echo ============================================================
echo.

cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist "digital-twin\venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call digital-twin\venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Run the population script
python populate_pre_conflict_memory.py %*

echo.
echo ============================================================
echo   DONE!
echo ============================================================
echo.
pause
