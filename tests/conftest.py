"""
Pytest configuration and shared fixtures.

Provides reusable test fixtures for the test suite.
All fixtures are designed for isolation and reproducibility.
"""

import pytest
import random
from typing import Generator, Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient

from app.main import app
from app.services.conflict_generator import ConflictGenerator, GeneratorConfig
from app.models.conflict import GeneratedConflict
from app.core.constants import (
    ConflictType,
    ConflictSeverity,
    TimeOfDay,
    ResolutionStrategy,
    ResolutionOutcome,
)


# =============================================================================
# Application Fixtures
# =============================================================================

@pytest.fixture
def client() -> Generator:
    """
    Create a test client for the FastAPI application.
    
    Yields:
        TestClient instance.
    """
    with TestClient(app) as test_client:
        yield test_client


# =============================================================================
# Conflict Generator Fixtures
# =============================================================================

@pytest.fixture
def conflict_generator() -> ConflictGenerator:
    """
    Create a seeded conflict generator for reproducible tests.
    
    Returns:
        ConflictGenerator with fixed seed.
    """
    return ConflictGenerator(seed=42)


@pytest.fixture
def sample_conflict(conflict_generator: ConflictGenerator) -> GeneratedConflict:
    """
    Create a sample generated conflict for testing.
    
    Returns:
        GeneratedConflict instance.
    """
    return conflict_generator.generate(count=1)[0]


@pytest.fixture
def sample_conflicts(conflict_generator: ConflictGenerator) -> List[GeneratedConflict]:
    """
    Generate multiple sample conflicts.
    
    Returns:
        List of GeneratedConflict instances.
    """
    return conflict_generator.generate(count=5)


@pytest.fixture
def sample_conflict_dict(sample_conflict: GeneratedConflict) -> Dict[str, Any]:
    """
    Create a sample conflict as dictionary.
    
    Returns:
        Conflict data as dictionary.
    """
    return sample_conflict.model_dump()


@pytest.fixture
def platform_conflict(conflict_generator: ConflictGenerator) -> GeneratedConflict:
    """
    Generate a platform conflict specifically.
    
    Returns:
        GeneratedConflict of type PLATFORM_CONFLICT.
    """
    return conflict_generator.generate_by_type(ConflictType.PLATFORM_CONFLICT, count=1)[0]


@pytest.fixture
def track_blockage_conflict(conflict_generator: ConflictGenerator) -> GeneratedConflict:
    """
    Generate a track blockage conflict specifically.
    
    Returns:
        GeneratedConflict of type TRACK_BLOCKAGE.
    """
    return conflict_generator.generate_by_type(ConflictType.TRACK_BLOCKAGE, count=1)[0]


@pytest.fixture
def mock_embedding() -> List[float]:
    """
    Create a mock embedding vector.
    
    Returns:
        List of floats representing an embedding.
    """
    import random
    random.seed(42)
    return [random.random() for _ in range(384)]


@pytest.fixture
def high_success_generator() -> ConflictGenerator:
    """
    Create a generator configured for high success rate.
    
    Returns:
        ConflictGenerator with 95% success rate.
    """
    config = GeneratorConfig(
        success_rate=0.95,
        partial_success_rate=0.04,
        min_confidence=0.8,
        max_confidence=0.99
    )
    return ConflictGenerator(seed=42, config=config)


# =============================================================================
# Mocked Service Fixtures
# =============================================================================

@pytest.fixture
def mock_embedding_service():
    """
    Create a mocked embedding service.
    
    Returns deterministic 384-dimensional embeddings.
    """
    mock_service = Mock()
    mock_service.embed_text = Mock(return_value=[0.1] * 384)
    mock_service.embed_conflict = Mock(return_value=[0.1] * 384)
    mock_service.embed_texts = Mock(return_value=[[0.1] * 384])
    return mock_service


@pytest.fixture
def mock_qdrant_service():
    """
    Create a mocked Qdrant service.
    
    Returns mock search results and upsert responses.
    """
    from app.services.qdrant_service import SearchResult, SimilarConflict, UpsertResult
    
    mock_service = Mock()
    mock_service.ensure_collections = Mock()
    mock_service.client = Mock()
    mock_service.client.upsert = Mock()
    
    # Mock search results
    mock_results = SearchResult(
        query_id="test-query",
        matches=[
            SimilarConflict(
                id="conflict-1",
                score=0.95,
                conflict_type="platform_conflict",
                severity="high",
                station="King's Cross",
                time_of_day="morning_peak",
                resolution_strategy="platform_change",
                resolution_outcome="success",
            ),
            SimilarConflict(
                id="conflict-2",
                score=0.87,
                conflict_type="platform_conflict",
                severity="medium",
                station="Paddington",
                time_of_day="midday",
                resolution_strategy="reroute",
                resolution_outcome="success",
            ),
        ],
        total_matches=2,
        search_time_ms=15.5,
    )
    mock_service.search_similar_conflicts = Mock(return_value=mock_results)
    
    # Mock upsert
    mock_service.upsert_conflict = AsyncMock(return_value=UpsertResult(
        id="test-id",
        collection="conflict_memory",
        success=True,
    ))
    
    return mock_service


@pytest.fixture
def mock_simulator():
    """
    Create a mocked digital twin simulator.
    
    Returns deterministic simulation outcomes.
    """
    from app.services.digital_twin import SimulationOutcome
    
    mock_sim = Mock()
    mock_sim.simulate = Mock(return_value=SimulationOutcome(
        conflict_id="test",
        strategy=ResolutionStrategy.PLATFORM_CHANGE,
        predicted_success=True,
        delay_before=15,
        delay_after=5,
        delay_reduction=10,
        recovery_time=8,
        confidence=0.85,
        simulation_score=82,
        factors={"base": 70, "severity": -5, "time": 10, "strategy": 7},
    ))
    return mock_sim


@pytest.fixture
def mock_recommendation_engine(mock_embedding_service, mock_qdrant_service, mock_simulator):
    """
    Create a recommendation engine with all dependencies mocked.
    """
    with patch("app.services.recommendation_engine.get_embedding_service") as mock_embed, \
         patch("app.services.recommendation_engine.get_qdrant_service") as mock_qdrant, \
         patch("app.services.recommendation_engine.DigitalTwinSimulator") as mock_sim_class:
        
        mock_embed.return_value = mock_embedding_service
        mock_qdrant.return_value = mock_qdrant_service
        mock_sim_class.return_value = mock_simulator
        
        from app.services.recommendation_engine import RecommendationEngine
        engine = RecommendationEngine()
        engine._embedding_service = mock_embedding_service
        engine._qdrant_service = mock_qdrant_service
        engine._simulator = mock_simulator
        
        yield engine


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_conflict_data() -> Dict[str, Any]:
    """
    Sample conflict data dictionary for testing.
    """
    return {
        "conflict_type": "platform_conflict",
        "severity": "high",
        "station": "London King's Cross",
        "time_of_day": "morning_peak",
        "affected_trains": ["IC101", "RE202"],
        "delay_before": 15,
        "description": "Platform 5 double-booked for arrivals",
        "platform": "5",
    }


@pytest.fixture
def sample_feedback_data() -> Dict[str, Any]:
    """
    Sample feedback data for testing.
    """
    return {
        "conflict_id": "conf-test-123",
        "strategy_applied": "platform_change",
        "outcome": "success",
        "actual_delay_after": 3,
        "resolution_time_minutes": 8,
        "notes": "Resolution executed smoothly",
    }


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_feedback_service_state():
    """
    Reset feedback service state before each test.
    
    This ensures tests don't share state through the feedback service.
    """
    from app.services.feedback_service import reset_feedback_service
    reset_feedback_service()
    yield
    reset_feedback_service()
