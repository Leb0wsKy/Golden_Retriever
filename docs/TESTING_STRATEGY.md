# Golden Retriever Testing Strategy

## Overview

This document outlines the comprehensive testing strategy for the Golden Retriever rail conflict resolution system. The strategy ensures **isolated, reproducible, and maintainable** tests across all components.

## Test Architecture

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── pytest.ini                     # Pytest configuration
├── test_conflict_generator.py     # Conflict generation tests (33 tests)
├── test_embedding_service.py      # Embedding creation tests (22 tests)
├── test_qdrant_service.py         # Vector database tests (28 tests)
├── test_digital_twin.py           # Simulation scoring tests (57 tests)
├── test_recommendation_engine.py  # Recommendation ranking tests (40 tests)
├── test_feedback_service.py       # Feedback loop tests (37 tests)
├── test_api_endpoints.py          # API integration tests (20 tests)
└── test_api/                      # Additional API tests (6 tests)
    ├── test_conflicts.py
    └── test_recommendations.py
```

**Total: 247 tests passing**

---

## 1. Conflict Generation Testing

### Purpose
Test the synthetic conflict generator produces valid, diverse, and reproducible conflicts.

### Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| Basic generation | 5 | Generate single/multiple conflicts |
| Type-specific | 4 | Generate by conflict type |
| Configuration | 6 | Custom generator settings |
| Reproducibility | 3 | Seeded random generation |
| Validation | 8 | Output schema validation |
| Edge cases | 7 | Boundary conditions |

### Key Fixtures

```python
@pytest.fixture
def conflict_generator() -> ConflictGenerator:
    """Seeded generator for reproducible tests."""
    return ConflictGenerator(seed=42)

@pytest.fixture
def sample_conflict(conflict_generator) -> GeneratedConflict:
    """Single conflict for testing."""
    return conflict_generator.generate(count=1)[0]
```

### Example Tests

```python
class TestConflictGeneration:
    """Test conflict generation functionality."""
    
    def test_generate_single_conflict(self, conflict_generator):
        """Generate one conflict."""
        conflicts = conflict_generator.generate(count=1)
        assert len(conflicts) == 1
        assert isinstance(conflicts[0], GeneratedConflict)
    
    def test_reproducibility_with_seed(self):
        """Same seed produces same conflicts."""
        gen1 = ConflictGenerator(seed=42)
        gen2 = ConflictGenerator(seed=42)
        
        conflicts1 = gen1.generate(count=5)
        conflicts2 = gen2.generate(count=5)
        
        for c1, c2 in zip(conflicts1, conflicts2):
            assert c1.conflict_type == c2.conflict_type
            assert c1.station == c2.station
    
    def test_conflict_type_distribution(self, conflict_generator):
        """All conflict types are generated."""
        conflicts = conflict_generator.generate(count=100)
        types = {c.conflict_type for c in conflicts}
        assert len(types) >= 3  # At least 3 different types
```

### Isolation Strategy

- Use seeded random generators (`seed=42`)
- No external dependencies
- Each test creates its own generator instance
- Tests don't share state

---

## 2. Embedding Creation Testing

### Purpose
Test the embedding service produces valid 384-dimensional vectors for text and conflicts.

### Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| Text embedding | 4 | Embed plain text |
| Conflict embedding | 5 | Embed conflict objects |
| Batch processing | 3 | Multiple embeddings |
| Vector properties | 5 | Dimension, normalization |
| Similarity | 3 | Similar texts → similar vectors |
| Error handling | 2 | Invalid inputs |

### Key Fixtures

```python
@pytest.fixture
def embedding_service():
    """Create embedding service with mocked model."""
    with patch("sentence_transformers.SentenceTransformer"):
        service = EmbeddingService()
        service._model = Mock()
        service._model.encode.return_value = np.array([[0.1] * 384])
        yield service

@pytest.fixture
def mock_embedding() -> List[float]:
    """384-dimensional mock embedding."""
    random.seed(42)
    return [random.random() for _ in range(384)]
```

### Example Tests

```python
class TestEmbeddingCreation:
    """Test embedding generation."""
    
    def test_embed_text_returns_384_dimensions(self, embedding_service):
        """Embeddings are 384-dimensional."""
        embedding = embedding_service.embed_text("Platform conflict at station")
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
    
    def test_embed_conflict_uses_description(self, embedding_service, sample_conflict):
        """Conflict embedding includes key fields."""
        embedding = embedding_service.embed_conflict(sample_conflict)
        assert len(embedding) == 384
    
    def test_similar_texts_similar_embeddings(self, real_embedding_service):
        """Similar texts produce similar embeddings."""
        emb1 = real_embedding_service.embed_text("Platform 3 double-booked")
        emb2 = real_embedding_service.embed_text("Platform 3 has booking conflict")
        emb3 = real_embedding_service.embed_text("Train delayed due to weather")
        
        # Cosine similarity
        sim_12 = cosine_similarity(emb1, emb2)
        sim_13 = cosine_similarity(emb1, emb3)
        
        assert sim_12 > sim_13  # Related texts more similar
```

### Isolation Strategy

- Mock the SentenceTransformer model for unit tests
- Use real model only in integration tests (marked `@pytest.mark.integration`)
- Predictable mock outputs for deterministic tests

---

## 3. Qdrant Search Logic Testing (Mocked)

### Purpose
Test vector database operations without requiring a live Qdrant instance.

### Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| Connection | 4 | Client initialization |
| Collection management | 5 | Create/ensure collections |
| Upsert operations | 6 | Single and batch inserts |
| Search operations | 8 | Similarity search |
| Filtering | 3 | Filtered search queries |
| Error handling | 2 | Connection failures |

### Key Fixtures

```python
@pytest.fixture
def mock_qdrant_client():
    """Mocked Qdrant client."""
    with patch("qdrant_client.QdrantClient") as mock:
        client = Mock()
        client.get_collections.return_value = Mock(collections=[])
        client.search.return_value = [
            Mock(id="conflict-1", score=0.95, payload={"conflict_type": "platform_conflict"}),
            Mock(id="conflict-2", score=0.87, payload={"conflict_type": "headway_violation"}),
        ]
        mock.return_value = client
        yield client

@pytest.fixture
def qdrant_service(mock_qdrant_client):
    """Qdrant service with mocked client."""
    service = QdrantService()
    service._client = mock_qdrant_client
    return service
```

### Example Tests

```python
class TestQdrantSearchLogic:
    """Test Qdrant search operations (mocked)."""
    
    def test_search_returns_similar_conflicts(self, qdrant_service, mock_embedding):
        """Search finds similar conflicts."""
        results = qdrant_service.search_similar_conflicts(
            query_embedding=mock_embedding,
            limit=5
        )
        
        assert len(results.matches) > 0
        assert results.matches[0].score >= results.matches[1].score  # Sorted
    
    def test_search_with_filter(self, qdrant_service, mock_embedding):
        """Search respects filter conditions."""
        results = qdrant_service.search_similar_conflicts(
            query_embedding=mock_embedding,
            limit=5,
            filter_conditions={"conflict_type": "platform_conflict"}
        )
        
        # Verify filter was applied
        qdrant_service.client.search.assert_called_once()
        call_kwargs = qdrant_service.client.search.call_args.kwargs
        assert call_kwargs.get("query_filter") is not None
    
    def test_upsert_stores_conflict(self, qdrant_service, sample_conflict, mock_embedding):
        """Upsert stores conflict in collection."""
        result = qdrant_service.upsert_conflict(sample_conflict, mock_embedding)
        
        assert result.success is True
        assert result.collection == "conflict_memory"
        qdrant_service.client.upsert.assert_called_once()
    
    def test_batch_upsert_efficiency(self, qdrant_service, sample_conflicts):
        """Batch upsert uses single call."""
        embeddings = [[0.1] * 384 for _ in sample_conflicts]
        
        results = qdrant_service.upsert_conflicts_batch(sample_conflicts, embeddings)
        
        assert len(results) == len(sample_conflicts)
        # Should be single upsert call, not multiple
        assert qdrant_service.client.upsert.call_count == 1
```

### Isolation Strategy

- **Always mock** `QdrantClient` for unit tests
- Use `@pytest.mark.qdrant` for tests requiring live Qdrant
- Mock returns predictable search results
- No network calls in standard test runs

---

## 4. Simulation Scoring Testing

### Purpose
Test the digital twin simulator produces accurate and consistent resolution scores.

### Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| Basic simulation | 8 | Simulate single resolutions |
| Strategy effectiveness | 12 | Each strategy type |
| Scoring accuracy | 10 | Score calculation logic |
| Context factors | 8 | Time, severity, station effects |
| Edge cases | 10 | Boundary conditions |
| Batch simulation | 5 | Multiple simulations |
| Determinism | 4 | Reproducible results |

### Key Fixtures

```python
@pytest.fixture
def simulator():
    """Digital twin simulator instance."""
    return DigitalTwinSimulator(seed=42)

@pytest.fixture
def high_severity_conflict(conflict_generator):
    """Conflict with high severity."""
    conflict = conflict_generator.generate(count=1)[0]
    conflict.severity = ConflictSeverity.CRITICAL
    return conflict
```

### Example Tests

```python
class TestSimulationScoring:
    """Test simulation scoring logic."""
    
    def test_simulation_returns_outcome(self, simulator, sample_conflict):
        """Simulation produces outcome."""
        outcome = simulator.simulate(
            conflict=sample_conflict,
            strategy=ResolutionStrategy.PLATFORM_CHANGE
        )
        
        assert outcome.predicted_success in [True, False]
        assert 0 <= outcome.simulation_score <= 100
        assert outcome.delay_after >= 0
    
    def test_higher_severity_lower_success(self, simulator, conflict_generator):
        """High severity reduces success probability."""
        low_severity = conflict_generator.generate(count=1)[0]
        low_severity.severity = ConflictSeverity.LOW
        
        high_severity = conflict_generator.generate(count=1)[0]
        high_severity.severity = ConflictSeverity.CRITICAL
        
        # Run multiple simulations for statistical significance
        low_scores = [
            simulator.simulate(low_severity, ResolutionStrategy.PLATFORM_CHANGE).simulation_score
            for _ in range(20)
        ]
        high_scores = [
            simulator.simulate(high_severity, ResolutionStrategy.PLATFORM_CHANGE).simulation_score
            for _ in range(20)
        ]
        
        assert sum(low_scores) / len(low_scores) > sum(high_scores) / len(high_scores)
    
    def test_strategy_suitability_affects_score(self, simulator, platform_conflict):
        """Matching strategy scores higher."""
        # Platform change is suitable for platform conflicts
        suitable = simulator.simulate(platform_conflict, ResolutionStrategy.PLATFORM_CHANGE)
        # Hold train is less suitable
        unsuitable = simulator.simulate(platform_conflict, ResolutionStrategy.HOLD_TRAIN)
        
        assert suitable.simulation_score >= unsuitable.simulation_score
    
    def test_simulation_determinism(self, sample_conflict):
        """Same seed produces same results."""
        sim1 = DigitalTwinSimulator(seed=42)
        sim2 = DigitalTwinSimulator(seed=42)
        
        outcome1 = sim1.simulate(sample_conflict, ResolutionStrategy.REROUTE)
        outcome2 = sim2.simulate(sample_conflict, ResolutionStrategy.REROUTE)
        
        assert outcome1.simulation_score == outcome2.simulation_score
        assert outcome1.predicted_success == outcome2.predicted_success
```

### Isolation Strategy

- Use seeded simulators for determinism
- No external dependencies
- Each test gets fresh simulator instance
- Statistical tests use sufficient samples

---

## 5. Recommendation Ranking Testing

### Purpose
Test the recommendation engine ranks strategies correctly based on historical evidence and simulation.

### Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| Basic ranking | 5 | Rank strategies for conflict |
| Historical weighting | 8 | Evidence from similar cases |
| Simulation integration | 6 | Combined scoring |
| Confidence calculation | 5 | Confidence bounds |
| Top-K selection | 4 | Return N recommendations |
| Explanation generation | 5 | Human-readable explanations |
| Edge cases | 7 | No history, no simulation |

### Key Fixtures

```python
@pytest.fixture
def recommendation_engine(mock_embedding_service, mock_qdrant_service, mock_simulator):
    """Engine with all dependencies mocked."""
    engine = RecommendationEngine()
    engine._embedding_service = mock_embedding_service
    engine._qdrant_service = mock_qdrant_service
    engine._simulator = mock_simulator
    return engine

@pytest.fixture
def mock_similar_conflicts():
    """Mock historical similar conflicts."""
    return [
        SimilarConflict(
            id="hist-1", score=0.95,
            conflict_type="platform_conflict", severity="high",
            station="King's Cross", time_of_day="morning_peak",
            resolution_strategy="platform_change", resolution_outcome="success"
        ),
        SimilarConflict(
            id="hist-2", score=0.88,
            conflict_type="platform_conflict", severity="medium",
            station="Paddington", time_of_day="midday",
            resolution_strategy="platform_change", resolution_outcome="success"
        ),
    ]
```

### Example Tests

```python
class TestRecommendationRanking:
    """Test recommendation ranking logic."""
    
    @pytest.mark.asyncio
    async def test_recommendations_are_ranked(self, recommendation_engine, sample_conflict):
        """Recommendations sorted by score."""
        response = await recommendation_engine.recommend(sample_conflict)
        
        assert len(response.recommendations) > 0
        scores = [r.final_score for r in response.recommendations]
        assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_historical_success_boosts_score(
        self, recommendation_engine, sample_conflict, mock_similar_conflicts
    ):
        """Strategies with historical success rank higher."""
        # All similar conflicts used platform_change successfully
        recommendation_engine._qdrant_service.search_similar_conflicts.return_value = Mock(
            matches=mock_similar_conflicts
        )
        
        response = await recommendation_engine.recommend(sample_conflict)
        
        # Platform change should be top recommendation
        top_strategy = response.recommendations[0].strategy
        assert top_strategy == ResolutionStrategy.PLATFORM_CHANGE
    
    @pytest.mark.asyncio
    async def test_confidence_bounded(self, recommendation_engine, sample_conflict):
        """Confidence scores between 0 and 1."""
        response = await recommendation_engine.recommend(sample_conflict)
        
        for rec in response.recommendations:
            assert 0.0 <= rec.confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_explanations_generated(self, recommendation_engine, sample_conflict):
        """Recommendations include explanations."""
        response = await recommendation_engine.recommend(sample_conflict)
        
        for rec in response.recommendations:
            assert rec.explanation is not None
            assert len(rec.explanation) > 10  # Meaningful explanation
    
    @pytest.mark.asyncio
    async def test_no_history_uses_simulation(self, recommendation_engine, sample_conflict):
        """Without history, relies on simulation."""
        # No similar conflicts found
        recommendation_engine._qdrant_service.search_similar_conflicts.return_value = Mock(
            matches=[]
        )
        
        response = await recommendation_engine.recommend(sample_conflict)
        
        # Should still produce recommendations from simulation
        assert len(response.recommendations) > 0
        assert response.similar_conflicts_found == 0
```

### Isolation Strategy

- Mock all external services (embedding, Qdrant, simulator)
- Control historical evidence via mock returns
- Test each scoring component independently
- Use `@pytest.mark.asyncio` for async tests

---

## 6. Feedback Loop Testing

### Purpose
Test the feedback service correctly processes outcomes and updates metrics.

### Test Categories

| Category | Tests | Description |
|----------|-------|-------------|
| Outcome comparison | 7 | Predicted vs actual |
| Confidence adjustment | 4 | Score adjustments |
| Golden run storage | 7 | Verified outcome storage |
| Metrics tracking | 7 | Accuracy statistics |
| Learning insights | 3 | Generated insights |
| Golden run retrieval | 5 | Query stored runs |
| Factory functions | 4 | Service initialization |

### Example Tests

```python
class TestFeedbackLoop:
    """Test feedback loop functionality."""
    
    @pytest.mark.asyncio
    async def test_accurate_prediction_boosts_confidence(
        self, feedback_service, sample_conflict_data
    ):
        """Accurate predictions increase confidence."""
        result = await feedback_service.process_feedback(
            conflict_id="conf-123",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
            predicted_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay_after=5,
        )
        
        assert result.prediction_was_accurate is True
        assert result.confidence_adjustment > 0
    
    @pytest.mark.asyncio
    async def test_golden_run_stored(self, feedback_service, sample_conflict_data):
        """Feedback creates golden run."""
        result = await feedback_service.process_feedback(
            conflict_id="conf-123",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=3,
        )
        
        assert result.golden_run is not None
        assert result.golden_run.is_golden is True
        assert result.stored_in_qdrant is True
```

---

## Running Tests

### Full Test Suite

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific category
pytest tests/ -v -m "unit"
pytest tests/ -v -m "generator"
pytest tests/ -v -m "not integration"
```

### Individual Components

```bash
# Conflict generator
pytest tests/test_conflict_generator.py -v

# Embedding service
pytest tests/test_embedding_service.py -v

# Qdrant service (mocked)
pytest tests/test_qdrant_service.py -v

# Simulation
pytest tests/test_digital_twin.py -v

# Recommendation engine
pytest tests/test_recommendation_engine.py -v

# Feedback loop
pytest tests/test_feedback_service.py -v

# API endpoints
pytest tests/test_api_endpoints.py -v
```

### Quick Smoke Test

```bash
# Fast tests only
pytest tests/ -v -m "unit" --ignore=tests/test_api_endpoints.py
```

---

## Test Markers

Use markers to categorize and selectively run tests:

```python
@pytest.mark.unit
def test_simple_function():
    """Fast, isolated test."""
    pass

@pytest.mark.integration
@pytest.mark.qdrant
def test_live_qdrant_search():
    """Requires live Qdrant instance."""
    pass

@pytest.mark.slow
def test_large_batch_processing():
    """Takes >1 second."""
    pass
```

Run by marker:

```bash
pytest -m "unit"              # Only unit tests
pytest -m "not integration"   # Skip integration tests
pytest -m "generator"         # Only generator tests
```

---

## Fixtures Best Practices

### 1. Use Seeded Randomness

```python
@pytest.fixture
def deterministic_generator():
    return ConflictGenerator(seed=42)
```

### 2. Scope Fixtures Appropriately

```python
@pytest.fixture(scope="module")  # Expensive setup, reuse across module
def embedding_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

@pytest.fixture(scope="function")  # Fresh for each test (default)
def conflict():
    return generator.generate(count=1)[0]
```

### 3. Use Autouse for Cleanup

```python
@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test."""
    reset_feedback_service()
    yield
    reset_feedback_service()
```

### 4. Compose Fixtures

```python
@pytest.fixture
def mock_services(mock_embedding_service, mock_qdrant_service, mock_simulator):
    """Bundle all mocked services."""
    return {
        "embedding": mock_embedding_service,
        "qdrant": mock_qdrant_service,
        "simulator": mock_simulator,
    }
```

---

## Mocking Strategy

### When to Mock

| Component | Unit Tests | Integration Tests |
|-----------|-----------|-------------------|
| Qdrant | ✅ Mock | Real connection |
| Embedding model | ✅ Mock | Real model |
| Simulator | Usually real | Real |
| External APIs | ✅ Mock | ✅ Mock |

### How to Mock

```python
from unittest.mock import Mock, patch, AsyncMock

# Patch at import location
@patch("app.services.recommendation_engine.get_embedding_service")
def test_with_mocked_embedding(mock_get):
    mock_service = Mock()
    mock_service.embed_text.return_value = [0.1] * 384
    mock_get.return_value = mock_service
    
    # Test code...

# Async mocking
@patch("app.services.qdrant_service.QdrantService.search_similar_conflicts")
async def test_async_search(mock_search):
    mock_search.return_value = AsyncMock(return_value=SearchResult(...))
    
    # Test code...
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: pytest tests/ -v --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Summary

| Component | Tests | Isolation Method |
|-----------|-------|------------------|
| Conflict Generator | 33 | Seeded random |
| Embedding Service | 22 | Mocked model |
| Qdrant Service | 28 | Mocked client |
| Digital Twin | 57 | Seeded simulator |
| Recommendation Engine | 40 | All deps mocked |
| Feedback Service | 37 | Mocked Qdrant |
| API Endpoints | 26 | TestClient |
| **Total** | **247** | |

All tests are:
- ✅ **Isolated** - No shared state between tests
- ✅ **Reproducible** - Seeded randomness, deterministic mocks
- ✅ **Fast** - Mocked external dependencies
- ✅ **Maintainable** - Clear fixtures and markers
