# CopyArena Professional Windows Client v2.0 Setup Script

Write-Host "🚀 Installing CopyArena Professional Windows Client v2.0..." -ForegroundColor Green
Write-Host ""

# Change to windows_client directory
Set-Location -Path "windows_client"

Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
pip install --upgrade pip
pip install -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Installation complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🎯 You can now run the enhanced client with:" -ForegroundColor Cyan
    Write-Host "   python copyarena_client.py" -ForegroundColor White
    Write-Host ""
    Write-Host "🌟 Features included:" -ForegroundColor Cyan
    Write-Host "   ✅ Secure credential storage" -ForegroundColor White
    Write-Host "   ✅ Auto-reconnection system" -ForegroundColor White
    Write-Host "   ✅ System tray integration" -ForegroundColor White
    Write-Host "   ✅ Professional UI/UX" -ForegroundColor White
    Write-Host "   ✅ Advanced logging with colors" -ForegroundColor White
    Write-Host "   ✅ Master status notifications" -ForegroundColor White
    Write-Host "   ✅ System notifications" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Installation failed. Please check the error messages above." -ForegroundColor Red
    Write-Host ""
}

Read-Host "Press Enter to continue..."
