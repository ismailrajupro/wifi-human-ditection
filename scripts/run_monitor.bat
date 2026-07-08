@echo off
cd /d "%~dp0.."
echo WiFi Human Presence Detection - RSSI Mode
echo =========================================
echo.
python main.py -m rssi
if %errorlevel% neq 0 (
    echo.
    echo Run install_deps.bat first if you haven't already.
    pause
)
