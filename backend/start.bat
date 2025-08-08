@echo off
echo Starting CopyArena Backend Server...

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start FastAPI server
python app.py

pause 