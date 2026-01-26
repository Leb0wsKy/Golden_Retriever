# Quick Start Guide

## The Easy Way

1. **Start Docker Desktop manually** from the Start Menu
2. Wait for Docker to show "Docker Desktop is running" (whale icon in system tray)
3. Run:
   ```bash
   quick-start.bat
   ```

This will:
- Start or create Qdrant container automatically
- Install dependencies if needed
- Start all services
- Open the dashboard

## Alternative: Step by Step

If quick-start.bat has issues, do it manually:

1. **Start Docker Desktop** (from Start Menu, wait for it to fully load)

2. **Start Qdrant manually**:
   ```bash
   docker run -d --name qdrant-vector-db -p 6333:6333 qdrant/qdrant:latest
   ```

3. **Install dependencies** (first time only):
   ```bash
   install-deps.bat
   ```

4. **Start services**:
   ```bash
   start-all.bat
   ```

## Troubleshooting

### "Docker Desktop is not running"
- Open Docker Desktop from Start Menu
- Wait 30-60 seconds for it to fully start
- Look for whale icon in system tray
- Run the script again

### "Failed to start Qdrant"
Try manually:
```bash
# Remove any existing container
docker rm -f qdrant-vector-db

# Start fresh
docker run -d --name qdrant-vector-db -p 6333:6333 qdrant/qdrant:latest

# Check if it's running
docker ps
```

### Services won't start
Make sure you have:
- Node.js installed: https://nodejs.org/
- Python 3.9+ installed: https://www.python.org/

Then run: `install-deps.bat`
