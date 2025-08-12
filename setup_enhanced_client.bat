@echo off
echo Installing CopyArena Professional Windows Client v2.0...
echo.

cd windows_client

echo Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Installation complete!
echo.
echo You can now run the enhanced client with:
echo   python copyarena_client.py
echo.
echo Features included:
echo   - Secure credential storage
echo   - Auto-reconnection
echo   - System tray integration  
echo   - Professional UI/UX
echo   - Advanced logging
echo   - Master status notifications
echo.
pause
