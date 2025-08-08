# CopyArena - Windows Cloud Deployment Guide

## 🚀 DigitalOcean Windows Droplet Setup

This guide shows how to deploy CopyArena with **real MT5 connectivity** on Windows cloud servers.

### 1. Create DigitalOcean Windows Droplet

**Recommended Specifications:**
- **OS**: Windows Server 2019/2022
- **Size**: 2 GB RAM, 1 vCPU (minimum)
- **Storage**: 50 GB SSD
- **Region**: Choose closest to your users

**Setup Steps:**
1. Create new Droplet on DigitalOcean
2. Choose "Windows" from OS options
3. Select Windows Server 2019 or 2022
4. Choose your preferred size (2GB+ recommended)
5. Add SSH keys or use password authentication

### 2. Initial Windows Server Setup

**Connect via RDP:**
1. Get IP address from DigitalOcean dashboard
2. Use Remote Desktop Connection
3. Username: `Administrator`
4. Password: (from DigitalOcean console)

**Install Required Software:**
```powershell
# Install Chocolatey (Windows package manager)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Python
choco install python -y

# Install Git
choco install git -y

# Install Node.js
choco install nodejs -y

# Refresh environment
refreshenv
```

### 3. MetaTrader 5 Installation

**Download and Install MT5:**
1. Download MT5 from MetaQuotes official site
2. Install MT5 terminal on the server
3. Configure MT5 for headless operation (optional)

**Enable MT5 API:**
1. Open MT5 terminal
2. Go to Tools → Options → Expert Advisors
3. Check "Allow automated trading"
4. Check "Allow DLL imports"
5. Check "Allow WebRequest"

### 4. Deploy CopyArena Backend

**Clone Repository:**
```powershell
cd C:\
git clone https://github.com/Mariosat15/CopyArena.git
cd CopyArena\backend
```

**Setup Python Environment:**
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

**Configure Environment:**
```powershell
# Create .env file
New-Item -Path ".env" -ItemType File
```

Add to `.env`:
```env
# Database
DATABASE_URL=sqlite:///./copyarena.db

# Security
SECRET_KEY=your-super-secure-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# MT5 Configuration
MT5_TIMEOUT=60000
MT5_PORTABLE=false

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### 5. Deploy Frontend

**Build Frontend:**
```powershell
cd ..\
npm install
npm run build
```

**Configure Web Server:**
Install IIS or use Python to serve static files:
```powershell
# Option 1: Serve with Python
cd dist
python -m http.server 3000

# Option 2: Install IIS and configure
# (More complex but production-ready)
```

### 6. Run Backend Server

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python app.py
```

### 7. Windows Service Setup (Production)

**Create Windows Service for Backend:**
```powershell
# Install python-windows-service
pip install pywin32

# Create service script
```

**Service Script** (`backend/service.py`):
```python
import win32serviceutil
import win32service
import win32event
import subprocess
import os
import sys

class CopyArenaService(win32serviceutil.ServiceFramework):
    _svc_name_ = "CopyArenaBackend"
    _svc_display_name_ = "CopyArena Backend Service"
    _svc_description_ = "CopyArena trading platform backend"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.process:
            self.process.terminate()
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        # Change to backend directory
        os.chdir(r'C:\CopyArena\backend')
        
        # Activate virtual environment and run app
        cmd = [r'C:\CopyArena\backend\venv\Scripts\python.exe', 'app.py']
        self.process = subprocess.Popen(cmd)
        
        # Wait for stop signal
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(CopyArenaService)
```

**Install Service:**
```powershell
python service.py install
python service.py start
```

### 8. Firewall Configuration

```powershell
# Allow HTTP traffic
New-NetFirewallRule -DisplayName "CopyArena Frontend" -Direction Inbound -Protocol TCP -LocalPort 3000 -Action Allow

# Allow Backend API
New-NetFirewallRule -DisplayName "CopyArena Backend" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow

# Allow MT5 ports (if needed)
New-NetFirewallRule -DisplayName "MT5 Terminal" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

### 9. SSL/HTTPS Setup (Production)

**Install Certbot for SSL:**
```powershell
choco install certbot -y

# Generate SSL certificate
certbot certonly --standalone -d your-domain.com
```

**Configure HTTPS in app.py:**
```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        ssl_keyfile="/path/to/private.key",
        ssl_certfile="/path/to/certificate.crt"
    )
```

### 10. Production Checklist

✅ **Windows Server running**  
✅ **MT5 terminal installed and configured**  
✅ **Python environment setup**  
✅ **CopyArena backend deployed**  
✅ **Frontend built and served**  
✅ **Windows services configured**  
✅ **Firewall rules added**  
✅ **SSL certificates installed**  
✅ **Database backup configured**  

### 11. Monitoring & Maintenance

**Log Files:**
- Backend logs: `C:\CopyArena\backend\logs\`
- MT5 logs: `%APPDATA%\MetaQuotes\Terminal\<TERMINAL_ID>\Logs\`
- Windows Event Viewer for service logs

**Backup Strategy:**
- Database: Schedule SQLite backups
- Configuration files: Backup `.env` and config files
- MT5 settings: Backup MT5 terminal configuration

**Updates:**
```powershell
# Update CopyArena
cd C:\CopyArena
git pull origin main
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt --upgrade

# Restart services
python service.py restart
```

## 🔐 Security Considerations

- Use strong passwords for Windows Administrator
- Configure Windows Firewall properly
- Use SSL/HTTPS for production
- Regular Windows updates
- Monitor MT5 terminal access
- Secure database access

## 📞 Support

For deployment issues:
1. Check Windows Event Viewer
2. Review CopyArena backend logs
3. Verify MT5 terminal connectivity
4. Test API endpoints manually

This setup provides **real MT5 connectivity** with full Windows compatibility! 🚀 