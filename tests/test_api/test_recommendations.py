"""
Tests for recommendation API endpoints.
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from fastapi.testclient import TestClient

from app.core.constants import ConflictType, ResolutionStrategy


class TestRecommendationEndpoints:
    """Test cases for recommendation-related API endpoints."""
    
    def test_get_recommendations_valid_request(self, client: TestClient):
        """Test getting recommendations with valid request."""
        # Use the quick recommendations endpoint with patched engine
        with patch("app.services.recommendation_engine.get_recommendation_engine") as mock:
            from app.services.recommendation_engine import (
                RecommendationResponse,
                Recommendation,
                ScoreBreakdown,
                SimulationEvidence,
            )
            
            engine = Mock()
            engine.recommend = AsyncMock(return_value=RecommendationResponse(
                conflict_id="test",
                conflict_type=ConflictType.PLATFORM_CONFLICT,
                recommendations=[
                    Recommendation(
                        rank=1,
                        strategy=ResolutionStrategy.PLATFORM_CHANGE,
                        final_score=80,
                        confidence=0.85,
                        explanation="Test recommendation",
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
        
            request_data = {
                "conflict_type": "platform_conflict",
                "severity": "high",
                "station": "Central Station",
                "time_of_day": "morning_peak",
                "affected_trains": ["IC123", "RE456"],
                "description": "Platform 3 double-booked for arrivals",
            }
            
            response = client.post("/api/v1/recommendations/", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert "recommendations" in data
            assert "executive_summary" in data
    
    def test_submit_feedback(self, client: TestClient):
        """Test submitting recommendation feedback."""
        # Mock the feedback service
        with patch("app.api.routes.recommendations.get_feedback_service") as mock_feedback:
            from app.services.feedback_service import (
                FeedbackResult,
                GoldenRun,
                OutcomeComparison,
            )
            
            # Create mock feedback result
            mock_golden_run = Mock(spec=GoldenRun)
            mock_golden_run.id = "golden-123"
            mock_golden_run.is_golden = True
            mock_golden_run.delay_reduction = 10
            mock_golden_run.conflict_id = "test-conflict-id"
            mock_golden_run.strategy_applied = "platform_change"
            mock_golden_run.actual_outcome = "success"
            mock_golden_run.actual_delay_after = 5
            mock_golden_run.delay_before = 15
            mock_golden_run.delay_reduction_percentage = 66.7
            mock_golden_run.operator_notes = "Worked well"
            mock_golden_run.original_prediction = None
            mock_golden_run.model_dump = Mock(return_value={})
            
            mock_result = Mock(spec=FeedbackResult)
            mock_result.feedback_id = "fb-test123"
            mock_result.conflict_id = "test-conflict-id"
            mock_result.golden_run = mock_golden_run
            mock_result.stored_in_qdrant = True
            mock_result.comparison = None
            mock_result.prediction_was_accurate = False
            mock_result.confidence_adjustment = 0.0
            mock_result.learning_insights = ["📚 Stored as golden run"]
            
            mock_service = Mock()
            mock_service.process_feedback = AsyncMock(return_value=mock_result)
            mock_feedback.return_value = mock_service
            
            response = client.post(
                "/api/v1/recommendations/feedback",
                json={
                    "conflict_id": "test-conflict-id",
                    "strategy_applied": "platform_change",
                    "outcome": "success",
                    "actual_delay_after": 5,
                    "notes": "Worked well",
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert "outcome_analysis" in data
            assert "golden_run_id" in data
