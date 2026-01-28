@echo off
echo ============================================
echo Testing FastAPI Digital Twin Endpoints
echo ============================================
echo.

echo Testing health endpoint...
curl -X GET http://localhost:8000/health
echo.
echo.

echo Testing API v1 health...
curl -X GET http://localhost:8000/api/v1/conflicts/
echo.
echo.

echo ============================================
echo Test complete! 
echo Full API docs: http://localhost:8000/docs
echo ============================================
pause
