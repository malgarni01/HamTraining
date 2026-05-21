@echo off
REM ============================================================
REM  Start-Training.bat
REM  ----------------------------------------------------------
REM  Double-click to open the Pig Training launcher.
REM  Keeps this terminal window visible so the trainer can read
REM  the [REWARD] log from whichever task is selected.
REM ============================================================

title Pig Training
cd /d "%~dp0"

set "PYEXE=%LOCALAPPDATA%\Python\bin\python.exe"

if not exist "%PYEXE%" (
    echo.
    echo Python interpreter not found at:
    echo   %PYEXE%
    echo.
    echo Ask the lab tech to install Python or update this shortcut.
    echo.
    pause
    exit /b 1
)

"%PYEXE%" launcher.py

REM Keep the window open after the session ends so the trainer can
REM read the final [REWARD] / report output before closing.
echo.
echo ----- session ended -----
pause
