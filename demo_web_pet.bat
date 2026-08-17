@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" demo_web_pet.py
) else (
  python demo_web_pet.py
)
pause
