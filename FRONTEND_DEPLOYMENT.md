# CopyArena Frontend Deployment Guide

## 🌐 Frontend Deployment for Windows Cloud Servers

The CopyArena frontend is designed to work seamlessly with Windows cloud deployments, automatically detecting the environment and configuring API/WebSocket connections accordingly.

## 📋 **Deployment Options**

### **Option 1: Static Build Deployment** ⭐ (Recommended)
Deploy the built frontend on a separate CDN/static hosting service while the backend runs on Windows server.

**Supported Static Hosts:**
- **Vercel** (Recommended)
- **Netlify**
- **Cloudflare Pages**
- **GitHub Pages**
- **AWS S3 + CloudFront**

### **Option 2: Same Windows Server**
Serve the frontend from the same Windows server as the backend.

### **Option 3: Hybrid CDN Setup**
Frontend on CDN, backend on Windows cloud, with proper CORS configuration.

---

## 🚀 **Option 1: Static Build Deployment (Vercel)**

### **Step 1: Build Frontend Locally**
```bash
# Install dependencies
npm install

# Build for production
npm run build
```

### **Step 2: Deploy to Vercel**
```bash
# Install Vercel CLI
npm i -g vercel

# Login to Vercel
vercel login

# Deploy (from project root)
vercel --prod
```

**Vercel Configuration** (`vercel.json`):
```json
{
  "name": "copyarena-frontend",
  "framework": "vite",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/index.html"
    }
  ],
  "env": {
    "VITE_API_BASE_URL": "https://your-windows-server.com"
  }
}
```

### **Step 3: Configure Backend URL**
Update the backend URL in production:

**Environment Variables:**
```bash
# Add to your deployment platform
VITE_API_BASE_URL=https://your-windows-server.digitalocean.com
VITE_WS_BASE_URL=wss://your-windows-server.digitalocean.com
```

---

## 🖥️ **Option 2: Same Windows Server Deployment**

### **Step 1: Build Frontend on Windows Server**
```powershell
# On your Windows Server (via RDP)
cd C:\CopyArena

# Install Node.js dependencies
npm install

# Build for production
npm run build
```

### **Step 2: Serve Static Files**

**Method A: Using Python Simple Server**
```powershell
cd dist
python -m http.server 3000
```

**Method B: Using IIS (Recommended for Production)**
```powershell
# Install IIS
Enable-WindowsOptionalFeature -Online -FeatureName IIS-WebServerRole, IIS-WebServer, IIS-CommonHttpFeatures, IIS-HttpErrors, IIS-HttpRedirect, IIS-ApplicationDevelopment, IIS-NetFxExtensibility45, IIS-HealthAndDiagnostics, IIS-HttpLogging, IIS-Security, IIS-RequestFiltering, IIS-Performance, IIS-WebServerManagementTools, IIS-ManagementConsole, IIS-IIS6ManagementCompatibility, IIS-Metabase, IIS-ASPNET45

# Copy dist folder to IIS
Copy-Item -Recurse -Force .\dist\* C:\inetpub\wwwroot\

# Configure IIS site
# Use IIS Manager to configure site on port 80/443
```

**Method C: Using Node.js Server**
```powershell
# Install serve globally
npm install -g serve

# Serve static files
serve -s dist -l 3000
```

### **Step 3: Configure Windows Firewall**
```powershell
# Allow frontend port
New-NetFirewallRule -DisplayName "CopyArena Frontend" -Direction Inbound -Protocol TCP -LocalPort 3000 -Action Allow

# Allow HTTP/HTTPS for IIS
New-NetFirewallRule -DisplayName "HTTP" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
New-NetFirewallRule -DisplayName "HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

---

## 🔧 **Frontend Configuration**

### **Dynamic API Configuration**
The frontend automatically detects the environment:

**`src/lib/api.ts`** (Already configured):
```typescript
const isProduction = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'

const API_BASE_URL = isProduction 
  ? `${window.location.protocol}//${window.location.host}:8001`  // Production
  : 'http://127.0.0.1:8001'  // Development
```

### **WebSocket Configuration**
**`src/hooks/useWebSocket.ts`** (Already configured):
```typescript
const isProduction = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1'
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const wsHost = isProduction ? `${window.location.hostname}:8001` : '127.0.0.1:8001'
```

### **Environment Variables**
**For Production Builds:**
```bash
# .env.production
VITE_API_BASE_URL=https://your-server.com:8001
VITE_WS_BASE_URL=wss://your-server.com:8001
```

---

## 🌍 **Domain & SSL Configuration**

### **Step 1: Domain Setup**
1. Point your domain to the Windows server IP
2. Configure A records:
   ```
   A    @              YOUR_SERVER_IP
   A    www            YOUR_SERVER_IP
   A    api            YOUR_SERVER_IP  (if using subdomain)
   ```

### **Step 2: SSL Certificate**
```powershell
# Install Certbot on Windows
choco install certbot -y

# Generate SSL certificate
certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Configure IIS with SSL certificate
# Import certificate to IIS and bind to site
```

### **Step 3: Update Backend for HTTPS**
**`backend/app.py`**:
```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        ssl_keyfile="/path/to/private.key",
        ssl_certfile="/path/to/certificate.crt"
    )
```

---

## 🔐 **CORS Configuration**

### **Backend CORS Setup**
**`backend/app.py`** (Already configured):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**For Production, specify exact origins:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://www.yourdomain.com",
        "https://copyarena.vercel.app"  # If using Vercel
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

---

## 📱 **Progressive Web App (PWA)**

### **Enable PWA Features**
**`vite.config.ts`**:
```typescript
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}']
      },
      manifest: {
        name: 'CopyArena Trading Platform',
        short_name: 'CopyArena',
        description: 'Professional Copy Trading Platform',
        theme_color: '#000000',
        icons: [
          {
            src: 'icon-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          }
        ]
      }
    })
  ]
})
```

---

## 🚀 **Production Deployment Checklist**

### **✅ Frontend Checklist:**
- [ ] Build completed successfully (`npm run build`)
- [ ] Static files served (IIS/CDN/Static hosting)
- [ ] API base URL configured for production
- [ ] WebSocket URL configured for production
- [ ] Domain pointing to server
- [ ] SSL certificate installed and configured
- [ ] CORS configured for production domains
- [ ] Error handling and fallbacks tested
- [ ] Mobile responsiveness verified
- [ ] PWA features working (optional)

### **✅ Integration Checklist:**
- [ ] Frontend can reach backend API (test `/api/health`)
- [ ] WebSocket connection established
- [ ] User registration/login working
- [ ] MT5 connection from frontend working
- [ ] Real-time updates functioning
- [ ] Trading data displaying correctly
- [ ] Error messages showing properly

---

## 🔧 **Troubleshooting**

### **Common Issues:**

**1. API Connection Failed**
```
Error: Network Error / CORS Error
```
**Solution**: Check CORS configuration and API URL

**2. WebSocket Connection Failed**
```
Error: WebSocket connection failed
```
**Solution**: Verify WebSocket URL and firewall rules

**3. SSL Mixed Content**
```
Error: Mixed Content (HTTP over HTTPS)
```
**Solution**: Ensure all API calls use HTTPS in production

**4. Authentication Issues**
```
Error: 401 Unauthorized
```
**Solution**: Check token handling in API interceptors

### **Debug Commands:**
```javascript
// Test API connection
console.log('API Base URL:', import.meta.env.VITE_API_BASE_URL || 'auto-detected')

// Test WebSocket
const ws = new WebSocket('ws://your-server.com:8001/ws/user/1')
ws.onopen = () => console.log('WebSocket connected')
```

---

## 🌟 **Best Practices**

1. **Use CDN for Static Assets**: Deploy frontend to Vercel/Netlify for better performance
2. **Separate Domains**: Use subdomain for API (api.yourdomain.com)
3. **Enable Compression**: Configure gzip/brotli in IIS or CDN
4. **Cache Management**: Set proper cache headers for static assets
5. **Error Boundaries**: Implement React error boundaries for graceful failures
6. **Monitoring**: Add analytics and error tracking (Sentry, LogRocket)

**The frontend is now ready for production deployment with real MT5 integration!** 🚀 