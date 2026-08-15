@echo off
cd /d "%~dp0"
rem 优先用项目虚拟环境，其次系统 python（python 命令可用性因机器而异）
if exist ".venv\Scripts\python.exe" (
  set "PY=.venv\Scripts\python.exe"
) else (
  set "PY=python"
)
"%PY%" main.py --headless-check
if errorlevel 1 (
  echo Self-check failed. Make sure Python is installed and in PATH.
  pause
  exit /b 1
)
"%PY%" main.py
pause
