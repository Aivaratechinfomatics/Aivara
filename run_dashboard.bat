@echo off
setlocal
cd /d "%~dp0"

title Aivara Insight - Business Intelligence Executive Analytics Server

echo ======================================================
echo   Aivara Insight - Business Intelligence Executive Canvas
echo ======================================================
echo.
echo Starting Aivara Analytical Engine & Executive Server...
echo Opening in default browser: http://localhost:3000
echo.
echo Press Ctrl+C in this window to stop the server.
echo ======================================================
echo.

start "" "http://localhost:3000"
python dashboard_server.py
