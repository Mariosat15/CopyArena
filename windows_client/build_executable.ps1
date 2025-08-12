# CopyArena Professional Client v2.0 - Enhanced Build Script
# PowerShell version for advanced build management

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " 🚀 CopyArena Professional Client v2.0" -ForegroundColor Green
Write-Host "    Enhanced Build System" -ForegroundColor Green  
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Install Dependencies
Write-Host "📦 Step 1: Installing enhanced dependencies..." -ForegroundColor Yellow
Write-Host ""

try {
    # Upgrade pip
    Write-Host "Upgrading pip..." -ForegroundColor Gray
    & pip install --upgrade pip
    
    # Install requirements
    Write-Host "Installing professional client dependencies..." -ForegroundColor Gray
    & pip install -r requirements.txt
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install dependencies"
    }
    
    Write-Host "✅ Dependencies installed successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to install dependencies!" -ForegroundColor Red
    Write-Host "Please check the error messages above." -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

Write-Host ""

# Step 2: Clean Previous Builds
Write-Host "🔧 Step 2: Cleaning previous builds..." -ForegroundColor Yellow

if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
    Write-Host "Removed dist directory" -ForegroundColor Gray
}

if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
    Write-Host "Removed build directory" -ForegroundColor Gray
}

Write-Host "✅ Clean complete!" -ForegroundColor Green
Write-Host ""

# Step 3: Build Executable
Write-Host "🔨 Step 3: Building professional executable..." -ForegroundColor Yellow
Write-Host "This may take several minutes for the enhanced client..." -ForegroundColor Gray
Write-Host ""

$buildStartTime = Get-Date

try {
    & pyinstaller CopyArenaClient.spec --clean --noconfirm
    
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed"
    }
} catch {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    Write-Host "Please check the error messages above." -ForegroundColor Red
    Read-Host "Press Enter to exit..."
    exit 1
}

$buildEndTime = Get-Date
$buildDuration = $buildEndTime - $buildStartTime

Write-Host ""

# Step 4: Verify Build
Write-Host "🎯 Step 4: Verifying build..." -ForegroundColor Yellow

$exePath = "dist\CopyArenaClient_Professional_v2.0.exe"

if (Test-Path $exePath) {
    Write-Host "✅ Build successful!" -ForegroundColor Green
    Write-Host ""
    
    # Get file information
    $fileInfo = Get-Item $exePath
    $fileSizeMB = [math]::Round($fileInfo.Length / 1MB, 2)
    
    Write-Host "Executable location: $exePath" -ForegroundColor Cyan
    Write-Host "File size: $fileSizeMB MB ($($fileInfo.Length) bytes)" -ForegroundColor Cyan
    Write-Host "Build time: $($buildDuration.TotalMinutes.ToString('F1')) minutes" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "🌟 Professional features included:" -ForegroundColor Green
    Write-Host "   ✅ Secure credential storage (Windows Keyring + AES)" -ForegroundColor White
    Write-Host "   ✅ Auto-reconnection system (intelligent retry logic)" -ForegroundColor White
    Write-Host "   ✅ System tray integration (minimize to tray)" -ForegroundColor White
    Write-Host "   ✅ Professional UI/UX (modern design + icons)" -ForegroundColor White
    Write-Host "   ✅ Advanced logging (color-coded + search/filter)" -ForegroundColor White
    Write-Host "   ✅ Master status notifications (real-time alerts)" -ForegroundColor White
    Write-Host "   ✅ System notifications (native Windows alerts)" -ForegroundColor White
    Write-Host ""
    
    Write-Host "🚀 Your professional trading client is ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "To deploy:" -ForegroundColor Cyan
    Write-Host "1. Copy the executable to target machine" -ForegroundColor White
    Write-Host "2. Run as administrator (first time only)" -ForegroundColor White  
    Write-Host "3. Configure credentials and enjoy!" -ForegroundColor White
    
} else {
    Write-Host "❌ Build verification failed!" -ForegroundColor Red
    Write-Host "Expected executable not found at: $exePath" -ForegroundColor Red
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Read-Host "Press Enter to continue"
