# Vector Database Dashboard

A full-stack dashboard application for managing vector databases with Qdrant Cloud integration and live train tracking.

## Project Structure

```
Vectors/
├── frontend/           # React dashboard
├── backend/           # Node.js API server
├── ai-service/        # Python Flask AI service (optional)
├── digital-twin/      # Python digital twin simulation (optional)
└── .env              # Environment configuration
```

## Features

- **Live Train Tracking**: Real-time train monitoring using Transitland API
- **Qdrant Cloud Integration**: Vector database management in the cloud
- **Interactive Dashboard**: Real-time maps and train data visualization
- **Multi-Network Support**: Track trains across multiple rail networks worldwide

## Prerequisites

- Node.js 16+ ([Download](https://nodejs.org/))
- Qdrant Cloud account (free tier available at [cloud.qdrant.io](https://cloud.qdrant.io))
- Transitland API key

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd Vectors

# Run setup to install dependencies
setup.bat
```

### 2. Configure Qdrant Cloud

1. Create account at [https://cloud.qdrant.io](https://cloud.qdrant.io)
2. Create a cluster and get your credentials
3. Update `.env` and `backend/.env` with your Qdrant Cloud URL and API key

See [QDRANT-CLOUD-SETUP.md](QDRANT-CLOUD-SETUP.md) for detailed instructions.

### 3. Start the Application

**Using the batch file (Windows):**
```bash
start-all.bat
```

**Or manually:**
```bash
# Terminal 1 - Backend
cd backend
npm start

# Terminal 2 - Frontend
cd frontend
npm start
```

### 4. Access the Dashboard

Open your browser to: **http://localhost:3000**

**Stop Everything:**
```bash
stop-all.bat
```

## Environment Configuration

Make sure these files are configured with your Qdrant Cloud credentials:

**`.env` (root directory):**
```bash
QDRANT_URL=https://your-cluster-url.qdrant.io
QDRANT_API_KEY=your_api_key
TRANSITLAND_API_KEY=your_transitland_key
```

**`backend/.env`:**
```bash
PORT=5000
QDRANT_URL=https://your-cluster-url.qdrant.io
QDRANT_API_KEY=your_api_key
TRANSITLAND_API_KEY=your_transitland_key
TRANSITLAND_BASE_URL=https://transit.land/api/v2
```

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
