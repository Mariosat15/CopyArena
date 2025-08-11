# CopyArena Windows Client

## 🚀 **Secure MT5 Integration - No EA Required!**

The CopyArena Windows Client replaces the traditional MetaTrader 5 Expert Advisor with a secure, standalone application that provides enhanced security and ease of use.

## ✨ **Key Features**

- **🔐 Enhanced Security**: Direct web login integration - no API key sharing
- **👤 User Verification**: Prevents cross-account API key abuse  
- **🖥️ User-Friendly GUI**: Easy setup with visual status monitoring
- **📊 Real-Time Sync**: Automatic data synchronization with CopyArena platform
- **📝 Comprehensive Logging**: Detailed logs for troubleshooting
- **⚙️ Configurable Settings**: Customizable update intervals and auto-connect

## 🛡️ **Security Improvements**

### **Previous EA Issues:**
- ❌ API keys could be shared between users
- ❌ No user verification
- ❌ Complex installation process
- ❌ Limited security controls

### **Windows Client Solutions:**
- ✅ **User-specific authentication** with web credentials
- ✅ **API key binding** to prevent unauthorized usage
- ✅ **User ID verification** ensures data goes to correct account
- ✅ **IP tracking** for additional security monitoring
- ✅ **Simple installation** - just run the executable

## 📋 **System Requirements**

- **Operating System**: Windows 10/11 (64-bit)
- **MetaTrader 5**: Any version with Python API support
- **Python** (if running script version): 3.8 or higher
- **Internet Connection**: Required for CopyArena platform communication

## 🚀 **Quick Start Guide**

### **Method 1: Executable (Recommended)**
1. Download `CopyArenaClient.exe` from your CopyArena profile
2. Run the executable
3. Enter your CopyArena web credentials
4. Enter your MT5 broker credentials
5. Click "Connect All"

### **Method 2: Python Script**
1. Install Python 3.8+
2. Install requirements: `pip install -r requirements.txt`
3. Run: `python copyarena_client.py`

## ⚙️ **Configuration**

### **CopyArena Web Credentials**
- **Server URL**: Your CopyArena server (default: http://localhost:8002)
- **Username**: Your CopyArena account username/email
- **Password**: Your CopyArena account password

### **MetaTrader 5 Credentials**
- **Login**: Your MT5 account number
- **Password**: Your MT5 account password  
- **Server**: Your broker's server name

### **Settings**
- **Update Interval**: How often to sync data (1-60 seconds)
- **Auto-Connect**: Automatically connect on startup

## 📊 **Interface Overview**

### **Connection Tab**
- Enter credentials for both CopyArena and MT5
- Connect/disconnect controls
- Save configuration

### **Status Tab**
- Real-time connection status
- Account information display
- Live data monitoring

### **Logs Tab**
- Detailed operation logs
- Error tracking
- Save logs to file

### **Settings Tab**
- Update interval configuration
- Auto-connect options
- Advanced settings

## 🔧 **Building from Source**

### **Create Executable**
```bash
# Using PyInstaller (Recommended)
pip install pyinstaller
./build_executable.bat

# Using cx_Freeze (Alternative)
pip install cx_Freeze
python setup.py build
```

### **Development**
```bash
# Install development dependencies
pip install -r requirements.txt

# Run in development mode
python copyarena_client.py
```

## 🐛 **Troubleshooting**

### **Connection Issues**
1. **Verify credentials** in both CopyArena and MT5 sections
2. **Check server URL** (include http:// or https://)
3. **Ensure MT5 is running** and logged in
4. **Check firewall/antivirus** settings

### **Authentication Errors**
- **Invalid web credentials**: Verify username/password on CopyArena website
- **MT5 connection failed**: Check broker server name and account details
- **Security violations**: Contact support if seeing user ID mismatch errors

### **Data Sync Issues**
- **No data appearing**: Check "Status" tab for connection status
- **Outdated information**: Adjust update interval in "Settings" tab
- **Missing trades**: Verify MT5 account has active positions/history

## 📝 **Log Files**

The client creates several log files for troubleshooting:
- `copyarena_client.log` - Main application log
- `copyarena_config.json` - Saved configuration (credentials not stored)

## 🔒 **Security Notes**

- **Passwords are NOT saved** in configuration files
- **API keys are managed automatically** through secure authentication
- **All communication** uses HTTPS when available
- **Local data** is minimal and non-sensitive

## 🆘 **Support**

If you encounter issues:
1. Check the **Logs tab** for error messages
2. Save logs using the "Save Logs" button
3. Contact CopyArena support with log files
4. Include your configuration (server URL, usernames - NO passwords)

## 🔄 **Migration from EA**

If you were previously using the MT5 Expert Advisor:
1. **Remove the old EA** from your MT5 charts
2. **Download and run** the new Windows Client
3. **Use the same CopyArena account** credentials
4. **Your trading data** will continue seamlessly

The Windows Client is more secure and easier to use than the previous EA system!

---

**CopyArena Windows Client v1.0**  
*Secure, Simple, Professional MT5 Integration*
