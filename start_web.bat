@echo off
echo ========================================
echo   UDS Terminal - Nintendo Edition
echo   Web UI Startup
echo ========================================
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
echo.

REM Start the server
echo Starting web server on http://localhost:8080
echo Press Ctrl+C to stop
echo.
python -m web.server

pause
