@echo off
echo Pushing to GitHub...
git add . && git commit -m "Quick update: %date% %time%" && git push origin main
if %errorlevel% equ 0 (
    echo ✅ Successfully pushed to https://github.com/Mariosat15/copyarena
) else (
    echo ❌ Push failed! Check your changes and try again.
)
pause 