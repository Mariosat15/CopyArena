@echo off
echo Building CopyArena Frontend for Windows Deployment...

REM Install dependencies
echo Installing dependencies...
npm install

REM Build for production
echo Building for production...
npm run build

echo.
echo Build completed! 
echo Frontend built in 'dist' folder
echo.
echo Next steps:
echo 1. Copy 'dist' folder to your Windows server
echo 2. Serve using IIS, serve, or python -m http.server
echo 3. Configure firewall rules for port 3000 (or 80/443 for IIS)
echo.

pause 