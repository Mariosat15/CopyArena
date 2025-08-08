# CopyArena Backend Deployment

## Windows Cloud Deployment (Production)

This backend is designed for **real MetaTrader5 integration** on Windows cloud servers.

### Supported Cloud Providers

✅ **DigitalOcean Windows Droplets** (Recommended)  
✅ **Azure Windows Virtual Machines**  
✅ **AWS Windows EC2 Instances**  
✅ **Google Cloud Windows VMs**  

### Quick Start

1. **Create Windows Server** (2019/2022)
2. **Install Dependencies**: Python, Git, Node.js, MT5
3. **Clone Repository**: `git clone https://github.com/Mariosat15/CopyArena.git`
4. **Setup Backend**: `pip install -r requirements.txt`
5. **Configure MT5**: Enable API and automated trading
6. **Run Server**: `python app.py`

### Features

- **Real MT5 Integration**: Live trading data and account info
- **Multi-User Support**: Each user connects their own MT5 account
- **WebSocket Real-time Updates**: Live trade monitoring
- **Production Ready**: Windows services, SSL, monitoring

### Full Setup Guide

See `WINDOWS_DEPLOYMENT.md` for complete step-by-step instructions.

## Local Development

For local Windows development:
```bash
pip install -r requirements.txt
python app.py
```

**Note**: This application requires Windows environment for MetaTrader5 integration. 