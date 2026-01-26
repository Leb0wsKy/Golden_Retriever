# Vector Database Dashboard

A full-stack dashboard application for managing vector databases with AI integration and digital twin simulation.

## Project Structure

```
Vectors/
├── frontend/           # React dashboard
├── backend/           # Node.js API server
├── ai-service/        # Python Flask AI service
├── digital-twin/      # Python digital twin simulation
└── docker-compose.yml # Docker configuration
```

## Features

- **Vector Database Management**: Create and manage Qdrant collections
- **AI-Powered Search**: Semantic search using sentence transformers
- **Real-time Dashboard**: Monitor performance metrics and statistics
- **Digital Twin Simulation**: Simulate and predict system behavior
- **Multi-Model Support**: Multiple AI models for embeddings and predictions

## Prerequisites

- Node.js 16+
- Python 3.9+
- Qdrant (running locally or cloud)
- npm or yarn

## Quick Start

### Windows Quick Start (Easiest)

**First Time Setup:**
```bash
# Run complete setup (installs everything)
setup.bat
```

**Daily Use:**
```bash
# Start all services (includes Qdrant check)
start-all.bat
```

**Manual Steps:**
1. **Start Docker Desktop** (if not running)
2. **Start Qdrant**:
   ```bash
   start-qdrant.bat
   ```
3. **Install dependencies** (first time only):
   ```bash
   install-deps.bat
   ```
4. **Configure API Key** (optional for local use): Edit `.env` files in `backend` and `ai-service` folders
5. **Start all services**:
   ```bash
   start-all.bat
   ```
6. **Access the dashboard**: http://localhost:3000

**Stop Everything:**
```bash
stop-all.bat      # Stop application services
stop-qdrant.bat   # Stop Qdrant database
```

### Manual Setup

### 1. Setup Qdrant

```bash
# Using Docker
docker pull qdrant/qdrant
docker run -p 6333:6333 qdrant/qdrant
```

### 2. Backend Setup

```bash
cd backend
npm install
# Edit .env file with your Qdrant API key
npm start
```

### 3. AI Service Setup

```bash
cd ai-service
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
# Edit .env file with your Qdrant API key
python app.py
```

### 4. Digital Twin Service Setup

```bash
cd digital-twin
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
python app.py
```

### 5. Frontend Setup

```bash
cd frontend
npm install
npm start
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- AI Service: http://localhost:5001
- Digital Twin: http://localhost:5002

## Configuration

### Backend (.env)
```
PORT=5000
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_api_key_here
AI_SERVICE_URL=http://localhost:5001
DIGITAL_TWIN_URL=http://localhost:5002
```

### AI Service (.env)
```
AI_SERVICE_PORT=5001
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_api_key_here
```

### Digital Twin (.env)
```
DIGITAL_TWIN_PORT=5002
```

## API Endpoints

### Backend API (Port 5000)
- `GET /api/health` - Health check
- `GET /api/stats` - System statistics
- `GET /api/collections` - List collections
- `POST /api/collections` - Create collection
- `POST /api/search` - Search vectors
- `GET /api/ai/models` - List AI models
- `POST /api/ai/embed` - Generate embeddings
- `GET /api/digital-twin/data` - Get simulation data

### AI Service (Port 5001)
- `GET /health` - Health check
- `GET /models` - List models
- `POST /embed` - Generate embedding
- `POST /embed_batch` - Batch embeddings
- `POST /predict` - Run prediction
- `POST /similarity` - Calculate similarity
- `POST /insert` - Insert vectors
- `POST /search_similar` - Search similar vectors

### Digital Twin (Port 5002)
- `GET /health` - Health check
- `GET /data` - Get current data
- `GET /history` - Get history
- `POST /start` - Start simulation
- `POST /stop` - Stop simulation
- `POST /reset` - Reset simulation
- `GET /scenarios` - List scenarios
- `POST /predict` - Predict performance

## Features Overview

### Dashboard
- Real-time statistics
- Performance metrics charts
- Activity monitoring
- System uptime tracking

### Vector Database
- Create and manage collections
- Semantic search functionality
- Vector count and dimension tracking
- Collection status monitoring

### AI Models
- Text embedding generation
- Batch processing
- Model predictions
- Similarity calculations

### Digital Twin
- Real-time simulation
- Multiple scenarios (normal, high load, stress test, failure)
- Performance prediction
- Adjustable parameters

## Technologies Used

- **Frontend**: React, Material-UI, Recharts, Axios
- **Backend**: Node.js, Express, Qdrant Client
- **AI Service**: Flask, Sentence Transformers, PyTorch
- **Digital Twin**: Flask, NumPy
- **Database**: Qdrant Vector Database

## License

MIT License
