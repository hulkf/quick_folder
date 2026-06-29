@echo off
set "APP_DIR=%~dp0"
set "LOG=%APP_DIR%startup.log"

echo [%DATE% %TIME%] Starting Quick Folder... > "%LOG%"

REM Try pythonw first (no console), fall back to python
pythonw "%APP_DIR%main.py" >> "%LOG%" 2>&1
if %errorlevel% equ 0 (
    echo Started successfully with pythonw >> "%LOG%"
    exit /b
)

echo pythonw failed, trying python... >> "%LOG%"
python "%APP_DIR%main.py" >> "%LOG%" 2>&1
if %errorlevel% equ 0 (
    echo Started successfully with python >> "%LOG%"
    exit /b
)

echo FAILED to start Quick Folder >> "%LOG%"
start notepad "%LOG%"
