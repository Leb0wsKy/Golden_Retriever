# 🦮 Golden Retriever

**AI-Powered Rail Conflict Resolution System**

Golden Retriever is an intelligent system that recommends resolution strategies for rail network conflicts using vector similarity search, digital twin simulation, and continuous learning from real-world outcomes.

[![Tests](https://img.shields.io/badge/tests-247%20passing-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688)]()
[![Qdrant](https://img.shields.io/badge/Qdrant-Cloud-ff6b6b)]()

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Architecture](#-architecture)
- [Key Features](#-key-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [How It Works](#-how-it-works)
- [Feedback Loop](#-feedback-loop)
- [Testing](#-testing)
- [Project Structure](#-project-structure)
- [Technology Stack](#-technology-stack)

---

## 🎯 Overview

Rail networks face operational conflicts daily—platform double-bookings, headway violations, track blockages, and capacity overloads. Golden Retriever helps operators resolve these conflicts by:

1. **Finding Similar Historical Cases** - Vector search in Qdrant finds past conflicts that resemble the current situation
2. **Simulating Outcomes** - A digital twin predicts how each resolution strategy would perform
3. **Ranking Recommendations** - Combines historical evidence with simulation to rank strategies
4. **Learning from Feedback** - Stores verified outcomes as "golden runs" to improve future recommendations

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GOLDEN RETRIEVER                                │
│                    AI-Powered Rail Conflict Resolution                       │
└─────────────────────────────────────────────────────────────────────────────┘

                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI REST API                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ POST /conflicts │  │ POST /feedback  │  │ GET /recommendations/metrics│  │
│  │   /generate     │  │                 │  │                             │  │
│  │   /analyze      │  │ Submit outcome  │  │ Learning metrics            │  │
│  │                 │  │ for learning    │  │ Strategy performance        │  │
│  └────────┬────────┘  └────────┬────────┘  └─────────────────────────────┘  │
└───────────┼─────────────────────┼───────────────────────────────────────────┘
            │                     │
            ▼                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SERVICE LAYER                                       │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    RECOMMENDATION ENGINE                              │   │
│  │                                                                       │   │
│  │   1. Embed conflict  ──▶  2. Search similar  ──▶  3. Simulate        │   │
│  │                                                                       │   │
│  │   4. Score & Rank    ──▶  5. Generate explanations                   │   │
│  │                                                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   EMBEDDING     │  │   DIGITAL TWIN  │  │      FEEDBACK LOOP          │  │
│  │    SERVICE      │  │   SIMULATOR     │  │        SERVICE              │  │
│  │                 │  │                 │  │                             │  │
│  │ all-MiniLM-L6-v2│  │ Rule-based      │  │ • Compare pred vs actual   │  │
│  │ 384 dimensions  │  │ simulation      │  │ • Store golden runs        │  │
│  │                 │  │ scoring         │  │ • Track metrics            │  │
│  └────────┬────────┘  └─────────────────┘  └────────────┬────────────────┘  │
│           │                                              │                   │
└───────────┼──────────────────────────────────────────────┼───────────────────┘
            │                                              │
            ▼                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                         │
│                                                                              │
│  ┌─────────────────────────────────────┐  ┌──────────────────────────────┐  │
│  │          QDRANT CLOUD               │  │      IN-MEMORY STORES        │  │
│  │                                     │  │                              │  │
│  │  ┌─────────────────────────────┐   │  │  • Conflict Store            │  │
│  │  │     conflict_memory         │   │  │  • Feedback Store            │  │
│  │  │                             │   │  │  • Metrics Store             │  │
│  │  │  • Historical conflicts    │   │  │  • Golden Runs               │  │
│  │  │  • Golden runs (verified)  │   │  │                              │  │
│  │  │  • Resolution outcomes     │   │  │                              │  │
│  │  └─────────────────────────────┘   │  └──────────────────────────────┘  │
│  │                                     │                                    │
│  │  ┌─────────────────────────────┐   │                                    │
│  │  │   pre_conflict_memory       │   │                                    │
│  │  │                             │   │                                    │
│  │  │  • Pre-conflict states     │   │                                    │
│  │  │  • Pattern recognition     │   │                                    │
│  │  └─────────────────────────────┘   │                                    │
│  └─────────────────────────────────────┘                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ CONFLICT │───▶│  EMBED   │───▶│  SEARCH  │───▶│ SIMULATE │───▶│  RANK    │
│  INPUT   │    │          │    │          │    │          │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                     │               │               │               │
                     ▼               ▼               ▼               ▼
               ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
               │ 384-dim  │   │ Similar  │   │ Outcome  │   │ Ranked   │
               │ vector   │   │ conflicts│   │ scores   │   │ recs     │
               └──────────┘   └──────────┘   └──────────┘   └──────────┘
```

### Layer Responsibilities

| Layer | Components | Purpose |
|-------|------------|---------|
| **API Layer** | FastAPI routes | Request handling, validation, HTTP interface |
| **Service Layer** | Embedding, Qdrant, Simulator, Recommender, Feedback | Business logic, orchestration |
| **Data Layer** | Qdrant Cloud, In-memory stores | Persistence, vector search |

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **Vector Similarity Search** | Find historical conflicts similar to the current situation using Qdrant |
| **Digital Twin Simulation** | Predict resolution outcomes based on conflict characteristics |
| **Continuous Learning** | Feedback loop stores verified outcomes to improve future recommendations |
| **Explainable AI** | Every recommendation includes human-readable explanations |
| **Real-time API** | FastAPI endpoints for conflict analysis and recommendations |
| **Metrics Dashboard** | Track prediction accuracy and strategy effectiveness |

### Conflict Types Supported

| Type | Description |
|------|-------------|
| `platform_conflict` | Multiple trains assigned to same platform |
| `headway_violation` | Insufficient time between trains on same track |
| `track_blockage` | Section blocked by maintenance or incident |
| `capacity_overflow` | Station/junction exceeds capacity limits |
| `crew_unavailability` | Missing or delayed crew assignment |

### Resolution Strategies

| Strategy | When Used |
|----------|-----------|
| `platform_change` | Reassign train to different platform |
| `reroute` | Send train via alternative route |
| `hold_train` | Delay departure until conflict clears |
| `speed_adjustment` | Modify train speed to create gaps |
| `cancel_service` | Remove train from schedule |
| `combine_services` | Merge multiple trains |

---

## 🚀 Installation

### Prerequisites

- Python 3.10+
- Qdrant Cloud account (or local Qdrant instance)

### Setup

```bash
# Clone the repository
git clone https://github.com/your-org/golden-retriever.git
cd golden-retriever

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Qdrant credentials
```

### Environment Variables

```env
# Qdrant Configuration
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-api-key

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
```

### Local Qdrant (Alternative)

```bash
# Using Docker
docker run -p 6333:6333 qdrant/qdrant
```

---

## 🏃 Quick Start

### Start the Server

```bash
# Development (with auto-reload)
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Generate Test Conflicts

```bash
curl -X POST http://localhost:8000/api/v1/conflicts/generate \
  -H "Content-Type: application/json" \
  -d '{"count": 10}'
```

### Analyze a Conflict

```bash
curl -X POST http://localhost:8000/api/v1/conflicts/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "conflict_type": "platform_conflict",
    "severity": "high",
    "station": "London Kings Cross",
    "time_of_day": "morning_peak",
    "affected_trains": ["IC101", "RE202"],
    "description": "Platform 5 double-booked for arrivals"
  }'
```

### Get Recommendations

```bash
curl http://localhost:8000/api/v1/conflicts/{conflict_id}/recommendations
```

### Submit Feedback

```bash
curl -X POST http://localhost:8000/api/v1/recommendations/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "conflict_id": "conf-abc123",
    "strategy_applied": "platform_change",
    "outcome": "success",
    "actual_delay_after": 3,
    "predicted_outcome": "success",
    "predicted_delay_after": 5
  }'
```

---

## 📚 API Reference

### Conflicts

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/conflicts/generate` | POST | Generate synthetic conflicts |
| `/api/v1/conflicts/analyze` | POST | Analyze a conflict and find similar cases |
| `/api/v1/conflicts/{id}` | GET | Get conflict details |
| `/api/v1/conflicts/{id}/recommendations` | GET | Get ranked recommendations |

### Recommendations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/recommendations/` | POST | Quick recommendations (no storage) |
| `/api/v1/recommendations/feedback` | POST | Submit resolution outcome |
| `/api/v1/recommendations/metrics` | GET | Get learning metrics |
| `/api/v1/recommendations/metrics/strategy/{name}` | GET | Strategy-specific metrics |
| `/api/v1/recommendations/golden-runs` | GET | List verified outcomes |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc documentation |

---

## 🔄 How It Works

### 1. Conflict Analysis

```python
# A new conflict arrives
conflict = {
    "type": "platform_conflict",
    "station": "King's Cross",
    "severity": "high",
    "time_of_day": "morning_peak"
}

# System embeds the conflict description
embedding = embed("Platform conflict at King's Cross during morning peak...")
# Result: [0.123, -0.456, 0.789, ...] (384 dimensions)
```

### 2. Similarity Search

```python
# Search Qdrant for similar historical conflicts
similar = qdrant.search(embedding, limit=10)

# Returns:
# [
#   {id: "hist-1", score: 0.95, resolution: "platform_change", outcome: "success"},
#   {id: "hist-2", score: 0.87, resolution: "reroute", outcome: "success"},
#   ...
# ]
```

### 3. Simulation

```python
# Simulate each candidate strategy
for strategy in ["platform_change", "reroute", "hold_train", ...]:
    outcome = simulator.simulate(conflict, strategy)
    # outcome.predicted_success = True/False
    # outcome.delay_reduction = 10 minutes
    # outcome.confidence = 0.85
```

### 4. Scoring & Ranking

```python
# Combine historical evidence and simulation
final_score = (
    0.4 * historical_score +   # What worked for similar cases
    0.5 * simulation_score +   # What simulation predicts
    0.1 * similarity_weight    # How similar the cases are
)

# Rank and return top recommendations
recommendations = sorted(candidates, key=lambda x: x.score, reverse=True)
```

---

## 🔁 Feedback Loop

The feedback loop enables **continuous learning** from real-world outcomes:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  1. RECOMMEND   │────▶│  2. OPERATOR     │────▶│  3. FEEDBACK    │
│                 │     │     APPLIES      │     │                 │
│  System says:   │     │                  │     │  Report actual  │
│  "Use platform  │     │  Platform change │     │  outcome        │
│   change"       │     │  executed        │     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
         ┌────────────────────────────────────────────────┘
         ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  4. COMPARE     │────▶│  5. STORE        │────▶│  6. IMPROVE     │
│                 │     │                  │     │                 │
│  Predicted: 5m  │     │  Golden run in   │     │  Next similar   │
│  Actual: 3m     │     │  Qdrant with     │     │  conflict gets  │
│  Accuracy: ✅   │     │  verified data   │     │  better recs    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

### Learning Metrics

```json
GET /api/v1/recommendations/metrics

{
  "overall_prediction_accuracy": 0.78,
  "outcome_prediction_accuracy": 0.85,
  "average_delay_prediction_error": 2.3,
  "total_feedback_count": 150,
  "strategy_metrics": {
    "platform_change": {
      "success_rate": 0.82,
      "prediction_accuracy": 0.88,
      "confidence_adjustment": 0.10
    }
  }
}
```

### Golden Runs

When feedback is received with matching predictions (successful outcome), the conflict-resolution pair is stored as a **golden run**—verified data that improves future recommendations:

```json
GET /api/v1/recommendations/golden-runs

{
  "golden_runs": [
    {
      "id": "gr-abc123",
      "conflict_id": "conf-456",
      "strategy": "platform_change",
      "outcome": "success",
      "actual_delay": 3,
      "created_at": "2026-01-26T10:30:00Z"
    }
  ],
  "count": 45
}
```

---

## 🧪 Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run by Category

```bash
pytest tests/ -m "generator"      # Conflict generation (33 tests)
pytest tests/ -m "embedding"      # Embedding service (22 tests)
pytest tests/ -m "qdrant"         # Vector database (28 tests)
pytest tests/ -m "simulation"     # Digital twin (57 tests)
pytest tests/ -m "recommendation" # Ranking engine (40 tests)
pytest tests/ -m "feedback"       # Feedback loop (37 tests)
pytest tests/ -m "api"            # API endpoints (26+ tests)
```

### Run Without Integration Tests

```bash
pytest tests/ -m "not integration"
```

### Test Coverage

```bash
pytest tests/ --cov=app --cov-report=html
```

### Test Summary

| Component | Tests | Status |
|-----------|-------|--------|
| Conflict Generator | 33 | ✅ |
| Embedding Service | 22 | ✅ |
| Qdrant Service | 28 | ✅ |
| Digital Twin | 57 | ✅ |
| Recommendation Engine | 40 | ✅ |
| Feedback Service | 37 | ✅ |
| API Endpoints | 26+ | ✅ |
| **Total** | **247** | ✅ |

---

## 📁 Project Structure

```
golden-retriever/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py        # Dependency injection
│   │   └── routes/
│   │       ├── conflicts.py       # Conflict endpoints
│   │       └── recommendations.py # Recommendation & feedback endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Settings management
│   │   ├── constants.py           # Enums: ConflictType, ResolutionStrategy
│   │   └── exceptions.py          # Custom exceptions
│   ├── models/
│   │   ├── __init__.py
│   │   ├── conflict.py            # Conflict data models
│   │   └── recommendation.py      # Recommendation models
│   └── services/
│       ├── __init__.py
│       ├── conflict_generator.py  # Synthetic conflict generation
│       ├── embedding_service.py   # Text → vector embeddings
│       ├── qdrant_service.py      # Vector database operations
│       ├── digital_twin.py        # Resolution simulation
│       ├── recommendation_engine.py # Orchestration & ranking
│       └── feedback_service.py    # Feedback loop & learning
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Shared fixtures & mocks
│   ├── test_conflict_generator.py
│   ├── test_embedding_service.py
│   ├── test_qdrant_service.py
│   ├── test_digital_twin.py
│   ├── test_recommendation_engine.py
│   ├── test_feedback_service.py
│   ├── test_api_endpoints.py
│   └── test_api/
│       ├── test_conflicts.py
│       └── test_recommendations.py
├── docs/
│   └── TESTING_STRATEGY.md        # Testing documentation
├── .env.example                   # Environment template
├── .env                           # Local configuration
├── pytest.ini                     # Pytest configuration
├── requirements.txt               # Python dependencies
├── COPILOT_CONTEXT.md            # AI assistant context
└── README.md                      # This file
```

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Framework** | FastAPI | REST API, async support, auto-docs |
| **Vector Database** | Qdrant Cloud | Similarity search, conflict memory |
| **Embeddings** | sentence-transformers | all-MiniLM-L6-v2 (384 dim) |
| **Data Validation** | Pydantic v2 | Request/response models |
| **Testing** | pytest, pytest-asyncio | Unit & integration tests |
| **Python** | 3.10+ | Runtime |

### Dependencies

```txt
fastapi>=0.100.0
uvicorn[standard]>=0.22.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
qdrant-client>=1.6.0
sentence-transformers>=2.2.0
python-dotenv>=1.0.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
httpx>=0.24.0
```

---

## 📈 Roadmap

- [ ] Real-time conflict detection from network feeds
- [ ] Multi-station conflict correlation
- [ ] Predictive conflict warning (pre-conflict detection)
- [ ] Dashboard UI for operators
- [ ] A/B testing for recommendation strategies
- [ ] Model retraining pipeline
- [ ] Prometheus metrics export
- [ ] Kubernetes deployment manifests

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

<p align="center">
  <b>Golden Retriever</b> - Finding the best resolution, every time. 🦮
</p>
