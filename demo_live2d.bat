@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" demo_live2d.py
) else (
  python demo_live2d.py
)
pause
