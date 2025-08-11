# CopyArena - Push to GitHub Script
# PowerShell version

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "   CopyArena - Push to GitHub" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in a git repository
try {
    git status | Out-Null
} catch {
    Write-Host "ERROR: Not in a git repository!" -ForegroundColor Red
    Write-Host "Please run this script from the project root directory." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Add all changes
Write-Host "[1/4] Adding all changes..." -ForegroundColor Yellow
try {
    git add .
} catch {
    Write-Host "ERROR: Failed to add files!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if there are changes to commit
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "No changes to commit. Repository is up to date." -ForegroundColor Green
    Write-Host ""
    Write-Host "Checking remote status..." -ForegroundColor Cyan
    git status
    Read-Host "Press Enter to exit"
    exit 0
}

# Get commit message from user
$commitMessage = Read-Host "Enter commit message (or press Enter for default)"
if ([string]::IsNullOrWhiteSpace($commitMessage)) {
    $commitMessage = "Update: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}

# Commit changes
Write-Host "[2/4] Committing changes..." -ForegroundColor Yellow
try {
    git commit -m $commitMessage
} catch {
    Write-Host "ERROR: Failed to commit changes!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Push to GitHub
Write-Host "[3/4] Pushing to GitHub repository..." -ForegroundColor Yellow
Write-Host "Repository: https://github.com/Mariosat15/CopyArena" -ForegroundColor Cyan
try {
    git push origin main
} catch {
    Write-Host "ERROR: Failed to push to GitHub!" -ForegroundColor Red
    Write-Host "Please check your internet connection and GitHub credentials." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Success
Write-Host "[4/4] Success!" -ForegroundColor Green
Write-Host ""
Write-Host "====================================" -ForegroundColor Green
Write-Host "   ✅ PUSH SUCCESSFUL!" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your CopyArena project has been successfully pushed to:" -ForegroundColor Cyan
Write-Host "https://github.com/Mariosat15/CopyArena" -ForegroundColor Blue
Write-Host ""
Write-Host "Recent commits:" -ForegroundColor Cyan
git log --oneline -5
Write-Host ""
Read-Host "Press Enter to exit" 