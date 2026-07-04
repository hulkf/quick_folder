@echo off
setlocal

set "APP_DIR=%~dp0"
set "LOG=%APP_DIR%startup.log"
set "SCRIPT=%APP_DIR%main_pyqt5.py"

cd /d "%APP_DIR%"
echo [%DATE% %TIME%] Launch requested. >> "%LOG%"

where pythonw.exe >nul 2>nul
if %errorlevel% equ 0 (
    start "Quick Folder" /D "%APP_DIR%" pythonw.exe "%SCRIPT%"
    exit /b 0
)

where python.exe >nul 2>nul
if %errorlevel% equ 0 (
    start "Quick Folder" /D "%APP_DIR%" python.exe "%SCRIPT%"
    exit /b 0
)

echo Python was not found in PATH. >> "%LOG%"
echo Python was not found in PATH.
echo.
echo Please install Python or add it to PATH, then run this file again.
pause
exit /b 1
