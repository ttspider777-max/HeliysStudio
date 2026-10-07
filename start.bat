@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv (
  echo Создаю окружение и ставлю зависимости...
  python -m venv .venv
  .venv\Scripts\python -m pip install -r requirements.txt
)
.venv\Scripts\python main.py
pause
