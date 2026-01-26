# Vector Dashboard - Quick Start Guide

## Installation & Setup

### Option 1: Docker (Recommended)

1. Copy `.env.example` to `.env` and add your Qdrant API key:
```bash
cp .env.example .env
# Edit .env and add your QDRANT_API_KEY
```

2. Start all services:
```bash
docker-compose up -d
```

3. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- AI Service: http://localhost:5001
- Digital Twin: http://localhost:5002
- Qdrant: http://localhost:6333

### Option 2: Manual Setup

#### 1. Start Qdrant
```bash
docker run -p 6333:6333 qdrant/qdrant
```

#### 2. Backend
```bash
cd backend
npm install
# Copy .env.example to .env and configure
npm start
```

#### 3. AI Service
```bash
cd ai-service
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python app.py
```

#### 4. Digital Twin
```bash
cd digital-twin
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python app.py
```

#### 5. Frontend
```bash
cd frontend
npm install
npm start
```

## Usage Examples

### 1. Create a Collection
Navigate to "Vector Database" → Click "Create Collection"

### 2. Generate Embeddings
Navigate to "AI Models" → Enter text → Click "Generate Embedding"

### 3. Search Vectors
Navigate to "Vector Database" → Enter search query → Click "Search"

### 4. Run Digital Twin
Navigate to "Digital Twin" → Configure parameters → Click "Start Simulation"

## Configuration

Edit the `.env` files in each service directory to configure:
- Qdrant URL and API key
- Service ports
- Model settings
- Simulation parameters

## Troubleshooting

### Qdrant Connection Issues
- Ensure Qdrant is running on port 6333
- Verify QDRANT_API_KEY in .env files
- Check firewall settings

### AI Service Errors
- Verify Python dependencies are installed
- Check if models are downloading correctly
- Ensure sufficient disk space for models

### Frontend Not Loading
- Clear browser cache
- Check if backend is running on port 5000
- Verify proxy settings in frontend/package.json
