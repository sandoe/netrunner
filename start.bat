@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %ERRORLEVEL%==0 (
    py -3 scripts\start_netrunner.py %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
    python scripts\start_netrunner.py %*
    exit /b %ERRORLEVEL%
)

echo Python 3 was not found. Install Python 3.10+ and run this again.
exit /b 1
