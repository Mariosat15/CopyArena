@echo off
echo.
echo ====================================
echo   CopyArena - Push to GitHub
echo ====================================
echo.

REM Check if we're in a git repository
git status >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Not in a git repository!
    echo Please run this script from the project root directory.
    pause
    exit /b 1
)

REM Add all changes
echo [1/4] Adding all changes...
git add .
if %errorlevel% neq 0 (
    echo ERROR: Failed to add files!
    pause
    exit /b 1
)

REM Check if there are changes to commit
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo No changes to commit. Repository is up to date.
    echo.
    echo Checking remote status...
    git status
    pause
    exit /b 0
)

REM Get commit message from user
set /p commit_message="Enter commit message (or press Enter for default): "
if "%commit_message%"=="" (
    set commit_message=Update: %date% %time%
)

REM Commit changes
echo [2/4] Committing changes...
git commit -m "%commit_message%"
if %errorlevel% neq 0 (
    echo ERROR: Failed to commit changes!
    pause
    exit /b 1
)

REM Push to GitHub
echo [3/4] Pushing to GitHub repository...
echo Repository: https://github.com/Mariosat15/copyarena
git push origin main
if %errorlevel% neq 0 (
    echo ERROR: Failed to push to GitHub!
    echo Please check your internet connection and GitHub credentials.
    pause
    exit /b 1
)

REM Success
echo [4/4] Success!
echo.
echo ====================================
echo   ✅ PUSH SUCCESSFUL!
echo ====================================
echo.
echo Your CopyArena project has been successfully pushed to:
echo https://github.com/Mariosat15/copyarena
echo.
echo Recent commits:
git log --oneline -5
echo.
pause 