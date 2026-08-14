@echo off
cd /d "%~dp0"
echo Running camera self-check (about 10 seconds)...
python main.py --camera-check
pause