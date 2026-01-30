@echo off
echo ================================================
echo Starting ML Integration Service
echo ================================================
echo.
echo This service monitors networks and generates
echo pre-conflict alerts using ML predictions
echo.

cd ai-service
python ml_integration_service.py

pause
