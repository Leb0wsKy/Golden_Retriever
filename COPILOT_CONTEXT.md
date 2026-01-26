You are building a Python backend project called "Golden Retriever".

Goal:
An AI-powered rail conflict resolution system using:
- Synthetic rail conflict generation
- Vector similarity search with Qdrant
- Sentence-transformer embeddings
- A rule-based digital twin simulator
- FastAPI for APIs
- **Feedback loop for continuous learning**

Core concepts:
- A "conflict" is an operational rail issue (platform, headway, track, capacity).
- The system retrieves similar past conflicts ("golden runs") from Qdrant.
- It simulates candidate resolutions and ranks them.
- It stores outcomes back into Qdrant for continuous learning.

Constraints:
- Python 3.10+
- Clean architecture
- Modular design
- No hardcoded data except synthetic generators
- All logic must be testable

Key components:
- Conflict generator
- Embedding service
- Qdrant service
- Simulation engine
- Recommendation engine
- **Feedback service** (new: for continuous learning)
- REST API

Always explain code with docstrings and comments.

---

# Feedback Loop: How It Improves Future Recommendations

The feedback loop is the key mechanism for **continuous learning**. Here's how it works:

## 1. Collect Real-World Outcomes

When an operator resolves a conflict and submits feedback:

```json
POST /api/v1/recommendations/feedback
{
    "conflict_id": "conf-123",
    "strategy_applied": "platform_change",
    "outcome": "success",
    "actual_delay_after": 3,
    "predicted_outcome": "success",     // Optional: what system predicted
    "predicted_delay_after": 5,         // Optional: predicted delay
    "notes": "Smooth execution"
}
```

## 2. Compare Predicted vs Actual

The system compares what it predicted vs what actually happened:

| Accuracy Level | Criteria | Learning Action |
|----------------|----------|-----------------|
| **Exact** | Outcome matches, delay within 2 min | High confidence boost (+15%) |
| **Close** | Outcome matches, delay within 5 min | Moderate boost (+10%) |
| **Outcome Only** | Outcome matches, delay way off | Small boost, calibrate delay |
| **Miss** | Outcome doesn't match | Reduce confidence (-10%) |

## 3. Store as Golden Run

Verified outcomes are stored as **golden runs** in Qdrant:

- Embedded with rich conflict+resolution text
- Marked with `is_golden_run: true` and `has_verified_outcome: true`
- Includes actual delay, reduction, and prediction accuracy

## 4. Update Success Metrics

The system tracks strategy performance over time:

```
GET /api/v1/recommendations/metrics
{
    "overall_prediction_accuracy": 0.78,
    "strategy_metrics": {
        "platform_change": {
            "success_rate": 0.85,
            "prediction_accuracy": 0.88,
            "confidence_adjustment": +0.1
        }
    }
}
```

## 5. Improve Future Recommendations

When a new conflict arrives:

1. **Similarity Search**: Find historical cases (including golden runs)
2. **Boost from Golden Runs**: Verified outcomes carry more weight
3. **Confidence Adjustment**: Apply strategy-level adjustments
4. **Better Ranking**: More accurate recommendations over time

**Example:**
- Day 1: Platform change at King's Cross → SUCCESS (stored as golden run)
- Day 2: Similar conflict → System finds golden run, boosts confidence
- Day 30: 10 feedbacks, 8 successes → Confidence for platform change at King's Cross now 0.92

## Key Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/recommendations/feedback` | Submit resolution outcome |
| `GET /api/v1/recommendations/metrics` | Get learning metrics |
| `GET /api/v1/recommendations/metrics/strategy/{name}` | Strategy performance |
| `GET /api/v1/recommendations/golden-runs` | List verified outcomes |

## Tests (247 passing)

- `test_feedback_service.py` - 37 tests for feedback loop
- `test_api_endpoints.py` - 20 tests for API endpoints
- Full suite: `pytest tests/ -v`
