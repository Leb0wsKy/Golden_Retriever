# Vector Dashboard (Qdrant + Live Train Alerts)

This repo is a small multi-service system:

1) a React dashboard UI
2) a Node/Express API
3) a Qdrant vector database (typically Qdrant Cloud)
4) optional Python services for embeddings (AI) and simulation (digital twin)

The “golden run” idea: store known incidents + expert solutions in Qdrant, then when a live incident occurs, embed the incident text and retrieve the most similar past incident to propose an actionable recommendation.

## Architecture

### High-level data flow

```
Transitland (live rail routes)  ───────────────┐
																							 ▼
																				 Backend API (Express)
																							 │
																							 │ detects anomalies
																							 ▼
																				 Alerts generator
																							 │
																							 │ embeds text (optional)
																							 ▼
AI Service (Flask, embeddings) ───► Qdrant (train_alerts vectors) ◄── seed “golden runs”
																							 │
																							 ▼
Frontend (React)  ◄────────────── /api/* responses (alerts, trains, collections)
```

### Components

- **Frontend** (`frontend/`)
	- React + MUI dashboard
	- Uses a dev proxy to the backend (`frontend/package.json` → `proxy: http://localhost:5000`)

- **Backend** (`backend/`)
	- Express API on `PORT` (default `5000`)
	- Talks to:
		- **Transitland API** for live rail route data
		- **Qdrant** for vector search / storage
		- **AI Service** (optional) for embeddings
		- **Digital Twin** (optional) for simulation endpoints

- **Qdrant modules + scripts** (`qdrant/`)
	- Node modules used by the backend (collection creation, similarity search, templates)
	- Includes a seeding script to bootstrap training incidents ("golden runs")

- **AI Service (optional)** (`ai-service/`)
	- Flask service providing `/embed` (384-d vectors via `all-MiniLM-L6-v2`)

- **Digital Twin (optional)** (`digital-twin/`)
	- Flask simulation service providing `/data`, `/start`, `/stop`, etc.

## Repository layout

```
backend/        Express API + routes (/api/*)
frontend/       React dashboard
qdrant/         Qdrant client config, collection helpers, alert similarity, seeding
ai-service/     Flask embeddings service (optional)
digital-twin/   Flask simulation service (optional)
start-all.bat   Starts backend + frontend (Windows)
stop-all.bat    Stops Node processes (Windows)
setup.bat       Installs backend + frontend dependencies
```

## Ports & URLs (defaults)

- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- AI Service (optional): http://localhost:5001
- Digital Twin (optional): http://localhost:5002

## Configuration

### Required environment variables (backend)

The backend reads environment variables from `backend/.env` (because the backend runs from the `backend/` directory).

Create `backend/.env` with at least:

```dotenv
PORT=5000

# Qdrant Cloud
QDRANT_URL=https://your-cluster-url.qdrant.io:6333
QDRANT_API_KEY=your_qdrant_api_key

# Transitland (required for live trains / live alerts)
TRANSITLAND_API_KEY=your_transitland_api_key
TRANSITLAND_BASE_URL=https://transit.land/api/v2

# Optional services
AI_SERVICE_URL=http://localhost:5001
DIGITAL_TWIN_URL=http://localhost:5002
```

Notes:
- If the AI service is not running, vector similarity will be degraded (the backend falls back to placeholder vectors).
- Keep API keys out of git. If you ever committed a real key, rotate it.

For Qdrant Cloud setup, see: `QDRANT-CLOUD-SETUP.md`.

## Workflows

### 1) Run the dashboard (Windows)

1. Install prerequisites:
	 - Node.js (16+ recommended)
	 - Python (3.9+ recommended) if you want the optional Python services
2. Configure `backend/.env` (see above)
3. Install JS dependencies:
	 ```powershell
	 .\setup.bat
	 ```
4. Start backend + frontend:
	 ```powershell
	 .\start-all.bat
	 ```
5. Open: http://localhost:3000

Stop everything:

```powershell
.\stop-all.bat
```

### 2) Seed “golden run” incidents into Qdrant

Seeding is what makes similarity search useful: it loads a small training set of incident texts + human-written solutions.

1. Start the backend (so the seed script can call its API)
2. Run:

```powershell
node .\qdrant\seed-alerts.js
```

This will populate the Qdrant collection named `train_alerts`.

### 3) Live alerts workflow (Transitland → anomalies → Qdrant → solution)

1. Ensure `TRANSITLAND_API_KEY` is set in `backend/.env`
2. Ensure Qdrant credentials are set in `backend/.env`
3. (Optional but recommended) start the AI service so embeddings are meaningful
4. Use the dashboard’s Alerts page, or call the API directly:

```powershell
Invoke-RestMethod http://localhost:5000/api/alerts/live
```

To understand the alert pipeline in detail, see:
- `HOW-ALERTS-WORK.md`
- `LIVE-ALERTS-INTEGRATION.md`

### 4) Optional: run AI Service (embeddings)

```powershell
cd .\ai-service
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

### 5) Optional: run Digital Twin service

```powershell
cd .\digital-twin
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The backend proxies digital-twin calls via `/api/digital-twin/*` (e.g. `/api/digital-twin/data`).

## Useful backend endpoints

- `GET /api/health`
- `GET /api/trains/live`
- `GET /api/alerts/live`
- `GET /api/ai/models` (requires AI service)
- `POST /api/ai/embed` (requires AI service)
- `GET /api/digital-twin/data` (requires digital-twin service)

## Troubleshooting

- **Qdrant errors**: confirm `QDRANT_URL` includes `:6333` and `QDRANT_API_KEY` is valid.
- **No live trains / alerts**: confirm `TRANSITLAND_API_KEY` is set.
- **AI endpoints failing**: start `ai-service/` or set `AI_SERVICE_URL` correctly.
- **Port already in use**: change `PORT` (backend) or free ports `3000/5000`.
