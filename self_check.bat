@echo off
cd /d "%~dp0"
echo Running self-check...
python main.py --headless-check
pause