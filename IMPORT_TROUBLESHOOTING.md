# 🔧 Import Resolution Troubleshooting Guide

## Current Import Issues and Solutions

### 1. Windows Client Import Warnings ⚠️

**Issue**: Missing imports for `keyring`, `pystray`, `plyer`
```
Import "keyring" could not be resolved
Import "pystray" could not be resolved  
Import "plyer" could not be resolved
```

**Solution**: Install the enhanced client dependencies
```bash
cd windows_client
pip install -r requirements.txt
```

Or use the automated setup:
```bash
# Windows Command Prompt
setup_enhanced_client.bat

# Windows PowerShell
.\setup_enhanced_client.ps1
```

### 2. Backend Module Import Issues 🔧

**Issue**: Relative imports in backend modules
```
Import "models" could not be resolved
Import "database" could not be resolved
```

**Solution**: These are relative imports within the backend directory. To fix:

1. **Run from correct directory**: Always run the backend from the project root:
   ```bash
   cd "New folder (12)"
   python -m backend.app
   ```

2. **Python path setup**: Add project root to Python path:
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   python backend/app.py
   ```

3. **IDE configuration**: Configure your IDE to recognize the project structure:
   - Set the project root as "New folder (12)"
   - Add the backend folder to Python path

### 3. Admin Panel Import Issues 🔧

**Issue**: Admin panel can't find backend modules
```
Import "models" could not be resolved
Import "database_security" could not be resolved
```

**Solution**: Run admin panel from project root:
```bash
cd "New folder (12)"
python -m admin_panel.app
```

### 4. Script Import Issues 🔧

**Issue**: Standalone scripts can't find modules
```
check_trades.py: Import "models" could not be resolved
update_user.py: Import "models" could not be resolved
```

**Solution**: These scripts need to be run from project root or have paths adjusted:

**Option A**: Run from project root
```bash
cd "New folder (12)"
python check_trades.py
python update_user.py
```

**Option B**: Add backend to path in scripts (add to top of each script):
```python
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
```

## Quick Setup Commands

### For Development Environment:
```bash
# 1. Install backend dependencies
cd backend
pip install -r requirements.txt

# 2. Install enhanced client dependencies  
cd ../windows_client
pip install -r requirements.txt

# 3. Install admin panel dependencies
cd ../admin_panel
pip install -r requirements.txt
```

### For Production Deployment:
```bash
# Set up proper Python environment
cd "New folder (12)"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run components
python -m backend.app          # Backend API
python -m admin_panel.app      # Admin panel
cd windows_client && python copyarena_client.py  # Windows client
```

## IDE Configuration

### VSCode Settings:
Add to `.vscode/settings.json`:
```json
{
    "python.analysis.extraPaths": [
        "./backend",
        "./admin_panel", 
        "./windows_client"
    ],
    "python.defaultInterpreterPath": "./venv/bin/python"
}
```

### PyCharm Settings:
1. Mark `backend`, `admin_panel`, `windows_client` as source roots
2. Set project interpreter to virtual environment
3. Enable relative imports

## Testing Import Resolution

Run this test to verify imports work:
```python
# test_imports.py
try:
    from backend.models import User, Trade
    from backend.database import engine
    print("✅ Backend imports working")
except ImportError as e:
    print(f"❌ Backend import error: {e}")

try:
    import keyring, pystray, plyer
    print("✅ Enhanced client dependencies available")
except ImportError as e:
    print(f"❌ Client dependency missing: {e}")
```

All import issues are **cosmetic linting warnings** and don't affect functionality when run from the correct directory with proper dependencies installed.
