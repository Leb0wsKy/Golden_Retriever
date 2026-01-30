# 🚂 Complete ML Integration Workflow

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                             │
│         Dashboard with Pre-Conflict Alerts                  │
│    (Shows both ML predictions & pattern-based alerts)       │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (Port 5000)                      │
│             Node.js/Express API Gateway                     │
│    - Proxies requests to Digital Twin                       │
│    - Serves active trains data                              │
│    - Routes /api/digital-twin/ml/predictions                │
└────────────┬────────────────────────┬──────────────────────┘
             │                        │
             ↓                        ↓
┌────────────────────────┐  ┌─────────────────────────────────┐
│   DIGITAL TWIN         │  │  ML INTEGRATION SERVICE         │
│   (Port 5002)          │  │  (Python Background Monitor)     │
│   FastAPI              │←─┤                                  │
│                        │  │  Every 30 seconds:               │
│  • /api/v1/ml/         │  │  1. Fetch active trains          │
│    predictions (POST)  │  │  2. Group by network             │
│  • /api/v1/ml/         │  │  3. Call ML API                  │
│    predictions (GET)   │  │  4. Store in Digital Twin        │
│                        │  └──────────────┬───────────────────┘
│  Stores predictions in │                 │
│  Qdrant with embeddings│                 ↓
└────────────┬───────────┘  ┌─────────────────────────────────┐
             │              │     ML PREDICTION API           │
             ↓              │     (Port 5003)                 │
┌─────────────────────────┐│     Flask Server                │
│   QDRANT VECTOR DB      ││                                  │
│   (Cloud/Local)         ││  • Loads trained model           │
│                         ││  • Aggregates train data         │
│  Collection:            ││  • Predicts conflict probability │
│  pre_conflict_memory    ││  • Returns risk level            │
│                         ││  • Identifies factors            │
│  Stores:                │└──────────────────────────────────┘
│  • ML predictions       │
│  • Pattern-based alerts │
│  • Historical conflicts │
│  • Embeddings for search│
└─────────────────────────┘
```

## 🔄 Data Flow

### 1. **ML Prediction Generation**

```
Active Trains → ML Integration Service → ML API
                                          ↓
                                    Predict Conflict
                                          ↓
                            {probability: 0.67, risk: HIGH}
```

### 2. **Storage in Digital Twin**

```
ML Prediction → Digital Twin /api/v1/ml/predictions
                      ↓
              Generate Embedding
                      ↓
              Store in Qdrant
                      ↓
         pre_conflict_memory collection
```

### 3. **Frontend Retrieval**

```
Frontend → Backend → Digital Twin /api/v1/ml/predictions
                            ↓
                    Query Qdrant
                            ↓
                Return ML predictions + pattern alerts
                            ↓
            Display in Pre-Conflict Alerts section
```

## 📦 Components Integration

### 1. ML Prediction API (`ai-service/ml_prediction_api.py`)

**Purpose:** Serves the trained ML model via REST API

**Endpoints:**
- `POST /api/ml/analyze-network` - Analyze live network state
- `GET /api/ml/health` - Health check
- `GET /api/ml/model-info` - Model metadata

**Flow:**
```python
Train Data → Aggregate to Network Level → Predict → Return {
    prediction: true/false,
    probability: 0.67,
    risk_level: "HIGH",
    contributing_factors: [...],
    recommended_action: "..."
}
```

### 2. ML Integration Service (`ai-service/ml_integration_service.py`)

**Purpose:** Monitors networks and automatically generates ML predictions

**Process:**
```
1. Fetch active trains from backend every 30s
2. Group trains by network_id
3. For each network:
   a. Call ML API to predict conflict
   b. If conflict predicted (probability > 40%):
      - Store in Digital Twin via /api/v1/ml/predictions
      - Digital Twin stores in Qdrant
      - Frontend displays alert
```

**Logging:**
```
[14:30:00] Iteration 42
----------------------------------------
Found 1,247 active trains
Analyzing 15 networks

  Network: FS (386 trains)
    Probability: 67.3%
    Risk Level: HIGH
    ⚠️  CONFLICT PREDICTED!
    ✓ ML prediction stored in Qdrant (ID: ml-pred-1706472823.45)
```

### 3. Digital Twin ML Endpoints (`digital-twin/app/api/routes/ml_predictions.py`)

**New Routes Added:**

#### `POST /api/v1/ml/predictions`
Stores ML prediction in Qdrant:
```python
{
    "network_id": "FS",
    "conflict_probability": 0.67,
    "risk_level": "HIGH",
    "contributing_factors": [
        "High anomaly rate (35%)",
        "Significant delays (22%)"
    ],
    ...
}
```

**Process:**
1. Receives ML prediction
2. Generates text embedding
3. Stores in `pre_conflict_memory` collection
4. Returns confirmation

#### `GET /api/v1/ml/predictions`
Retrieves ML predictions from Qdrant:
```
Query params:
- limit: max results (default 50)
- network_id: filter by network
- min_probability: minimum threshold

Returns: Array of ML prediction alerts
```

### 4. Backend Proxy (`backend/server.js`)

**Added Routes:**
```javascript
POST /api/digital-twin/ml/predictions
GET  /api/digital-twin/ml/predictions
```

Proxies requests to Digital Twin API.

### 5. Frontend Component (`frontend/src/components/PreConflictAlerts.js`)

**Updated to:**
- Fetch both pattern-based alerts AND ML predictions
- Combine into single alert list
- Display source (ml_model vs pattern_matching)
- Show risk levels with color coding

**Visual Indicators:**
- 🔴 CRITICAL (≥80% probability)
- 🟠 HIGH (≥60% probability)
- 🟡 MEDIUM (≥40% probability)

## 🚀 Complete Startup Sequence

### Terminal 1: Start All Core Services
```bash
.\start-all.bat
```
This starts:
- Backend (port 5000)
- Digital Twin (port 5002)
- Frontend (port 3000)
- AI Service (port 5001)

### Terminal 2: Start ML Prediction API
```bash
.\start-ml-api.bat
```
Loads model and serves on port 5003

### Terminal 3: Start ML Integration Service
```bash
.\start-ml-integration.bat
```
Begins monitoring and generating predictions

## ✅ Verification Steps

### 1. Check ML API is Running
```bash
curl http://localhost:5003/api/ml/health
```

Expected:
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

### 2. Test ML Integration
```bash
python ai-service/test_ml_api.py
```

### 3. Check Qdrant Storage
```bash
curl http://localhost:5000/api/digital-twin/ml/predictions?limit=5
```

Should return recent ML predictions.

### 4. View in Frontend
1. Open http://localhost:3000
2. Navigate to Dashboard
3. Check **Pre-Conflict Alerts** section
4. Should see alerts with source "ML Model" or "Pattern Matching"

## 📊 Qdrant Integration Details

### Collection: `pre_conflict_memory`

**Stores:**
- ML predictions from the model
- Pattern-based preventive alerts
- Historical pre-conflict states

**Structure:**
```javascript
{
  id: "uuid",
  vector: [384-dimensional embedding],
  payload: {
    prediction_id: "ml-pred-xxx",
    network_id: "FS",
    source: "ml_prediction",
    probability: 0.67,
    risk_level: "HIGH",
    contributing_factors: "...",
    detected_at: "2026-01-30T14:30:00Z",
    ...
  }
}
```

**Embedding Generation:**
Text description of network state → SentenceTransformer → 384d vector → Stored

**Benefits:**
- Semantic search over predictions
- Find similar historical patterns
- Analyze trends over time
- Combine ML + pattern-based alerts

## 🎯 Use Cases in Production

### 1. Real-Time Monitoring
```
Every 30s → Check all networks → Predict conflicts → Alert operators
```

### 2. Historical Analysis
```
Query Qdrant → "Show all HIGH risk predictions for network FS"
              → Analyze patterns leading to conflicts
```

### 3. Similarity Search
```
Current network state → Generate embedding → Find similar past states
                                           → See what happened
                                           → Preventive action
```

### 4. Continuous Learning
```
ML Prediction → Actual Outcome → Feedback Loop → Model Improvement
```

## 🔧 Configuration

### Environment Variables

**Backend (.env):**
```
DIGITAL_TWIN_URL=http://localhost:5002
```

**Digital Twin (.env):**
```
QDRANT_URL=your-qdrant-url
QDRANT_API_KEY=your-api-key
```

### Tuning Parameters

**ML Integration Service (`ml_integration_service.py`):**
```python
SCAN_INTERVAL = 30  # seconds between scans
MIN_PROBABILITY_THRESHOLD = 0.4  # alert threshold
```

**Digital Twin ML Routes:**
```python
DEFAULT_LIMIT = 50  # max predictions returned
```

## 📈 Monitoring

### Logs to Watch

**ML Integration Service:**
```
[14:30:00] ✓ Created 3 pre-conflict alerts
[14:30:30] Network: FS (386 trains)
[14:30:30]   ⚠️  CONFLICT PREDICTED!
```

**Digital Twin:**
```
✅ ML prediction ml-pred-1706472823.45 stored in Qdrant (point: uuid)
```

**Backend:**
```
POST /api/digital-twin/ml/predictions 200
GET /api/digital-twin/ml/predictions 200
```

## 🐛 Troubleshooting

### No ML Predictions Appearing

1. Check ML API is running: `curl http://localhost:5003/api/ml/health`
2. Check ML Integration Service logs
3. Verify Digital Twin is accessible
4. Check Qdrant connection in Digital Twin logs

### Predictions Not in Frontend

1. Check backend proxy is running
2. Verify endpoint: `curl http://localhost:5000/api/digital-twin/ml/predictions`
3. Check browser console for errors
4. Verify PreConflictAlerts component is fetching both endpoints

### Qdrant Storage Issues

1. Check Digital Twin .env has correct QDRANT_URL and QDRANT_API_KEY
2. Verify collection exists: check Qdrant dashboard
3. Check embedding service is generating vectors

## 🎉 Success Indicators

When fully integrated, you should see:

✅ ML API serving predictions (port 5003)  
✅ Integration service monitoring networks every 30s  
✅ Predictions stored in Qdrant `pre_conflict_memory`  
✅ Backend proxying ML endpoints  
✅ Frontend displaying ML alerts with 🤖 icon  
✅ Alerts color-coded by severity (🔴🟠🟡)  
✅ Both ML and pattern-based alerts in one view  

---

**The ML model is now fully integrated into your Golden Retriever platform!** 🚂✨
