@echo off
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv || python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
  .venv\Scripts\pip install --no-deps "moviepy==2.2.1"
)
.venv\Scripts\python main.py
pause
