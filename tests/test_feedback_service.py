"""
Tests for the Feedback Loop Service.

Tests the complete feedback loop including:
- Predicted vs actual outcome comparison
- Golden run storage
- Success metrics tracking
- Confidence adjustments
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from app.services.feedback_service import (
    FeedbackLoopService,
    get_feedback_service,
    reset_feedback_service,
    GoldenRun,
    OutcomeComparison,
    LearningMetrics,
    StrategyMetrics,
    FeedbackResult,
    PredictionAccuracy,
    _golden_runs_store,
    _metrics_store,
)
from app.core.constants import ResolutionStrategy, ResolutionOutcome


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_service():
    """Reset the feedback service before each test."""
    reset_feedback_service()
    yield
    reset_feedback_service()


@pytest.fixture
def feedback_service():
    """Get a fresh feedback service instance."""
    # Mock the embedding and qdrant services
    mock_embedding = Mock()
    mock_embedding.embed_text = Mock(return_value=[0.1] * 384)
    
    mock_qdrant = Mock()
    mock_qdrant.ensure_collections = Mock()
    mock_qdrant.client = Mock()
    mock_qdrant.client.upsert = Mock()
    
    return FeedbackLoopService(
        embedding_service=mock_embedding,
        qdrant_service=mock_qdrant,
    )


@pytest.fixture
def sample_conflict_data():
    """Sample conflict data for testing."""
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


# =============================================================================
# Test Outcome Comparison
# =============================================================================

class TestOutcomeComparison:
    """Tests for predicted vs actual outcome comparison."""
    
    def test_exact_match(self, feedback_service):
        """Test exact match when outcome and delay match perfectly."""
        comparison = feedback_service._compare_outcomes(
            predicted_outcome=ResolutionOutcome.SUCCESS,
            actual_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay=5,
            actual_delay=5,
        )
        
        assert comparison.outcome_matched is True
        assert comparison.delay_difference == 0
        assert comparison.overall_accuracy == "exact"
        assert comparison.learning_value == 1.0
    
    def test_close_match_within_threshold(self, feedback_service):
        """Test close match when delay is within threshold."""
        comparison = feedback_service._compare_outcomes(
            predicted_outcome=ResolutionOutcome.SUCCESS,
            actual_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay=5,
            actual_delay=3,  # 2 min difference
        )
        
        assert comparison.outcome_matched is True
        assert comparison.delay_difference == 2
        assert comparison.overall_accuracy == "exact"  # <=2 is exact
    
    def test_close_match_moderate_difference(self, feedback_service):
        """Test close match when delay difference is moderate."""
        comparison = feedback_service._compare_outcomes(
            predicted_outcome=ResolutionOutcome.SUCCESS,
            actual_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay=10,
            actual_delay=6,  # 4 min difference, within 5 min threshold
        )
        
        assert comparison.outcome_matched is True
        assert comparison.delay_difference == 4
        assert comparison.overall_accuracy == "close"
    
    def test_outcome_only_match(self, feedback_service):
        """Test when outcome matches but delay is significantly off."""
        comparison = feedback_service._compare_outcomes(
            predicted_outcome=ResolutionOutcome.SUCCESS,
            actual_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay=5,
            actual_delay=15,  # Big difference
        )
        
        assert comparison.outcome_matched is True
        assert comparison.delay_difference == 10
        assert comparison.overall_accuracy == "outcome_only"
    
    def test_prediction_miss(self, feedback_service):
        """Test when outcome does not match."""
        comparison = feedback_service._compare_outcomes(
            predicted_outcome=ResolutionOutcome.SUCCESS,
            actual_outcome=ResolutionOutcome.FAILED,
            predicted_delay=5,
            actual_delay=20,
        )
        
        assert comparison.outcome_matched is False
        assert comparison.overall_accuracy == "miss"
        # Misses still have high learning value
        assert comparison.learning_value == 0.85
    
    def test_partial_success_comparison(self, feedback_service):
        """Test comparison with partial success outcome."""
        comparison = feedback_service._compare_outcomes(
            predicted_outcome=ResolutionOutcome.PARTIAL_SUCCESS,
            actual_outcome=ResolutionOutcome.PARTIAL_SUCCESS,
            predicted_delay=10,
            actual_delay=8,
        )
        
        assert comparison.outcome_matched is True
        assert comparison.overall_accuracy in ["exact", "close"]
    
    def test_comparison_generates_insights(self, feedback_service):
        """Test that comparison generates meaningful insights."""
        comparison = feedback_service._compare_outcomes(
            predicted_outcome=ResolutionOutcome.SUCCESS,
            actual_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay=10,
            actual_delay=5,  # Better than predicted
        )
        
        assert len(comparison.insights) > 0
        # Should note the outcome was correct
        assert any("✅" in insight for insight in comparison.insights)


# =============================================================================
# Test Confidence Adjustment
# =============================================================================

class TestConfidenceAdjustment:
    """Tests for confidence adjustment calculation."""
    
    def test_exact_match_boosts_confidence(self, feedback_service):
        """Test that exact predictions boost confidence."""
        comparison = OutcomeComparison(
            predicted_outcome="success",
            actual_outcome="success",
            predicted_delay=5,
            actual_delay=5,
            outcome_matched=True,
            delay_difference=0,
            delay_accuracy_percentage=100.0,
            overall_accuracy="exact",
            learning_value=1.0,
        )
        
        adjustment = feedback_service._calculate_confidence_adjustment(
            comparison=comparison,
            actual_outcome=ResolutionOutcome.SUCCESS,
            original_confidence=0.8,
        )
        
        assert adjustment > 0
        assert adjustment == 0.15  # GOLDEN_RUN_CONFIDENCE_BOOST
    
    def test_close_match_moderate_boost(self, feedback_service):
        """Test that close predictions give moderate boost."""
        comparison = OutcomeComparison(
            predicted_outcome="success",
            actual_outcome="success",
            predicted_delay=5,
            actual_delay=8,
            outcome_matched=True,
            delay_difference=3,
            delay_accuracy_percentage=70.0,
            overall_accuracy="close",
            learning_value=0.9,
        )
        
        adjustment = feedback_service._calculate_confidence_adjustment(
            comparison=comparison,
            actual_outcome=ResolutionOutcome.SUCCESS,
            original_confidence=0.8,
        )
        
        assert adjustment > 0
        assert adjustment < 0.15  # Less than exact match
    
    def test_miss_reduces_confidence(self, feedback_service):
        """Test that prediction misses reduce confidence."""
        comparison = OutcomeComparison(
            predicted_outcome="success",
            actual_outcome="failed",
            predicted_delay=5,
            actual_delay=20,
            outcome_matched=False,
            delay_difference=15,
            delay_accuracy_percentage=0.0,
            overall_accuracy="miss",
            learning_value=0.85,
        )
        
        adjustment = feedback_service._calculate_confidence_adjustment(
            comparison=comparison,
            actual_outcome=ResolutionOutcome.FAILED,
            original_confidence=0.8,
        )
        
        assert adjustment < 0
    
    def test_overconfident_miss_bigger_penalty(self, feedback_service):
        """Test that high-confidence misses get bigger penalty."""
        comparison = OutcomeComparison(
            predicted_outcome="success",
            actual_outcome="failed",
            predicted_delay=5,
            actual_delay=20,
            outcome_matched=False,
            delay_difference=15,
            delay_accuracy_percentage=0.0,
            overall_accuracy="miss",
            learning_value=0.85,
        )
        
        # High confidence miss
        high_conf_adj = feedback_service._calculate_confidence_adjustment(
            comparison=comparison,
            actual_outcome=ResolutionOutcome.FAILED,
            original_confidence=0.9,  # High confidence
        )
        
        # Low confidence miss
        low_conf_adj = feedback_service._calculate_confidence_adjustment(
            comparison=comparison,
            actual_outcome=ResolutionOutcome.FAILED,
            original_confidence=0.5,  # Low confidence
        )
        
        # High confidence miss should have bigger penalty
        assert abs(high_conf_adj) > abs(low_conf_adj)


# =============================================================================
# Test Golden Run Storage
# =============================================================================

class TestGoldenRunStorage:
    """Tests for golden run creation and storage."""
    
    @pytest.mark.asyncio
    async def test_creates_golden_run(self, feedback_service, sample_conflict_data):
        """Test that feedback creates a golden run."""
        result = await feedback_service.process_feedback(
            conflict_id="conf-123",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=3,
        )
        
        assert result.golden_run is not None
        assert result.golden_run.conflict_id == "conf-123"
        assert result.golden_run.strategy_applied == "platform_change"
        assert result.golden_run.actual_outcome == "success"
        assert result.golden_run.actual_delay_after == 3
    
    @pytest.mark.asyncio
    async def test_golden_run_calculates_delay_reduction(
        self, feedback_service, sample_conflict_data
    ):
        """Test that golden run calculates delay reduction."""
        sample_conflict_data["delay_before"] = 15
        
        result = await feedback_service.process_feedback(
            conflict_id="conf-123",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=3,
        )
        
        assert result.golden_run.delay_before == 15
        assert result.golden_run.delay_reduction == 12
        assert result.golden_run.delay_reduction_percentage == 80.0
    
    @pytest.mark.asyncio
    async def test_successful_outcome_is_golden(
        self, feedback_service, sample_conflict_data
    ):
        """Test that successful outcomes with good reduction are marked golden."""
        sample_conflict_data["delay_before"] = 20
        
        result = await feedback_service.process_feedback(
            conflict_id="conf-123",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=10,  # 10 min reduction
        )
        
        assert result.golden_run.is_golden is True
    
    @pytest.mark.asyncio
    async def test_operator_notes_preserved(
        self, feedback_service, sample_conflict_data
    ):
        """Test that operator notes are preserved in golden run."""
        result = await feedback_service.process_feedback(
            conflict_id="conf-123",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
            operator_notes="Smooth execution, passengers cooperative",
        )
        
        assert result.golden_run.operator_notes == "Smooth execution, passengers cooperative"
    
    @pytest.mark.asyncio
    async def test_golden_run_stores_prediction_info(
        self, feedback_service, sample_conflict_data
    ):
        """Test that original prediction is stored in golden run."""
        result = await feedback_service.process_feedback(
            conflict_id="conf-123",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=3,
            predicted_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay_after=5,
            predicted_confidence=0.85,
        )
        
        assert result.golden_run.original_prediction is not None
        assert result.golden_run.original_prediction["outcome"] == "success"
        assert result.golden_run.original_prediction["delay_after"] == 5
        assert result.golden_run.original_prediction["confidence"] == 0.85
    
    @pytest.mark.asyncio
    async def test_golden_run_stored_in_memory(
        self, feedback_service, sample_conflict_data
    ):
        """Test that golden run is stored in memory store."""
        result = await feedback_service.process_feedback(
            conflict_id="conf-123",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
        )
        
        # Check it's in the store
        assert result.golden_run.id in _golden_runs_store
        stored = _golden_runs_store[result.golden_run.id]
        assert stored.conflict_id == "conf-123"
    
    @pytest.mark.asyncio
    async def test_stores_in_qdrant(self, feedback_service, sample_conflict_data):
        """Test that golden run is stored in Qdrant."""
        result = await feedback_service.process_feedback(
            conflict_id="conf-123",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
        )
        
        # Verify Qdrant upsert was called
        assert feedback_service.qdrant_service.client.upsert.called
        assert result.stored_in_qdrant is True


# =============================================================================
# Test Metrics Tracking
# =============================================================================

class TestMetricsTracking:
    """Tests for metrics tracking and calculation."""
    
    @pytest.mark.asyncio
    async def test_tracks_total_feedbacks(
        self, feedback_service, sample_conflict_data
    ):
        """Test that total feedbacks are tracked."""
        # Submit 3 feedbacks
        for i in range(3):
            await feedback_service.process_feedback(
                conflict_id=f"conf-{i}",
                conflict_data=sample_conflict_data,
                strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
                actual_outcome=ResolutionOutcome.SUCCESS,
                actual_delay_after=5,
            )
        
        metrics = await feedback_service.get_metrics()
        assert metrics.total_feedbacks == 3
        assert metrics.golden_runs_stored == 3
    
    @pytest.mark.asyncio
    async def test_tracks_strategy_success_rate(
        self, feedback_service, sample_conflict_data
    ):
        """Test that strategy success rates are tracked."""
        # 2 successes, 1 failure for platform_change
        await feedback_service.process_feedback(
            conflict_id="conf-1",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
        )
        await feedback_service.process_feedback(
            conflict_id="conf-2",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=3,
        )
        await feedback_service.process_feedback(
            conflict_id="conf-3",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.FAILED,
            actual_delay_after=20,
        )
        
        metrics = await feedback_service.get_metrics()
        platform_metrics = metrics.strategy_metrics.get("platform_change")
        
        assert platform_metrics is not None
        assert platform_metrics.total_applications == 3
        assert platform_metrics.successful_outcomes == 2
        assert platform_metrics.failed_outcomes == 1
        assert platform_metrics.success_rate == pytest.approx(2/3, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_tracks_prediction_accuracy(
        self, feedback_service, sample_conflict_data
    ):
        """Test that prediction accuracy is tracked."""
        # Accurate prediction
        await feedback_service.process_feedback(
            conflict_id="conf-1",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
            predicted_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay_after=5,
        )
        # Inaccurate prediction
        await feedback_service.process_feedback(
            conflict_id="conf-2",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.FAILED,
            actual_delay_after=20,
            predicted_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay_after=5,
        )
        
        metrics = await feedback_service.get_metrics()
        
        assert metrics.outcome_predictions_total == 2
        assert metrics.outcome_predictions_correct == 1
        assert metrics.outcome_prediction_accuracy == 0.5
    
    @pytest.mark.asyncio
    async def test_tracks_average_delay_error(
        self, feedback_service, sample_conflict_data
    ):
        """Test that average delay prediction error is tracked."""
        await feedback_service.process_feedback(
            conflict_id="conf-1",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
            predicted_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay_after=3,  # 2 min error
        )
        await feedback_service.process_feedback(
            conflict_id="conf-2",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=10,
            predicted_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay_after=6,  # 4 min error
        )
        
        metrics = await feedback_service.get_metrics()
        
        # Average error should be (2 + 4) / 2 = 3
        assert metrics.average_delay_prediction_error == 3.0
    
    @pytest.mark.asyncio
    async def test_tracks_multiple_strategies(
        self, feedback_service, sample_conflict_data
    ):
        """Test tracking metrics for multiple strategies."""
        # Platform change
        await feedback_service.process_feedback(
            conflict_id="conf-1",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
        )
        # Reroute
        await feedback_service.process_feedback(
            conflict_id="conf-2",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.REROUTE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=8,
        )
        # Speed adjustment
        await feedback_service.process_feedback(
            conflict_id="conf-3",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.SPEED_ADJUSTMENT,
            actual_outcome=ResolutionOutcome.PARTIAL_SUCCESS,
            actual_delay_after=10,
        )
        
        metrics = await feedback_service.get_metrics()
        
        assert "platform_change" in metrics.strategy_metrics
        assert "reroute" in metrics.strategy_metrics
        assert "speed_adjustment" in metrics.strategy_metrics
    
    @pytest.mark.asyncio
    async def test_data_freshness_tracked(
        self, feedback_service, sample_conflict_data
    ):
        """Test that data freshness is tracked."""
        await feedback_service.process_feedback(
            conflict_id="conf-1",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
        )
        
        metrics = await feedback_service.get_metrics()
        
        # Should be very fresh (just submitted)
        assert metrics.data_freshness_hours < 0.1  # Less than 6 minutes
    
    @pytest.mark.asyncio
    async def test_strategy_confidence_adjustment(
        self, feedback_service, sample_conflict_data
    ):
        """Test that strategy confidence adjustment is calculated."""
        # Submit several accurate predictions to build up good record
        for i in range(6):
            await feedback_service.process_feedback(
                conflict_id=f"conf-{i}",
                conflict_data=sample_conflict_data,
                strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
                actual_outcome=ResolutionOutcome.SUCCESS,
                actual_delay_after=5,
                predicted_outcome=ResolutionOutcome.SUCCESS,
                predicted_delay_after=5,
            )
        
        metrics = await feedback_service.get_metrics()
        platform_metrics = metrics.strategy_metrics.get("platform_change")
        
        # High accuracy should result in positive confidence adjustment
        assert platform_metrics.prediction_accuracy == 1.0
        assert platform_metrics.confidence_adjustment > 0


# =============================================================================
# Test Learning Insights
# =============================================================================

class TestLearningInsights:
    """Tests for learning insights generation."""
    
    @pytest.mark.asyncio
    async def test_generates_storage_insight(
        self, feedback_service, sample_conflict_data
    ):
        """Test that storage insight is generated."""
        result = await feedback_service.process_feedback(
            conflict_id="conf-123",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
        )
        
        assert len(result.learning_insights) > 0
        assert any("golden run" in insight.lower() for insight in result.learning_insights)
    
    @pytest.mark.asyncio
    async def test_generates_confidence_insight_for_boost(
        self, feedback_service, sample_conflict_data
    ):
        """Test confidence boost insight when prediction is accurate."""
        result = await feedback_service.process_feedback(
            conflict_id="conf-123",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
            predicted_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay_after=5,
        )
        
        # Should have insight about confidence boost
        assert any("📈" in insight or "boost" in insight.lower() 
                   for insight in result.learning_insights)
    
    @pytest.mark.asyncio
    async def test_generates_insight_for_miss(
        self, feedback_service, sample_conflict_data
    ):
        """Test insight generation when prediction misses."""
        result = await feedback_service.process_feedback(
            conflict_id="conf-123",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.FAILED,
            actual_delay_after=20,
            predicted_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay_after=5,
        )
        
        # Should have insight about confidence reduction or miss
        insights_text = " ".join(result.learning_insights).lower()
        assert "📉" in " ".join(result.learning_insights) or "cautious" in insights_text or "reduced" in insights_text


# =============================================================================
# Test Golden Run Retrieval
# =============================================================================

class TestGoldenRunRetrieval:
    """Tests for retrieving stored golden runs."""
    
    @pytest.mark.asyncio
    async def test_get_golden_runs(self, feedback_service, sample_conflict_data):
        """Test retrieving golden runs."""
        # Store some golden runs
        for i in range(3):
            await feedback_service.process_feedback(
                conflict_id=f"conf-{i}",
                conflict_data=sample_conflict_data,
                strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
                actual_outcome=ResolutionOutcome.SUCCESS,
                actual_delay_after=5,
            )
        
        runs = await feedback_service.get_golden_runs()
        assert len(runs) == 3
    
    @pytest.mark.asyncio
    async def test_filter_by_strategy(self, feedback_service, sample_conflict_data):
        """Test filtering golden runs by strategy."""
        # Platform change
        await feedback_service.process_feedback(
            conflict_id="conf-1",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
        )
        # Reroute
        await feedback_service.process_feedback(
            conflict_id="conf-2",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.REROUTE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
        )
        
        platform_runs = await feedback_service.get_golden_runs(strategy="platform_change")
        reroute_runs = await feedback_service.get_golden_runs(strategy="reroute")
        
        assert len(platform_runs) == 1
        assert len(reroute_runs) == 1
        assert platform_runs[0].strategy_applied == "platform_change"
        assert reroute_runs[0].strategy_applied == "reroute"
    
    @pytest.mark.asyncio
    async def test_filter_by_outcome(self, feedback_service, sample_conflict_data):
        """Test filtering golden runs by outcome."""
        # Success
        await feedback_service.process_feedback(
            conflict_id="conf-1",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
        )
        # Failed
        await feedback_service.process_feedback(
            conflict_id="conf-2",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.FAILED,
            actual_delay_after=20,
        )
        
        success_runs = await feedback_service.get_golden_runs(outcome="success")
        failed_runs = await feedback_service.get_golden_runs(outcome="failed")
        
        assert len(success_runs) == 1
        assert len(failed_runs) == 1
    
    @pytest.mark.asyncio
    async def test_filter_by_station(self, feedback_service, sample_conflict_data):
        """Test filtering golden runs by station."""
        # Station 1
        data1 = {**sample_conflict_data, "station": "King's Cross"}
        await feedback_service.process_feedback(
            conflict_id="conf-1",
            conflict_data=data1,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
        )
        # Station 2
        data2 = {**sample_conflict_data, "station": "Paddington"}
        await feedback_service.process_feedback(
            conflict_id="conf-2",
            conflict_data=data2,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
        )
        
        kings_runs = await feedback_service.get_golden_runs(station="King's Cross")
        paddington_runs = await feedback_service.get_golden_runs(station="Paddington")
        
        assert len(kings_runs) == 1
        assert len(paddington_runs) == 1
    
    @pytest.mark.asyncio
    async def test_limit_results(self, feedback_service, sample_conflict_data):
        """Test limiting golden run results."""
        # Store 5 golden runs
        for i in range(5):
            await feedback_service.process_feedback(
                conflict_id=f"conf-{i}",
                conflict_data=sample_conflict_data,
                strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
                actual_outcome=ResolutionOutcome.SUCCESS,
                actual_delay_after=5,
            )
        
        runs = await feedback_service.get_golden_runs(limit=3)
        assert len(runs) == 3


# =============================================================================
# Test Factory Function
# =============================================================================

class TestFactoryFunction:
    """Tests for the factory function."""
    
    def test_get_feedback_service_returns_instance(self):
        """Test that factory returns a service instance."""
        service = get_feedback_service()
        assert service is not None
        assert isinstance(service, FeedbackLoopService)
    
    def test_get_feedback_service_returns_singleton(self):
        """Test that factory returns same instance."""
        service1 = get_feedback_service()
        service2 = get_feedback_service()
        assert service1 is service2
    
    def test_reset_clears_singleton(self):
        """Test that reset clears the singleton."""
        service1 = get_feedback_service()
        reset_feedback_service()
        service2 = get_feedback_service()
        # After reset, should be different instance
        # (or same type, but stores cleared)
        assert _metrics_store["total_feedbacks"] == 0
        assert len(_golden_runs_store) == 0


# =============================================================================
# Test Feedback Result Model
# =============================================================================

class TestFeedbackResultModel:
    """Tests for the FeedbackResult model."""
    
    @pytest.mark.asyncio
    async def test_feedback_result_structure(
        self, feedback_service, sample_conflict_data
    ):
        """Test that feedback result has expected structure."""
        result = await feedback_service.process_feedback(
            conflict_id="conf-123",
            conflict_data=sample_conflict_data,
            strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            actual_outcome=ResolutionOutcome.SUCCESS,
            actual_delay_after=5,
            predicted_outcome=ResolutionOutcome.SUCCESS,
            predicted_delay_after=5,
        )
        
        # Check all expected fields
        assert result.feedback_id is not None
        assert result.conflict_id == "conf-123"
        assert result.golden_run is not None
        assert result.stored_in_qdrant is True
        assert result.comparison is not None
        assert isinstance(result.prediction_was_accurate, bool)
        assert isinstance(result.confidence_adjustment, float)
        assert isinstance(result.learning_insights, list)
        assert result.status == "processed"
        assert result.processed_at is not None
