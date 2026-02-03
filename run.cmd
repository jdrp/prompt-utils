@echo off
setlocal

REM Get the directory where this script lives
set "REPO_DIR=%~dp0"
cd /d "%REPO_DIR%"

REM Run using the venv python (pythonw.exe avoids a console window)
"%REPO_DIR%.venv\Scripts\pythonw.exe" -m prompt_utils_app
