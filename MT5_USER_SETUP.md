# MT5 Setup Guide for CopyArena Users

## 🎯 **How to Connect Your MT5 Account**

CopyArena connects to **your local MT5 terminal** running on your computer. This ensures complete security and privacy of your trading account.

### **📋 Prerequisites:**
- Windows computer with MT5 installed
- Active MT5 trading account with your broker
- Internet connection

---

## 🚀 **Step 1: Install MetaTrader 5**

### **Download MT5:**
1. Go to your broker's website
2. Download MT5 terminal
3. Install on your Windows computer
4. Login with your broker credentials

### **Popular Brokers with MT5:**
- **IC Markets**
- **Pepperstone** 
- **FXPRO**
- **Admiral Markets**
- **XM Global**

---

## 🔧 **Step 2: Enable MT5 Web API**

### **In MT5 Terminal:**
1. **Open MT5** → Go to **Tools** → **Options**
2. Click **"Expert Advisors"** tab
3. **Check these boxes:**
   - ✅ "Allow automated trading"
   - ✅ "Allow DLL imports"  
   - ✅ "Allow WebRequest"
   - ✅ "Enable web server" (if available)

### **Set Web API Port:**
1. Go to **Tools** → **Options** → **Expert Advisors**
2. Find **"WebRequest"** settings
3. Set port to **8080** (default)
4. Click **"OK"**

---

## 🌐 **Step 3: Install MT5 Web Bridge**

You need a small program that creates a web API for your MT5:

### **Option A: Download Pre-built Bridge**
1. Download `MT5WebBridge.exe` from CopyArena
2. Run as Administrator
3. It will connect to your MT5 terminal

### **Option B: Python Script (Advanced)**
```python
# Save as mt5_web_bridge.py
import MetaTrader5 as mt5
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/ping')
def ping():
    return jsonify({"status": "connected"})

@app.route('/api/account')
def get_account():
    if not mt5.initialize():
        return jsonify({"error": "MT5 not connected"}), 500
    
    account = mt5.account_info()
    if account is None:
        return jsonify({"error": "No account info"}), 500
    
    return jsonify({
        "login": account.login,
        "server": account.server,
        "name": account.name,
        "company": account.company,
        "currency": account.currency,
        "balance": account.balance,
        "equity": account.equity,
        "margin": account.margin,
        "free_margin": account.margin_free,
        "margin_level": account.margin_level,
        "profit": account.profit
    })

@app.route('/api/positions')
def get_positions():
    if not mt5.initialize():
        return jsonify({"error": "MT5 not connected"}), 500
    
    positions = mt5.positions_get()
    if positions is None:
        return jsonify([])
    
    result = []
    for pos in positions:
        result.append({
            "ticket": pos.ticket,
            "symbol": pos.symbol,
            "type": "BUY" if pos.type == 0 else "SELL",
            "volume": pos.volume,
            "price_open": pos.price_open,
            "price_current": pos.price_current,
            "sl": pos.sl,
            "tp": pos.tp,
            "profit": pos.profit,
            "swap": pos.swap,
            "comment": pos.comment,
            "time_open": pos.time
        })
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080)
```

### **Run the Bridge:**
```bash
# Install requirements
pip install MetaTrader5 flask flask-cors

# Run the bridge
python mt5_web_bridge.py
```

---

## 🔗 **Step 4: Connect to CopyArena**

### **In CopyArena Web App:**
1. **Go to** "MT5 Connection" page
2. **Click** "Test Connection"
3. **Should show:** ✅ "Connected to MT5"
4. **Your account info** will appear automatically

### **If Connection Fails:**
- ✅ MT5 terminal is running
- ✅ MT5WebBridge is running on port 8080
- ✅ Windows Firewall allows port 8080
- ✅ Antivirus not blocking the bridge

---

## 🔐 **Security & Privacy**

### **✅ Your Data Stays Safe:**
- **MT5 runs locally** on your computer
- **CopyArena connects via web** (no direct access)
- **Your broker credentials** never leave your computer
- **Only trading data** is shared (no passwords)

### **What CopyArena Can See:**
- ✅ Account balance, equity, margin
- ✅ Open positions and their P/L
- ✅ Trade history for analytics
- ❌ **Cannot see:** Login credentials, personal info
- ❌ **Cannot do:** Place trades without your permission

---

## 🚨 **Troubleshooting**

### **"MT5 Not Connected" Error:**
```
Solution:
1. Restart MT5 terminal
2. Restart MT5WebBridge
3. Check port 8080 is not blocked
4. Try different port (8081, 8082)
```

### **"CORS Error" in Browser:**
```
Solution:
1. Ensure MT5WebBridge includes CORS headers
2. Use the provided Python script
3. Or download the pre-built bridge
```

### **"Permission Denied" Error:**
```
Solution:
1. Run MT5WebBridge as Administrator
2. Add Windows Firewall exception
3. Check antivirus settings
```

### **Firewall Configuration:**
```powershell
# Allow port 8080 in Windows Firewall
New-NetFirewallRule -DisplayName "MT5 Web Bridge" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow
```

---

## 📱 **Mobile Trading**

### **Current Limitation:**
- Web bridge only works on Windows computers
- Mobile devices cannot run MT5 terminal

### **Planned Features:**
- Broker API integration (OANDA, FXPRO)
- Mobile-friendly broker connections
- Cloud-based trading accounts

---

## 🎯 **Final Checklist**

### **✅ Setup Complete When:**
- [ ] MT5 terminal installed and logged in
- [ ] Expert Advisors enabled in MT5 options
- [ ] MT5WebBridge running on port 8080
- [ ] CopyArena shows "Connected" status
- [ ] Account balance visible in web app
- [ ] Real-time trade updates working

**🎉 You're ready to use CopyArena with live MT5 data!**

---

## 📞 **Need Help?**

**Common Issues:**
- Connection problems → Check firewall and antivirus
- Missing trades → Restart MT5WebBridge  
- Slow updates → Reduce monitoring interval

**Contact Support:**
- Discord: [CopyArena Community]
- Email: support@copyarena.com
- Help Desk: In-app chat support 