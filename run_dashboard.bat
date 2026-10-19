@echo off
setlocal
cd /d "%~dp0"

title Aivara Insight - Power BI Executive Analytics Server

echo ======================================================
echo       Aivara Insight - Power BI Executive Canvas
echo ======================================================
echo.
echo Starting Aivara Analytical Engine & Power BI Server...
echo Opening in default browser: http://localhost:3000
echo.
echo Press Ctrl+C in this window to stop the server.
echo ======================================================
echo.

start "" "http://localhost:3000"
python dashboard_server.py
