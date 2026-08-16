@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" tools\install_extension.py
) else (
  python tools\install_extension.py
)
pause
