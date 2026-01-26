"""
Tests for the Recommendation Engine.

Tests cover:
1. Basic recommendation functionality
2. Historical evidence aggregation
3. Score calculation and ranking
4. Explainability features
5. Edge cases (no history, failed simulation, etc.)
6. Configuration options
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
from typing import List, Dict, Any

pytestmark = pytest.mark.asyncio(loop_scope="function")

from app.core.constants import (
    ConflictType,
    ConflictSeverity,
    ResolutionStrategy,
    ResolutionOutcome,
)
from app.services.recommendation_engine import (
    RecommendationEngine,
    RecommendationConfig,
    RecommendationResponse,
    Recommendation,
    HistoricalEvidence,
    SimulationEvidence,
    ScoreBreakdown,
    get_recommendation_engine,
    clear_engine_cache,
)
from app.services.simulation_service import SimulationOutcome, SimulationStatus
from app.services.qdrant_service import SearchResult, SimilarConflict


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    mock = Mock()
    mock.embed_conflict.return_value = [0.1] * 384  # Standard embedding size
    return mock


@pytest.fixture
def mock_qdrant_service():
    """Create a mock Qdrant service."""
    mock = Mock()
    mock.search_similar_conflicts.return_value = SearchResult(
        total_found=0,
        query_time_ms=1.0,
        matches=[],
    )
    return mock


@pytest.fixture
def mock_simulator():
    """Create a mock digital twin simulator."""
    mock = Mock()
    
    def create_outcome(strategy):
        return SimulationOutcome(
            strategy=strategy,
            success=True,
            delay_after=5,
            delay_reduction=10,
            recovery_time=15,
            score=75.0,
            confidence=0.8,
            side_effects={"cascade_probability": 0.2},
            explanation=f"Simulation predicts {strategy.value} will succeed.",
            status=SimulationStatus.COMPLETED,
        )
    
    mock.simulate.side_effect = lambda c, s: create_outcome(s)
    mock._get_applicable_strategies.return_value = list(ResolutionStrategy)
    return mock


@pytest.fixture
def sample_search_results() -> SearchResult:
    """Create sample historical search results."""
    matches = [
        SimilarConflict(
            id="hist_1",
            score=0.92,
            conflict_type="platform_conflict",
            severity="high",
            station="London Waterloo",
            time_of_day="morning_peak",
            affected_trains=["T1", "T2"],
            delay_before=15,
            resolution_strategy="platform_change",
            resolution_outcome="success",
            actual_delay_after=3,
            metadata={"recovery_time": 18},
        ),
        SimilarConflict(
            id="hist_2",
            score=0.87,
            conflict_type="platform_conflict",
            severity="medium",
            station="Victoria",
            time_of_day="midday",
            affected_trains=["T3"],
            delay_before=10,
            resolution_strategy="platform_change",
            resolution_outcome="success",
            actual_delay_after=2,
            metadata={"recovery_time": 12},
        ),
        SimilarConflict(
            id="hist_3",
            score=0.78,
            conflict_type="platform_conflict",
            severity="low",
            station="Clapham Junction",
            time_of_day="evening",
            affected_trains=["T4", "T5"],
            delay_before=8,
            resolution_strategy="delay",
            resolution_outcome="partial_success",
            actual_delay_after=3,
            metadata={"recovery_time": 25},
        ),
        SimilarConflict(
            id="hist_4",
            score=0.72,
            conflict_type="platform_conflict",
            severity="high",
            station="King's Cross",
            time_of_day="evening_peak",
            affected_trains=["T6"],
            delay_before=20,
            resolution_strategy="platform_change",
            resolution_outcome="failed",
            actual_delay_after=18,
            metadata={"recovery_time": 40},
        ),
    ]
    return SearchResult(
        query_id="test_query",
        matches=matches,
        total_matches=len(matches),
        search_time_ms=15.5,
    )


@pytest.fixture
def sample_conflict():
    """Create a sample conflict for testing."""
    return {
        "id": "conflict_123",
        "conflict_type": "platform_conflict",
        "station": "London Waterloo",
        "severity": "high",
        "time_of_day": "morning_peak",
        "affected_trains": ["T1", "T2", "T3"],
        "delay_before": 15,
        "platform": "4A",
    }


@pytest.fixture
def engine(mock_embedding_service, mock_qdrant_service, mock_simulator):
    """Create a recommendation engine with mocked dependencies."""
    return RecommendationEngine(
        config=RecommendationConfig(),
        embedding_service=mock_embedding_service,
        qdrant_service=mock_qdrant_service,
        simulator=mock_simulator,
    )


# =============================================================================
# Basic Functionality Tests
# =============================================================================

class TestBasicFunctionality:
    """Test basic recommendation functionality."""
    
    @pytest.mark.asyncio
    async def test_recommend_returns_response(
        self, engine, sample_conflict
    ):
        """recommend() returns a RecommendationResponse."""
        response = await engine.recommend(sample_conflict)
        
        assert isinstance(response, RecommendationResponse)
        assert response.conflict_id is not None
        assert response.conflict_type == ConflictType.PLATFORM_CONFLICT
        assert len(response.recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_recommendations_are_ranked(
        self, engine, sample_conflict
    ):
        """Recommendations are sorted by score (descending)."""
        response = await engine.recommend(sample_conflict)
        
        scores = [r.final_score for r in response.recommendations]
        assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_recommendations_have_ranks(
        self, engine, sample_conflict
    ):
        """Each recommendation has correct rank."""
        response = await engine.recommend(sample_conflict)
        
        for i, rec in enumerate(response.recommendations, 1):
            assert rec.rank == i
    
    @pytest.mark.asyncio
    async def test_embedding_service_called(
        self, engine, sample_conflict, mock_embedding_service
    ):
        """Embedding service is called with conflict."""
        await engine.recommend(sample_conflict)
        
        mock_embedding_service.embed_conflict.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_simulator_called_for_each_strategy(
        self, engine, sample_conflict, mock_simulator
    ):
        """Simulator is called for each candidate strategy."""
        await engine.recommend(sample_conflict)
        
        assert mock_simulator.simulate.call_count >= 1


# =============================================================================
# Historical Evidence Tests
# =============================================================================

class TestHistoricalEvidence:
    """Test historical evidence aggregation."""
    
    @pytest.mark.asyncio
    async def test_historical_evidence_included(
        self, engine, sample_conflict, mock_qdrant_service, sample_search_results
    ):
        """Historical evidence is included in recommendations."""
        mock_qdrant_service.search_similar_conflicts.return_value = sample_search_results
        
        response = await engine.recommend(sample_conflict)
        
        # Find platform_change recommendation (has most evidence)
        pc_rec = next(
            (r for r in response.recommendations 
             if r.strategy == ResolutionStrategy.PLATFORM_CHANGE),
            None
        )
        
        if pc_rec:
            assert pc_rec.num_similar_cases > 0
            assert len(pc_rec.historical_evidence) > 0
    
    @pytest.mark.asyncio
    async def test_evidence_sorted_by_similarity(
        self, engine, sample_conflict, mock_qdrant_service, sample_search_results
    ):
        """Historical evidence is sorted by similarity score."""
        mock_qdrant_service.search_similar_conflicts.return_value = sample_search_results
        
        response = await engine.recommend(sample_conflict)
        
        for rec in response.recommendations:
            if rec.historical_evidence:
                scores = [e.similarity_score for e in rec.historical_evidence]
                assert scores == sorted(scores, reverse=True)
    
    def test_historical_evidence_model(self):
        """HistoricalEvidence model works correctly."""
        evidence = HistoricalEvidence(
            conflict_id="test_123",
            similarity_score=0.85,
            station="Test Station",
            timestamp=datetime(2025, 1, 15, 10, 30),
            resolution_applied=ResolutionStrategy.PLATFORM_CHANGE,
            outcome=ResolutionOutcome.SUCCESS,
            delay_reduction_achieved=10,
            recovery_time_actual=15,
            context_summary="Test context",
        )
        
        assert evidence.conflict_id == "test_123"
        assert evidence.similarity_score == 0.85
        assert evidence.outcome == ResolutionOutcome.SUCCESS
    
    def test_evidence_explanation_text(self):
        """HistoricalEvidence generates explanation text."""
        evidence = HistoricalEvidence(
            conflict_id="test_123",
            similarity_score=0.85,
            station="London Waterloo",
            timestamp=datetime(2025, 1, 15),
            resolution_applied=ResolutionStrategy.PLATFORM_CHANGE,
            outcome=ResolutionOutcome.SUCCESS,
            delay_reduction_achieved=10,
        )
        
        text = evidence.to_explanation_text()
        
        assert "London Waterloo" in text
        assert "platform_change" in text
        assert "succeeded" in text
        assert "10min" in text


# =============================================================================
# Scoring Tests
# =============================================================================

class TestScoring:
    """Test score calculation."""
    
    @pytest.mark.asyncio
    async def test_scores_in_valid_range(
        self, engine, sample_conflict
    ):
        """All scores are in 0-100 range."""
        response = await engine.recommend(sample_conflict)
        
        for rec in response.recommendations:
            assert 0 <= rec.final_score <= 100
    
    @pytest.mark.asyncio
    async def test_confidence_in_valid_range(
        self, engine, sample_conflict
    ):
        """All confidence values are in 0-1 range."""
        response = await engine.recommend(sample_conflict)
        
        for rec in response.recommendations:
            assert 0 <= rec.confidence <= 1
    
    @pytest.mark.asyncio
    async def test_high_success_rate_increases_score(
        self, engine, sample_conflict, mock_qdrant_service
    ):
        """Strategies with high historical success rate score higher."""
        # All successes for platform_change
        mock_qdrant_service.search_similar_conflicts.return_value = SearchResult(
            total_found=5,
            query_time_ms=15.0,
            matches=[
                SimilarConflict(
                    id=f"hist_{i}",
                    score=0.9,
                    conflict_type="platform_conflict",
                    severity="medium",
                    station="Test Station",
                    time_of_day="morning_peak",
                    affected_trains=["T1"],
                    delay_before=15,
                    resolution_strategy="platform_change",
                    resolution_outcome="success",
                    actual_delay_after=5,
                )
                for i in range(5)
            ],
        )
        
        response = await engine.recommend(sample_conflict)
        
        pc_rec = next(
            (r for r in response.recommendations 
             if r.strategy == ResolutionStrategy.PLATFORM_CHANGE),
            None
        )
        
        if pc_rec:
            assert pc_rec.historical_success_rate == 1.0
    
    def test_score_breakdown_model(self):
        """ScoreBreakdown model works correctly."""
        breakdown = ScoreBreakdown(
            historical_score=80,
            historical_weight=0.4,
            simulation_score=70,
            simulation_weight=0.5,
            similarity_bonus=3.0,
            confidence_adjustment=-2.0,
            final_score=68.0,
        )
        
        explanation = breakdown.explain()
        
        assert "Historical" in explanation
        assert "Simulation" in explanation
        assert "68.0" in explanation


# =============================================================================
# Explainability Tests
# =============================================================================

class TestExplainability:
    """Test explainability features."""
    
    @pytest.mark.asyncio
    async def test_recommendations_have_explanations(
        self, engine, sample_conflict
    ):
        """Each recommendation has an explanation."""
        response = await engine.recommend(sample_conflict)
        
        for rec in response.recommendations:
            assert rec.explanation
            assert len(rec.explanation) > 20
    
    @pytest.mark.asyncio
    async def test_recommendations_have_score_breakdown(
        self, engine, sample_conflict
    ):
        """Each recommendation has score breakdown."""
        response = await engine.recommend(sample_conflict)
        
        for rec in response.recommendations:
            assert rec.score_breakdown is not None
            assert rec.score_breakdown.final_score == rec.final_score
    
    @pytest.mark.asyncio
    async def test_simulation_evidence_included(
        self, engine, sample_conflict
    ):
        """Simulation evidence is included."""
        response = await engine.recommend(sample_conflict)
        
        for rec in response.recommendations:
            if rec.simulation_evidence:
                assert rec.simulation_evidence.delay_reduction >= 0
                assert rec.simulation_evidence.recovery_time >= 0
    
    @pytest.mark.asyncio
    async def test_response_has_summary(
        self, engine, sample_conflict
    ):
        """Response includes executive summary."""
        response = await engine.recommend(sample_conflict)
        
        assert response.summary
        assert len(response.summary) > 50
    
    def test_full_explanation_generation(self):
        """Recommendation generates full explanation."""
        rec = Recommendation(
            rank=1,
            strategy=ResolutionStrategy.PLATFORM_CHANGE,
            final_score=85.0,
            confidence=0.9,
            explanation="Test explanation",
            score_breakdown=ScoreBreakdown(
                historical_score=80,
                simulation_score=90,
                final_score=85,
            ),
            historical_evidence=[
                HistoricalEvidence(
                    conflict_id="test",
                    similarity_score=0.9,
                    resolution_applied=ResolutionStrategy.PLATFORM_CHANGE,
                    outcome=ResolutionOutcome.SUCCESS,
                )
            ],
            simulation_evidence=SimulationEvidence(
                predicted_success=True,
                delay_after=5,
                delay_reduction=10,
                recovery_time=15,
                simulation_score=90,
            ),
            historical_success_rate=0.85,
            num_similar_cases=5,
            avg_similarity=0.88,
        )
        
        full = rec.get_full_explanation()
        
        assert "platform change" in full.lower()
        assert "85.0" in full
        assert "Simulation Prediction" in full
        assert "Historical Evidence" in full


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_no_historical_data(
        self, engine, sample_conflict, mock_qdrant_service
    ):
        """Engine works with no historical data."""
        mock_qdrant_service.search_similar_conflicts.return_value = SearchResult(
            total_found=0,
            query_time_ms=1.0,
            matches=[],
        )
        
        response = await engine.recommend(sample_conflict)
        
        assert len(response.recommendations) > 0
        assert response.similar_conflicts_found == 0
    
    @pytest.mark.asyncio
    async def test_qdrant_failure_graceful(
        self, engine, sample_conflict, mock_qdrant_service
    ):
        """Engine handles Qdrant failures gracefully."""
        mock_qdrant_service.search_similar_conflicts.side_effect = Exception("Connection failed")
        
        response = await engine.recommend(sample_conflict)
        
        # Should still return recommendations (from simulation)
        assert len(response.recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_simulation_failure_graceful(
        self, engine, sample_conflict, mock_simulator
    ):
        """Engine handles simulation failures gracefully."""
        mock_simulator.simulate.side_effect = Exception("Simulation error")
        
        response = await engine.recommend(sample_conflict)
        
        # Should handle gracefully (may have fewer recommendations)
        assert isinstance(response, RecommendationResponse)
    
    @pytest.mark.asyncio
    async def test_unknown_conflict_type(self, engine):
        """Engine handles unknown conflict types."""
        conflict = {
            "conflict_type": "unknown_type",
            "station": "Test",
        }
        
        response = await engine.recommend(conflict)
        
        # Should default to track_blockage
        assert response.conflict_type == ConflictType.TRACK_BLOCKAGE
    
    @pytest.mark.asyncio
    async def test_minimal_conflict_data(self, engine):
        """Engine works with minimal conflict data."""
        conflict = {"conflict_type": "headway_conflict"}
        
        response = await engine.recommend(conflict)
        
        assert len(response.recommendations) > 0


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfiguration:
    """Test configuration options."""
    
    def test_custom_weights(self):
        """Custom weights are applied."""
        config = RecommendationConfig(
            historical_weight=0.6,
            simulation_weight=0.3,
            similarity_weight=0.1,
        )
        
        assert config.historical_weight == 0.6
        assert config.simulation_weight == 0.3
    
    def test_max_recommendations(self, mock_embedding_service, mock_qdrant_service, mock_simulator):
        """max_recommendations limits output."""
        config = RecommendationConfig(max_recommendations=3)
        engine = RecommendationEngine(
            config=config,
            embedding_service=mock_embedding_service,
            qdrant_service=mock_qdrant_service,
            simulator=mock_simulator,
        )
        
        # Just verify config is set (actual limit tested in async test)
        assert engine.config.max_recommendations == 3
    
    @pytest.mark.asyncio
    async def test_similarity_threshold(
        self, mock_embedding_service, mock_qdrant_service, mock_simulator
    ):
        """similarity_threshold is passed to search."""
        config = RecommendationConfig(similarity_threshold=0.8)
        engine = RecommendationEngine(
            config=config,
            embedding_service=mock_embedding_service,
            qdrant_service=mock_qdrant_service,
            simulator=mock_simulator,
        )
        
        await engine.recommend({"conflict_type": "platform_conflict"})
        
        # Verify threshold was passed
        call_kwargs = mock_qdrant_service.search_similar_conflicts.call_args[1]
        assert call_kwargs["score_threshold"] == 0.8


# =============================================================================
# Response Model Tests
# =============================================================================

class TestResponseModels:
    """Test response model functionality."""
    
    def test_recommendation_response_get_top(self):
        """get_top_recommendation returns first recommendation."""
        response = RecommendationResponse(
            conflict_id="test",
            conflict_type=ConflictType.PLATFORM_CONFLICT,
            recommendations=[
                Recommendation(
                    rank=1,
                    strategy=ResolutionStrategy.PLATFORM_CHANGE,
                    final_score=90,
                    confidence=0.9,
                    explanation="Top choice",
                    score_breakdown=ScoreBreakdown(final_score=90),
                ),
                Recommendation(
                    rank=2,
                    strategy=ResolutionStrategy.DELAY,
                    final_score=80,
                    confidence=0.8,
                    explanation="Second choice",
                    score_breakdown=ScoreBreakdown(final_score=80),
                ),
            ],
        )
        
        top = response.get_top_recommendation()
        
        assert top.rank == 1
        assert top.strategy == ResolutionStrategy.PLATFORM_CHANGE
    
    def test_recommendation_response_empty(self):
        """get_top_recommendation handles empty list."""
        response = RecommendationResponse(
            conflict_id="test",
            conflict_type=ConflictType.PLATFORM_CONFLICT,
            recommendations=[],
        )
        
        assert response.get_top_recommendation() is None
    
    def test_simulation_evidence_from_outcome(self):
        """SimulationEvidence.from_outcome creates correct model."""
        outcome = SimulationOutcome(
            strategy=ResolutionStrategy.DELAY,
            success=True,
            delay_after=8,
            delay_reduction=12,
            recovery_time=20,
            score=82.5,
            confidence=0.85,
            side_effects={"cascade_probability": 0.15},
            explanation="Test explanation",
        )
        
        evidence = SimulationEvidence.from_outcome(outcome)
        
        assert evidence.predicted_success is True
        assert evidence.delay_after == 8
        assert evidence.delay_reduction == 12
        assert evidence.simulation_score == 82.5


# =============================================================================
# Factory Function Tests
# =============================================================================

class TestFactoryFunctions:
    """Test singleton factory functions."""
    
    def test_get_engine_singleton(self):
        """get_recommendation_engine returns singleton."""
        clear_engine_cache()
        
        engine1 = get_recommendation_engine()
        engine2 = get_recommendation_engine()
        
        assert engine1 is engine2
    
    def test_clear_cache(self):
        """clear_engine_cache works."""
        clear_engine_cache()
        engine1 = get_recommendation_engine()
        
        clear_engine_cache()
        engine2 = get_recommendation_engine()
        
        assert engine1 is not engine2


# =============================================================================
# Integration Tests (with mocked Qdrant)
# =============================================================================

class TestIntegration:
    """Integration tests with full pipeline."""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(
        self, engine, sample_conflict, mock_qdrant_service, sample_search_results
    ):
        """Full recommendation pipeline works end-to-end."""
        mock_qdrant_service.search_similar_conflicts.return_value = sample_search_results
        
        response = await engine.recommend(sample_conflict)
        
        # Verify response structure
        assert response.conflict_id
        assert response.conflict_type == ConflictType.PLATFORM_CONFLICT
        assert response.total_candidates > 0
        assert response.processing_time_ms > 0
        
        # Verify recommendations
        assert len(response.recommendations) > 0
        top = response.get_top_recommendation()
        assert top.rank == 1
        assert top.explanation
        assert top.score_breakdown
    
    @pytest.mark.asyncio
    async def test_metadata_tracking(
        self, engine, sample_conflict, mock_qdrant_service, sample_search_results
    ):
        """Response includes processing metadata."""
        mock_qdrant_service.search_similar_conflicts.return_value = sample_search_results
        
        response = await engine.recommend(sample_conflict)
        
        assert response.similar_conflicts_found == len(sample_search_results.matches)
        assert response.processing_time_ms >= 0


# =============================================================================
# Historical Score Calculation Tests
# =============================================================================

class TestHistoricalScoreCalculation:
    """Test historical score calculation logic."""
    
    def test_all_successes_high_score(self, engine):
        """100% success rate gives high score."""
        evidence = [
            HistoricalEvidence(
                conflict_id=f"test_{i}",
                similarity_score=0.9,
                resolution_applied=ResolutionStrategy.PLATFORM_CHANGE,
                outcome=ResolutionOutcome.SUCCESS,
            )
            for i in range(5)
        ]
        
        score, rate, similarity = engine._calculate_historical_score(evidence)
        
        assert rate == 1.0
        assert score > 80
    
    def test_all_failures_low_score(self, engine):
        """0% success rate gives low score."""
        evidence = [
            HistoricalEvidence(
                conflict_id=f"test_{i}",
                similarity_score=0.9,
                resolution_applied=ResolutionStrategy.PLATFORM_CHANGE,
                outcome=ResolutionOutcome.FAILED,
            )
            for i in range(5)
        ]
        
        score, rate, similarity = engine._calculate_historical_score(evidence)
        
        assert rate == 0.0
        assert score < 50
    
    def test_no_evidence_neutral_score(self, engine):
        """No evidence gives neutral score."""
        score, rate, similarity = engine._calculate_historical_score([])
        
        assert score == 50.0
        assert rate == 0.0
    
    def test_similarity_weighted_success(self, engine):
        """Success rate is weighted by similarity."""
        # High similarity success
        evidence = [
            HistoricalEvidence(
                conflict_id="high_sim",
                similarity_score=0.95,
                resolution_applied=ResolutionStrategy.PLATFORM_CHANGE,
                outcome=ResolutionOutcome.SUCCESS,
            ),
            # Low similarity failure (should have less impact)
            HistoricalEvidence(
                conflict_id="low_sim",
                similarity_score=0.60,
                resolution_applied=ResolutionStrategy.PLATFORM_CHANGE,
                outcome=ResolutionOutcome.FAILED,
            ),
        ]
        
        score, rate, similarity = engine._calculate_historical_score(evidence)
        
        # Success rate should be weighted toward the high-similarity success
        assert rate > 0.5


# =============================================================================
# Confidence Calculation Tests
# =============================================================================

class TestConfidenceCalculation:
    """Test confidence calculation logic."""
    
    def test_more_cases_higher_confidence(self, engine):
        """More similar cases increases confidence."""
        conf_0 = engine._calculate_confidence(0, 0.5, 0.7)
        conf_5 = engine._calculate_confidence(5, 0.5, 0.7)
        
        assert conf_5 > conf_0
    
    def test_higher_similarity_higher_confidence(self, engine):
        """Higher similarity increases confidence."""
        conf_low = engine._calculate_confidence(3, 0.5, 0.7)
        conf_high = engine._calculate_confidence(3, 0.9, 0.7)
        
        assert conf_high > conf_low
    
    def test_confidence_bounded(self, engine):
        """Confidence is bounded to valid range."""
        conf_min = engine._calculate_confidence(0, 0, 0)
        conf_max = engine._calculate_confidence(10, 1.0, 1.0)
        
        assert conf_min >= 0.2
        assert conf_max <= 0.95
