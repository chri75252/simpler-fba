@echo off
echo Starting FBA Monitoring System...
echo.

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

REM Start monitoring system in background
echo Starting monitoring system...
start "FBA Monitor" python monitoring_system.py

REM Wait a moment
timeout /t 3 /nobreak >nul

REM Start notification system in background
echo Starting notification system...
start "FBA Notifier" python flag_notifier.py

echo.
echo Both monitoring systems are now running in background windows.
echo.
echo To check flags manually, run: python monitoring_system.py --show-flags
echo To stop monitoring, close the "FBA Monitor" and "FBA Notifier" windows.
echo.
pause
