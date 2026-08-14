@echo off
cd /d "%~dp0"
python main.py --headless-check
if errorlevel 1 (
  echo Self-check failed. Make sure Python is installed and in PATH.
  pause
  exit /b 1
)
python main.py
pause