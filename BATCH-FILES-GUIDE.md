# Vector Dashboard - Quick Reference

## 🚀 Batch Files Guide

### First Time Setup
```bash
setup.bat           # Complete setup (Docker + Qdrant + Dependencies)
```

### Daily Use
```bash
start-all.bat       # Start all application services
stop-all.bat        # Stop all application services
```

### Qdrant Management
```bash
start-qdrant.bat    # Start Qdrant database
stop-qdrant.bat     # Stop Qdrant database
```

### Utilities
```bash
install-deps.bat    # Install/update all dependencies
```

## 📋 Common Issues

### "Docker Desktop is not running"
**Solution:**
1. Open Docker Desktop from Start Menu
2. Wait for it to fully start (whale icon in system tray)
3. Run the script again

Or let `setup.bat` handle it automatically!

### "Qdrant is not running"
**Solution:**
- Run: `start-qdrant.bat`
- Or let `start-all.bat` prompt you to start it

### "Port already in use"
**Solution:**
```bash
# Stop all services
stop-all.bat

# Check what's using the port (e.g., 5000)
netstat -ano | findstr :5000

# Kill the process (replace PID with actual process ID)
taskkill /F /PID <PID>
```

### Python or Node.js not found
**Solution:**
- Install Node.js: https://nodejs.org/
- Install Python 3.9+: https://www.python.org/
- Run `install-deps.bat` again

## 🔧 Configuration

### Qdrant API Key (Optional for local use)
Edit these files:
- `backend\.env` → Line 7: `QDRANT_API_KEY=your_key_here`
- `ai-service\.env` → Line 8: `QDRANT_API_KEY=your_key_here`

For local development, you can leave it empty or use any value.

## 🌐 Access Points

After running `start-all.bat`:
- **Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:5000
- **AI Service**: http://localhost:5001
- **Digital Twin**: http://localhost:5002
- **Qdrant**: http://localhost:6333/dashboard

## 📁 Project Structure

```
Vectors/
├── start-all.bat       # ⭐ Start all services
├── stop-all.bat        # Stop all services
├── setup.bat           # ⭐ Complete first-time setup
├── start-qdrant.bat    # Start Qdrant only
├── stop-qdrant.bat     # Stop Qdrant only
├── install-deps.bat    # Install dependencies
├── frontend/           # React dashboard
├── backend/           # Node.js API
├── ai-service/        # Python AI service
└── digital-twin/      # Python simulation
```

## 💡 Tips

1. **Always start Docker Desktop first** (or let setup.bat do it)
2. **Use setup.bat for first-time setup** - it does everything
3. **Use start-all.bat for daily use** - it's smart enough to check Qdrant
4. **Close terminal windows to stop services** or use stop-all.bat
5. **Qdrant data persists** in `qdrant_storage/` folder
