"""
Tests for FastAPI endpoints.

Tests the conflict generation, analysis, recommendation, and feedback endpoints.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.constants import (
    ConflictType,
    ConflictSeverity,
    TimeOfDay,
    ResolutionStrategy,
    ResolutionOutcome,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_conflict_generator():
    """Mock conflict generator."""
    with patch("app.api.routes.conflicts.get_conflict_generator") as mock:
        from app.models.conflict import GeneratedConflict, RecommendedResolution, FinalOutcome
        
        sample_conflict = GeneratedConflict(
            id="gen-001",
            conflict_type=ConflictType.PLATFORM_CONFLICT,
            severity=ConflictSeverity.HIGH,
            station="Test Station",
            time_of_day=TimeOfDay.MORNING_PEAK,
            affected_trains=["T1", "T2"],
            delay_before=15,
            description="Test conflict description for generation",
            platform="3",
            detected_at=datetime(2026, 1, 26),
            recommended_resolution=RecommendedResolution(
                strategy=ResolutionStrategy.PLATFORM_CHANGE,
                confidence=0.85,
                estimated_delay_reduction=10,
                description="Change platform to resolve conflict",
            ),
            final_outcome=FinalOutcome(
                outcome=ResolutionOutcome.SUCCESS,
                actual_delay=5,
                resolution_time_minutes=8,
                notes="Resolved successfully",
            ),
        )
        
        generator = Mock()
        # Mock both generate methods
        generator.generate.return_value = [sample_conflict]
        generator.generate_by_type.return_value = [sample_conflict]
        mock.return_value = generator
        yield generator


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for both routes modules."""
    with patch("app.api.routes.conflicts.get_embedding_service") as mock1, \
         patch("app.api.routes.recommendations.get_embedding_service") as mock2:
        service = Mock()
        service.embed_text.return_value = [0.1] * 384
        mock1.return_value = service
        mock2.return_value = service
        yield service


@pytest.fixture
def mock_qdrant_service():
    """Mock Qdrant service for both routes modules."""
    with patch("app.api.routes.conflicts.get_qdrant_service") as mock1, \
         patch("app.api.routes.recommendations.get_qdrant_service") as mock2:
        service = Mock()
        service.upsert_conflict = AsyncMock(return_value=Mock(id="point-123"))
        
        # Mock search result
        from app.services.qdrant_service import SearchResult, SimilarConflict
        service.search_similar_conflicts = AsyncMock(return_value=SearchResult(
            total_found=2,
            query_time_ms=10.5,
            matches=[
                SimilarConflict(
                    id="hist-001",
                    score=0.92,
                    conflict_type="platform_conflict",
                    severity="high",
                    station="Test Station",
                    time_of_day="morning_peak",
                    affected_trains=["T1"],
                    delay_before=12,
                    resolution_strategy="platform_change",
                    resolution_outcome="success",
                    actual_delay_after=3,
                ),
                SimilarConflict(
                    id="hist-002",
                    score=0.85,
                    conflict_type="platform_conflict",
                    severity="medium",
                    station="Other Station",
                    time_of_day="midday",
                    affected_trains=["T2"],
                    delay_before=8,
                    resolution_strategy="delay",
                    resolution_outcome="partial_success",
                    actual_delay_after=4,
                ),
            ],
        ))
        mock1.return_value = service
        mock2.return_value = service
        yield service


@pytest.fixture
def mock_recommendation_engine():
    """Mock recommendation engine."""
    with patch("app.api.routes.conflicts.get_recommendation_engine") as mock:
        from app.services.recommendation_engine import (
            RecommendationResponse,
            Recommendation,
            ScoreBreakdown,
            SimulationEvidence,
        )
        
        engine = Mock()
        engine.recommend = AsyncMock(return_value=RecommendationResponse(
            conflict_id="conf-test",
            conflict_type=ConflictType.PLATFORM_CONFLICT,
            recommendations=[
                Recommendation(
                    rank=1,
                    strategy=ResolutionStrategy.PLATFORM_CHANGE,
                    final_score=82.5,
                    confidence=0.87,
                    explanation="Platform change recommended with 87% confidence based on historical success.",
                    score_breakdown=ScoreBreakdown(
                        historical_score=80,
                        historical_weight=0.4,
                        simulation_score=85,
                        simulation_weight=0.5,
                        similarity_bonus=3.0,
                        confidence_adjustment=0,
                        final_score=82.5,
                    ),
                    historical_evidence=[],
                    simulation_evidence=SimulationEvidence(
                        predicted_success=True,
                        delay_after=5,
                        delay_reduction=10,
                        recovery_time=15,
                        simulation_score=85,
                        confidence=0.9,
                        explanation="Simulation predicts success",
                    ),
                    historical_success_rate=0.85,
                    num_similar_cases=3,
                    avg_similarity=0.88,
                ),
                Recommendation(
                    rank=2,
                    strategy=ResolutionStrategy.DELAY,
                    final_score=65.0,
                    confidence=0.72,
                    explanation="Delay is a secondary option.",
                    score_breakdown=ScoreBreakdown(
                        historical_score=60,
                        historical_weight=0.4,
                        simulation_score=70,
                        simulation_weight=0.5,
                        final_score=65.0,
                    ),
                    historical_evidence=[],
                    simulation_evidence=SimulationEvidence(
                        predicted_success=True,
                        delay_after=8,
                        delay_reduction=7,
                        recovery_time=20,
                        simulation_score=70,
                        confidence=0.8,
                        explanation="Delay may work",
                    ),
                    historical_success_rate=0.65,
                    num_similar_cases=2,
                    avg_similarity=0.75,
                ),
            ],
            total_candidates=5,
            similar_conflicts_found=3,
            processing_time_ms=150.5,
            summary="Platform change is the top recommendation.",
        ))
        mock.return_value = engine
        yield engine


# =============================================================================
# Test POST /conflicts/generate
# =============================================================================

class TestGenerateConflicts:
    """Test conflict generation endpoint."""
    
    def test_generate_conflicts_basic(
        self, client, mock_conflict_generator
    ):
        """Generate conflicts with default parameters."""
        response = client.post(
            "/api/v1/conflicts/generate",
            json={"count": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "generated_count" in data
        assert "conflicts" in data
        assert "summary" in data
        assert data["generated_count"] >= 0
    
    def test_generate_conflicts_with_options(
        self, client, mock_conflict_generator
    ):
        """Generate conflicts with custom options."""
        response = client.post(
            "/api/v1/conflicts/generate",
            json={
                "count": 10,
                "conflict_types": ["platform_conflict", "headway_conflict"],
                "severity_distribution": {"high": 0.3, "medium": 0.5, "low": 0.2},
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
    
    def test_generate_conflicts_validation(self, client):
        """Validate input constraints."""
        # Count too high
        response = client.post(
            "/api/v1/conflicts/generate",
            json={"count": 10000}
        )
        assert response.status_code == 422  # Validation error
        
        # Count too low
        response = client.post(
            "/api/v1/conflicts/generate",
            json={"count": 0}
        )
        assert response.status_code == 422


# =============================================================================
# Test POST /conflicts/analyze
# =============================================================================

class TestAnalyzeConflict:
    """Test conflict analysis endpoint."""
    
    def test_analyze_conflict_basic(
        self, client, mock_embedding_service, mock_qdrant_service
    ):
        """Analyze a conflict with basic parameters."""
        response = client.post(
            "/api/v1/conflicts/analyze",
            json={
                "conflict_type": "platform_conflict",
                "severity": "high",
                "station": "London Waterloo",
                "time_of_day": "morning_peak",
                "affected_trains": ["IC101", "RE205"],
                "delay_before": 15,
                "description": "Platform 3 double-booked for IC101 and RE205",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "conflict_id" in data
        assert data["conflict_id"].startswith("conf-")
        assert "stored" in data
        assert "embedding_generated" in data
        assert data["embedding_generated"] is True
        assert "analysis_summary" in data
        assert "recommended_next_step" in data
    
    def test_analyze_conflict_finds_similar(
        self, client, mock_embedding_service, mock_qdrant_service
    ):
        """Analysis finds similar historical conflicts."""
        response = client.post(
            "/api/v1/conflicts/analyze",
            json={
                "conflict_type": "platform_conflict",
                "station": "Test Station",
                "time_of_day": "morning_peak",
                "affected_trains": ["T1"],
                "description": "Test conflict for similarity search",
                "find_similar": True,
                "similarity_threshold": 0.7,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "similar_conflicts_found" in data
        assert "similar_conflicts" in data
        
        if data["similar_conflicts"]:
            sc = data["similar_conflicts"][0]
            assert "conflict_id" in sc
            assert "similarity_score" in sc
            assert "explanation" in sc
    
    def test_analyze_conflict_validation(self, client):
        """Validate input constraints."""
        # Missing required fields
        response = client.post(
            "/api/v1/conflicts/analyze",
            json={
                "station": "Test",
            }
        )
        assert response.status_code == 422
        
        # Description too short
        response = client.post(
            "/api/v1/conflicts/analyze",
            json={
                "conflict_type": "platform_conflict",
                "station": "Test",
                "time_of_day": "morning_peak",
                "affected_trains": ["T1"],
                "description": "Short",
            }
        )
        assert response.status_code == 422
    
    def test_analyze_conflict_no_storage(
        self, client, mock_embedding_service, mock_qdrant_service
    ):
        """Can skip Qdrant storage."""
        response = client.post(
            "/api/v1/conflicts/analyze",
            json={
                "conflict_type": "platform_conflict",
                "station": "Test Station",
                "time_of_day": "midday",
                "affected_trains": ["T1"],
                "description": "Test conflict without storage",
                "store_in_qdrant": False,
                "find_similar": False,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["stored"] is False


# =============================================================================
# Test GET /conflicts/{conflict_id}/recommendations
# =============================================================================

class TestGetRecommendations:
    """Test recommendation retrieval endpoint."""
    
    def test_get_recommendations_not_found(self, client):
        """Returns 404 for unknown conflict."""
        response = client.get("/api/v1/conflicts/unknown-123/recommendations")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_recommendations_success(
        self, 
        client, 
        mock_embedding_service, 
        mock_qdrant_service,
        mock_recommendation_engine,
    ):
        """Get recommendations for analyzed conflict."""
        # First, analyze a conflict
        analyze_response = client.post(
            "/api/v1/conflicts/analyze",
            json={
                "conflict_type": "platform_conflict",
                "station": "Test Station",
                "time_of_day": "morning_peak",
                "affected_trains": ["T1", "T2"],
                "description": "Test conflict for recommendations",
            }
        )
        assert analyze_response.status_code == 200
        conflict_id = analyze_response.json()["conflict_id"]
        
        # Now get recommendations
        response = client.get(f"/api/v1/conflicts/{conflict_id}/recommendations")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check structure
        assert data["conflict_id"] == conflict_id
        assert "recommendations" in data
        assert "top_recommendation" in data
        assert "top_confidence" in data
        assert "executive_summary" in data
        assert "detailed_explanation" in data
        
        # Check recommendations
        if data["recommendations"]:
            rec = data["recommendations"][0]
            assert "rank" in rec
            assert "strategy" in rec
            assert "confidence" in rec
            assert "explanation" in rec
            assert rec["rank"] == 1
    
    def test_get_recommendations_limit(
        self,
        client,
        mock_embedding_service,
        mock_qdrant_service,
        mock_recommendation_engine,
    ):
        """Can limit number of recommendations."""
        # Analyze
        analyze_response = client.post(
            "/api/v1/conflicts/analyze",
            json={
                "conflict_type": "track_blockage",
                "station": "Another Station",
                "time_of_day": "evening_peak",
                "affected_trains": ["T3"],
                "description": "Track blockage for testing limit parameter",
            }
        )
        conflict_id = analyze_response.json()["conflict_id"]
        
        # Get with limit
        response = client.get(
            f"/api/v1/conflicts/{conflict_id}/recommendations",
            params={"max_recommendations": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendations"]) <= 1


# =============================================================================
# Test POST /recommendations/feedback
# =============================================================================

class TestFeedback:
    """Test feedback endpoint."""
    
    def test_submit_feedback_basic(
        self,
        client,
        mock_embedding_service,
        mock_qdrant_service,
    ):
        """Submit basic feedback."""
        # First analyze a conflict
        analyze_response = client.post(
            "/api/v1/conflicts/analyze",
            json={
                "conflict_type": "platform_conflict",
                "station": "Test Station",
                "time_of_day": "morning_peak",
                "affected_trains": ["T1"],
                "description": "Conflict for feedback testing",
            }
        )
        conflict_id = analyze_response.json()["conflict_id"]
        
        # Submit feedback
        response = client.post(
            "/api/v1/recommendations/feedback",
            json={
                "conflict_id": conflict_id,
                "strategy_applied": "platform_change",
                "outcome": "success",
                "actual_delay_after": 3,
                "resolution_time_minutes": 10,
                "notes": "Resolution worked perfectly",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "feedback_id" in data
        assert data["feedback_id"].startswith("fb-")
        assert data["status"] == "processed"  # Updated: now returns "processed"
        assert data["conflict_id"] == conflict_id
        assert "outcome_analysis" in data
        assert "golden_run_id" in data  # New: includes golden run info
        assert "learning_insights" in data  # New: includes learning insights
    
    def test_submit_feedback_with_deviation(
        self, client, mock_embedding_service, mock_qdrant_service
    ):
        """Submit feedback when different strategy was used."""
        # Analyze
        analyze_response = client.post(
            "/api/v1/conflicts/analyze",
            json={
                "conflict_type": "capacity_overload",
                "station": "Central",
                "time_of_day": "midday",
                "affected_trains": ["T5", "T6"],
                "description": "Capacity overload requiring manual resolution",
            }
        )
        conflict_id = analyze_response.json()["conflict_id"]
        
        # Submit feedback with deviation
        response = client.post(
            "/api/v1/recommendations/feedback",
            json={
                "conflict_id": conflict_id,
                "strategy_applied": "delay",
                "outcome": "partial_success",
                "actual_delay_after": 8,
                "deviation_reason": "Platform change not possible due to maintenance",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "outcome_analysis" in data
    
    def test_submit_feedback_failure(
        self, client, mock_embedding_service, mock_qdrant_service
    ):
        """Submit feedback for failed resolution."""
        # Analyze
        analyze_response = client.post(
            "/api/v1/conflicts/analyze",
            json={
                "conflict_type": "platform_conflict",
                "station": "Problem Station",
                "time_of_day": "evening_peak",
                "affected_trains": ["T7"],
                "description": "Conflict that failed to resolve",
            }
        )
        conflict_id = analyze_response.json()["conflict_id"]
        
        response = client.post(
            "/api/v1/recommendations/feedback",
            json={
                "conflict_id": conflict_id,
                "strategy_applied": "platform_change",
                "outcome": "failed",
                "actual_delay_after": 20,
                "notes": "Platform was already occupied",
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "UNSUCCESSFUL" in data["outcome_analysis"]
    
    def test_feedback_validation(self, client):
        """Validate feedback input."""
        # Missing required fields
        response = client.post(
            "/api/v1/recommendations/feedback",
            json={
                "conflict_id": "test",
            }
        )
        assert response.status_code == 422
        
        # Invalid outcome
        response = client.post(
            "/api/v1/recommendations/feedback",
            json={
                "conflict_id": "test",
                "strategy_applied": "platform_change",
                "outcome": "invalid_outcome",
                "actual_delay_after": 5,
            }
        )
        assert response.status_code == 422


# =============================================================================
# Test POST /recommendations (Quick Recommendations)
# =============================================================================

class TestQuickRecommendations:
    """Test quick recommendation endpoint."""
    
    def test_quick_recommendations(
        self, client, mock_recommendation_engine
    ):
        """Get quick recommendations without prior analysis."""
        # Patch at the recommendation module level
        with patch("app.services.recommendation_engine.get_recommendation_engine") as mock:
            from app.services.recommendation_engine import (
                RecommendationResponse,
                Recommendation,
                ScoreBreakdown,
                SimulationEvidence,
            )
            
            engine = Mock()
            engine.recommend = AsyncMock(return_value=RecommendationResponse(
                conflict_id="quick-test",
                conflict_type=ConflictType.PLATFORM_CONFLICT,
                recommendations=[
                    Recommendation(
                        rank=1,
                        strategy=ResolutionStrategy.PLATFORM_CHANGE,
                        final_score=80,
                        confidence=0.85,
                        explanation="Quick recommendation",
                        score_breakdown=ScoreBreakdown(final_score=80),
                        simulation_evidence=SimulationEvidence(
                            predicted_success=True,
                            delay_after=5,
                            delay_reduction=10,
                            recovery_time=15,
                            simulation_score=80,
                        ),
                    )
                ],
                similar_conflicts_found=2,
            ))
            mock.return_value = engine
            
            response = client.post(
                "/api/v1/recommendations/",
                json={
                    "conflict_type": "platform_conflict",
                    "station": "Quick Station",
                    "time_of_day": "morning_peak",
                    "affected_trains": ["T1"],
                    "description": "Quick test conflict",
                }
            )
        
            assert response.status_code == 200
            data = response.json()
            
            assert "recommendations" in data
            assert "executive_summary" in data
            assert "processing_time_ms" in data


# =============================================================================
# Test Health Endpoint
# =============================================================================

class TestHealth:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Health endpoint returns healthy status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


# =============================================================================
# Test Response Explanations
# =============================================================================

class TestExplanations:
    """Test that responses include human-readable explanations."""
    
    def test_generate_has_summary(
        self, client, mock_conflict_generator
    ):
        """Generate response includes summary."""
        response = client.post(
            "/api/v1/conflicts/generate",
            json={"count": 3}
        )
        
        data = response.json()
        assert "summary" in data
        assert len(data["summary"]) > 20  # Meaningful summary
    
    def test_analyze_has_explanation(
        self, client, mock_embedding_service, mock_qdrant_service
    ):
        """Analyze response includes analysis summary."""
        response = client.post(
            "/api/v1/conflicts/analyze",
            json={
                "conflict_type": "platform_conflict",
                "station": "Test",
                "time_of_day": "midday",
                "affected_trains": ["T1"],
                "description": "Test conflict for explanation",
            }
        )
        
        data = response.json()
        assert "analysis_summary" in data
        assert len(data["analysis_summary"]) > 10
        assert "recommended_next_step" in data
    
    def test_recommendations_have_explanations(
        self,
        client,
        mock_embedding_service,
        mock_qdrant_service,
        mock_recommendation_engine,
    ):
        """Recommendations include explanations."""
        # Analyze
        analyze_response = client.post(
            "/api/v1/conflicts/analyze",
            json={
                "conflict_type": "platform_conflict",
                "station": "Explain Station",
                "time_of_day": "evening_peak",
                "affected_trains": ["T1"],
                "description": "Conflict for testing explanations",
            }
        )
        conflict_id = analyze_response.json()["conflict_id"]
        
        # Get recommendations
        response = client.get(f"/api/v1/conflicts/{conflict_id}/recommendations")
        data = response.json()
        
        assert "executive_summary" in data
        assert "detailed_explanation" in data
        
        for rec in data["recommendations"]:
            assert "explanation" in rec
            assert len(rec["explanation"]) > 10
    
    def test_feedback_has_analysis(
        self, client, mock_embedding_service, mock_qdrant_service
    ):
        """Feedback response includes outcome analysis."""
        # Analyze
        analyze_response = client.post(
            "/api/v1/conflicts/analyze",
            json={
                "conflict_type": "track_blockage",
                "station": "Feedback Station",
                "time_of_day": "morning_peak",
                "affected_trains": ["T2"],
                "description": "Conflict for feedback analysis test",
            }
        )
        conflict_id = analyze_response.json()["conflict_id"]
        
        # Submit feedback
        response = client.post(
            "/api/v1/recommendations/feedback",
            json={
                "conflict_id": conflict_id,
                "strategy_applied": "speed_adjustment",
                "outcome": "success",
                "actual_delay_after": 2,
            }
        )
        
        data = response.json()
        assert "outcome_analysis" in data
        assert len(data["outcome_analysis"]) > 20
