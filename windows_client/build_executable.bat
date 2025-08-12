@echo off
echo ==========================================
echo  🚀 CopyArena Professional Client v2.0
echo     Enhanced Build System
echo ==========================================
echo.

echo 📦 Step 1: Installing enhanced dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to install dependencies!
    echo Please check the error messages above.
    pause
    exit /b 1
)
echo ✅ Dependencies installed successfully!
echo.

echo 🔧 Step 2: Cleaning previous builds...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
echo ✅ Clean complete!
echo.

echo 🔨 Step 3: Building professional executable...
echo This may take several minutes for the enhanced client...
pyinstaller CopyArenaClient.spec --clean --noconfirm
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Build failed!
    echo Please check the error messages above.
    pause
    exit /b 1
)
echo.

echo 🎯 Step 4: Verifying build...
if exist "dist\CopyArenaClient_Professional_v2.0.exe" (
    echo ✅ Build successful!
    echo.
    echo 📁 Executable location: dist\CopyArenaClient_Professional_v2.0.exe
    echo 📊 File size:
    for %%I in ("dist\CopyArenaClient_Professional_v2.0.exe") do echo    %%~zI bytes
    echo.
    echo 🌟 Professional features included:
    echo    ✅ Secure credential storage
    echo    ✅ Auto-reconnection system  
    echo    ✅ System tray integration
    echo    ✅ Professional UI/UX
    echo    ✅ Advanced logging
    echo    ✅ Master status notifications
    echo    ✅ System notifications
    echo.
    echo 🚀 Your professional trading client is ready!
) else (
    echo ❌ Build verification failed!
    echo Expected executable not found.
)

echo.
echo ==========================================
pause
