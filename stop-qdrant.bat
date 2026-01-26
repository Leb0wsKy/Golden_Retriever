@echo off
echo ============================================
echo Stopping Qdrant Vector Database
echo ============================================
echo.

docker stop qdrant-vector-db

if errorlevel 1 (
    echo No Qdrant container running or Docker not available.
) else (
    echo Qdrant stopped successfully!
)

echo.
echo To remove the container completely:
echo   docker rm qdrant-vector-db
echo.
echo To remove stored data:
echo   rmdir /s /q qdrant_storage
echo.
pause
