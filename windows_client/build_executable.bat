@echo off
echo Building CopyArena Windows Client...

REM Install requirements if not already installed
pip install -r requirements.txt

REM Create executable using PyInstaller spec file (with NumPy fix)
pyinstaller copyarena_client.spec

echo.
echo Build complete! Executable is in the 'dist' folder.
echo.
pause
