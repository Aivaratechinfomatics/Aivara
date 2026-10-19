@echo off
setlocal
cd /d "%~dp0"

title Aivara Analytics Suite (Dual Frontends)

echo ======================================================
echo             Aivara Analytics Platform
echo ======================================================
echo Launching Dual Analytical Frontends:
echo   1. Streamlit Dashboard: http://localhost:8501
echo   2. Business Intelligence Executive Canvas: http://localhost:3000
echo ======================================================
echo.

:: Launch Executive BI dashboard in background
start "Aivara Executive BI Dashboard (Port 3000)" run_dashboard.bat

:: Launch Streamlit app
call run.bat
