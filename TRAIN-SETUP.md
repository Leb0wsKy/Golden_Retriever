# Train Network Monitoring Platform

## Setup Instructions

### 1. Add Your Transitland API Key

Edit [backend/.env](backend/.env) and add your Transitland API key:

```
TRANSITLAND_API_KEY=your_actual_api_key_here
```

### 2. Install Frontend Dependencies

The new map features require additional packages:

```bash
cd frontend
npm install react-leaflet leaflet
cd ..
```

### 3. Start the Application

```bash
# Make sure Docker Desktop is running
# Then start all services
quick-start.bat
```

### 4. Access the Dashboard

Open http://localhost:3000

You'll see:
- **Live train positions on an interactive map**
- **Real-time status cards** showing active trains, speeds, and delays
- **Train list** with detailed information
- **Route visualization** on the map

## Transitland API

The app now uses the Transitland API to fetch real-time train data. 

If you haven't added your API key yet, the system will show **demo data** so you can still see how everything works.

### Get a Transitland API Key

1. Go to https://www.transit.land/
2. Sign up for an account
3. Get your API key from the dashboard
4. Add it to `backend/.env`

### API Features Used

- Live vehicle positions
- Route information
- Real-time status updates
- Speed and delay data

## What Changed

### Frontend
- New interactive map using Leaflet
- Custom train icons and markers
- Real-time position updates every 10 seconds
- Route visualization
- Status indicators (on-time, delayed)

### Backend
- New `/api/trains/live` endpoint
- Transitland API integration
- Demo data fallback if no API key

### UI Updates
- Changed from "Vector Database Dashboard" to "Train Network Monitoring Platform"
- Train-focused statistics and metrics
- Map-centric layout
