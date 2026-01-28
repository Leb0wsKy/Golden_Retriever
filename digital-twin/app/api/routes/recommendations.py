"""
Recommendation-related API endpoints.

Handles conflict resolution recommendations and feedback collection
for continuous learning.

The feedback loop is critical for system improvement:
1. Real-world outcomes validate or correct predictions
2. Golden runs provide high-quality training data
3. Metrics track system accuracy over time
4. Confidence adjustments fine-tune recommendations
"""

import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.models.recommendation import RecommendationRequest
from app.core.constants import ResolutionStrategy, ResolutionOutcome
from app.services.embedding_service import get_embedding_service
from app.services.qdrant_service import get_qdrant_service
from app.services.feedback_service import (
    get_feedback_service,
    FeedbackResult,
    LearningMetrics,
    GoldenRun,
    OutcomeComparison,
    StrategyMetrics,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class FeedbackRequest(BaseModel):
    """
    Request model for submitting resolution feedback.
    
    Feedback is crucial for continuous learning - it helps the system
    improve its recommendations over time by learning from real outcomes.
    
    The system compares predicted vs actual outcomes to:
    - Validate prediction accuracy
    - Adjust confidence scores for similar future cases
    - Store verified outcomes as "golden runs" for future reference
    """
    conflict_id: str = Field(
        ...,
        description="ID of the conflict that was resolved"
    )
    recommendation_id: Optional[str] = Field(
        default=None,
        description="ID of the recommendation that was followed (if any)"
    )
    strategy_applied: ResolutionStrategy = Field(
        ...,
        description="The actual resolution strategy that was applied"
    )
    outcome: ResolutionOutcome = Field(
        ...,
        description="The outcome of the resolution attempt"
    )
    actual_delay_after: int = Field(
        ...,
        ge=0,
        description="Actual delay in minutes after resolution"
    )
    resolution_time_minutes: int = Field(
        default=0,
        ge=0,
        description="Time taken to implement the resolution"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Operator notes about the resolution"
    )
    deviation_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="If a different strategy was used, why?"
    )
    # Optional: Include prediction data for comparison
    predicted_outcome: Optional[ResolutionOutcome] = Field(
        default=None,
        description="What the system predicted would happen"
    )
    predicted_delay_after: Optional[int] = Field(
        default=None,
        ge=0,
        description="Predicted delay after resolution"
    )
    predicted_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Original prediction confidence"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "conflict_id": "conf-abc123",
                "recommendation_id": "rec-xyz789",
                "strategy_applied": "platform_change",
                "outcome": "success",
                "actual_delay_after": 3,
                "resolution_time_minutes": 8,
                "notes": "Platform change executed smoothly. Passengers redirected via announcements.",
                "deviation_reason": None
            }
        }


class FeedbackResponse(BaseModel):
    """
    Response model for feedback submission.
    
    Includes comparison between predicted and actual outcomes,
    golden run storage confirmation, and learning insights.
    """
    feedback_id: str = Field(..., description="Unique feedback ID")
    status: str = Field(..., description="Submission status")
    conflict_id: str = Field(..., description="Associated conflict ID")
    
    # Golden run info
    golden_run_id: Optional[str] = Field(
        default=None,
        description="ID of the stored golden run"
    )
    is_golden: bool = Field(
        default=False,
        description="Whether this is a high-quality golden run"
    )
    
    # Learning impact
    stored_in_qdrant: bool = Field(
        default=False,
        description="Whether feedback was stored for future learning"
    )
    will_improve_recommendations: bool = Field(
        default=True,
        description="Whether this feedback will influence future recommendations"
    )
    
    # Prediction comparison
    prediction_comparison: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Comparison between predicted and actual outcomes"
    )
    prediction_was_accurate: bool = Field(
        default=False,
        description="Whether the system's prediction was accurate"
    )
    confidence_adjustment: float = Field(
        default=0.0,
        description="Adjustment to confidence for similar future cases"
    )
    
    # Feedback insights
    outcome_analysis: str = Field(
        ...,
        description="Human-readable analysis of the outcome"
    )
    improvement_suggestion: Optional[str] = Field(
        default=None,
        description="System's suggestion for future similar cases"
    )
    learning_insights: List[str] = Field(
        default_factory=list,
        description="Insights about how this feedback helps the system"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "feedback_id": "fb-123abc",
                "status": "processed",
                "conflict_id": "conf-abc123",
                "golden_run_id": "golden-456def",
                "is_golden": True,
                "stored_in_qdrant": True,
                "will_improve_recommendations": True,
                "prediction_comparison": {
                    "predicted_outcome": "success",
                    "actual_outcome": "success",
                    "predicted_delay": 5,
                    "actual_delay": 3,
                    "outcome_matched": True,
                    "delay_difference": 2,
                    "overall_accuracy": "close"
                },
                "prediction_was_accurate": True,
                "confidence_adjustment": 0.105,
                "outcome_analysis": "Resolution SUCCESSFUL. Platform Change reduced delay by 12 minutes "
                                    "(80% reduction). This positive outcome will boost confidence "
                                    "in Platform Change for similar future conflicts.",
                "improvement_suggestion": "Excellent outcome! This case is now a strong evidence point for "
                                          "platform change effectiveness.",
                "learning_insights": [
                    "📚 Stored as golden run 'golden-456def' - this verified outcome will help similar future conflicts",
                    "✅ Outcome prediction correct, delay off by 2 minutes",
                    "📈 Confidence for platform change boosted by 10.5% for similar cases"
                ]
            }
        }


class QuickRecommendationRequest(BaseModel):
    """
    Quick recommendation request without requiring prior analysis.
    
    Use this for real-time recommendations when a conflict is detected.
    """
    conflict_type: str = Field(..., description="Type of conflict")
    severity: str = Field(default="medium", description="Severity level")
    station: str = Field(..., description="Station name")
    time_of_day: str = Field(..., description="Time period")
    affected_trains: List[str] = Field(default_factory=list, description="Train IDs")
    delay_before: int = Field(default=0, ge=0, description="Current delay (min)")
    description: str = Field(..., description="Conflict description")
    platform: Optional[str] = Field(default=None, description="Platform")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata (e.g., network_id)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "conflict_type": "platform_conflict",
                "severity": "high",
                "station": "London Waterloo",
                "time_of_day": "morning_peak",
                "affected_trains": ["IC101", "RE205"],
                "delay_before": 15,
                "description": "Platform 3 double-booked for arrivals",
                "platform": "3",
                "metadata": {"network_id": "FS"}
            }
        }


class QuickRecommendation(BaseModel):
    """A quick recommendation for immediate action."""
    rank: int = Field(..., ge=1)
    strategy: str = Field(...)
    confidence: float = Field(..., ge=0, le=1)
    explanation: str = Field(...)
    expected_delay_reduction: int = Field(default=0, ge=0)


class QuickRecommendationResponse(BaseModel):
    """Response for quick recommendations."""
    recommendations: List[QuickRecommendation] = Field(...)
    processing_time_ms: float = Field(...)
    similar_cases_found: int = Field(default=0)
    executive_summary: str = Field(...)


# =============================================================================
# In-Memory Feedback Storage
# =============================================================================

_feedback_store: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/", response_model=QuickRecommendationResponse)
async def get_quick_recommendations(
    request: QuickRecommendationRequest,
    top_k: int = Query(default=3, ge=1, le=10, description="Max recommendations"),
):
    """
    Get quick resolution recommendations for a conflict.
    
    This is a streamlined endpoint for real-time conflict handling.
    It bypasses the full analysis workflow and directly returns
    ranked recommendations.
    
    **Explanation:**
    The system:
    1. Embeds the conflict description
    2. Finds similar historical cases
    3. Simulates candidate resolutions
    4. Returns ranked recommendations with explanations
    
    For more detailed analysis, use:
    - POST /conflicts/analyze (to analyze and store)
    - GET /conflicts/{id}/recommendations (for full explanations)
    
    Args:
        request: Conflict details
        top_k: Maximum recommendations to return
        
    Returns:
        Ranked recommendations with explanations
    """
    import time
    start_time = time.time()
    
    try:
        from app.services.recommendation_engine import get_recommendation_engine
        
        engine = get_recommendation_engine()
        
        # Build conflict dict
        conflict_input = {
            "id": f"quick-{uuid.uuid4().hex[:8]}",
            "conflict_type": request.conflict_type,
            "severity": request.severity,
            "station": request.station,
            "time_of_day": request.time_of_day,
            "affected_trains": request.affected_trains,
            "delay_before": request.delay_before,
            "description": request.description,
            "platform": request.platform,
            "metadata": request.metadata,
        }
        
        # Get recommendations
        response = await engine.recommend(conflict_input)
        
        # Convert to quick format
        recommendations = []
        for rec in response.recommendations[:top_k]:
            recommendations.append(QuickRecommendation(
                rank=rec.rank,
                strategy=rec.strategy.value,
                confidence=rec.confidence,
                explanation=rec.explanation,
                expected_delay_reduction=rec.simulation_evidence.delay_reduction if rec.simulation_evidence else 0,
            ))
        
        # Build summary
        if recommendations:
            top = recommendations[0]
            summary = (
                f"Recommend {top.strategy.upper().replace('_', ' ')} "
                f"({top.confidence:.0%} confidence). "
                f"{top.explanation}"
            )
        else:
            summary = "Unable to generate recommendations. Consider manual assessment."
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return QuickRecommendationResponse(
            recommendations=recommendations,
            processing_time_ms=elapsed_ms,
            similar_cases_found=response.similar_conflicts_found,
            executive_summary=summary,
        )
        
    except Exception as e:
        logger.error(f"Quick recommendation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
):
    """
    Submit feedback on a resolution outcome.
    
    **The Feedback Loop - How It Works:**
    
    When you submit feedback, the system:
    
    1. **Compares predicted vs actual outcomes** - Measures prediction accuracy
    2. **Stores as golden run** - Adds to Qdrant as verified training data
    3. **Updates success metrics** - Tracks strategy effectiveness over time
    4. **Adjusts confidence scores** - Fine-tunes future recommendations
    
    **Why This Matters:**
    
    The feedback loop is the key to continuous improvement:
    
    - ✅ **Accurate predictions** → Confidence boost for similar cases
    - ❌ **Prediction misses** → Reduced confidence, system learns what NOT to do
    - 📊 **Metrics over time** → Track which strategies work best at which stations
    - 🎯 **Golden runs** → High-quality verified outcomes guide future recommendations
    
    **Example Flow:**
    
    1. System predicts: "Platform change will reduce delay to 5 min (85% confidence)"
    2. Operator applies platform change
    3. Actual result: Delay reduced to 3 min (SUCCESS)
    4. You submit feedback with outcome
    5. System compares: Predicted 5 min, actual 3 min → Better than expected!
    6. System stores this as a golden run
    7. Confidence for platform change at this station increases
    8. Next similar conflict → Higher confidence in platform change
    
    **Prediction Comparison (optional):**
    
    Include `predicted_outcome`, `predicted_delay_after`, and `predicted_confidence`
    from the original recommendation for detailed accuracy analysis.
    
    Args:
        request: Feedback details including outcome, delay, and optional notes
        
    Returns:
        Detailed response with golden run info, comparison results, and learning insights
    """
    try:
        # Get conflict data
        from app.api.routes.conflicts import _conflict_store
        
        conflict_data = {}
        if request.conflict_id in _conflict_store:
            conflict_data = _conflict_store[request.conflict_id]
        else:
            # Create minimal conflict data if not found
            conflict_data = {
                "conflict_type": "unknown",
                "severity": "medium",
                "station": "Unknown",
                "time_of_day": "off_peak",
                "affected_trains": [],
                "delay_before": request.actual_delay_after,  # Best guess
                "description": f"Conflict {request.conflict_id}",
            }
        
        # Process feedback through the feedback loop service
        feedback_service = get_feedback_service()
        
        result = await feedback_service.process_feedback(
            conflict_id=request.conflict_id,
            conflict_data=conflict_data,
            strategy_applied=request.strategy_applied,
            actual_outcome=request.outcome,
            actual_delay_after=request.actual_delay_after,
            predicted_outcome=request.predicted_outcome,
            predicted_delay_after=request.predicted_delay_after,
            predicted_confidence=request.predicted_confidence,
            resolution_time_minutes=request.resolution_time_minutes,
            operator_notes=request.notes,
            deviation_reason=request.deviation_reason,
        )
        
        # Also store in local feedback store for GET /feedback/{id}
        _feedback_store[result.feedback_id] = {
            "feedback_id": result.feedback_id,
            "conflict_id": request.conflict_id,
            "recommendation_id": request.recommendation_id,
            "strategy_applied": request.strategy_applied.value,
            "outcome": request.outcome.value,
            "actual_delay_after": request.actual_delay_after,
            "delay_reduction": result.golden_run.delay_reduction,
            "resolution_time_minutes": request.resolution_time_minutes,
            "notes": request.notes,
            "deviation_reason": request.deviation_reason,
            "submitted_at": datetime.utcnow().isoformat(),
            "golden_run_id": result.golden_run.id,
            "stored_in_qdrant": result.stored_in_qdrant,
            "prediction_was_accurate": result.prediction_was_accurate,
        }
        
        # Mark conflict as resolved if found
        if request.conflict_id in _conflict_store:
            _conflict_store[request.conflict_id]["resolved"] = True
            _conflict_store[request.conflict_id]["resolution_strategy"] = request.strategy_applied.value
            _conflict_store[request.conflict_id]["resolution_successful"] = request.outcome == ResolutionOutcome.SUCCESS
        
        # Build outcome analysis
        outcome_analysis = _build_outcome_analysis(
            request, 
            result.golden_run.delay_reduction, 
            conflict_data.get("delay_before", 0)
        )
        
        # Build improvement suggestion
        improvement_suggestion = _build_improvement_suggestion(
            request, 
            result.golden_run.delay_reduction
        )
        
        # Convert comparison to dict for response
        comparison_dict = None
        if result.comparison:
            comparison_dict = {
                "predicted_outcome": result.comparison.predicted_outcome,
                "actual_outcome": result.comparison.actual_outcome,
                "predicted_delay": result.comparison.predicted_delay,
                "actual_delay": result.comparison.actual_delay,
                "outcome_matched": result.comparison.outcome_matched,
                "delay_difference": result.comparison.delay_difference,
                "delay_accuracy_percentage": result.comparison.delay_accuracy_percentage,
                "overall_accuracy": result.comparison.overall_accuracy,
                "learning_value": result.comparison.learning_value,
            }
        
        return FeedbackResponse(
            feedback_id=result.feedback_id,
            status="processed",
            conflict_id=request.conflict_id,
            golden_run_id=result.golden_run.id,
            is_golden=result.golden_run.is_golden,
            stored_in_qdrant=result.stored_in_qdrant,
            will_improve_recommendations=True,
            prediction_comparison=comparison_dict,
            prediction_was_accurate=result.prediction_was_accurate,
            confidence_adjustment=result.confidence_adjustment,
            outcome_analysis=outcome_analysis,
            improvement_suggestion=improvement_suggestion,
            learning_insights=result.learning_insights,
        )
        
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to record feedback: {str(e)}"
        )


@router.get("/feedback/{feedback_id}")
async def get_feedback(feedback_id: str):
    """
    Retrieve submitted feedback by ID.
    
    Args:
        feedback_id: The feedback ID returned from POST /feedback
        
    Returns:
        Feedback details
    """
    if feedback_id not in _feedback_store:
        raise HTTPException(
            status_code=404,
            detail=f"Feedback '{feedback_id}' not found"
        )
    return _feedback_store[feedback_id]


@router.get("/feedback")
async def list_feedback(
    limit: int = Query(default=50, ge=1, le=500),
    conflict_id: Optional[str] = Query(default=None, description="Filter by conflict"),
    outcome: Optional[str] = Query(default=None, description="Filter by outcome"),
):
    """
    List submitted feedback.
    
    Args:
        limit: Maximum entries to return
        conflict_id: Optional filter by conflict ID
        outcome: Optional filter by outcome (success, failed, partial_success)
        
    Returns:
        List of feedback entries
    """
    feedbacks = list(_feedback_store.values())
    
    if conflict_id:
        feedbacks = [f for f in feedbacks if f["conflict_id"] == conflict_id]
    if outcome:
        feedbacks = [f for f in feedbacks if f["outcome"] == outcome]
    
    return feedbacks[:limit]


# =============================================================================
# Helper Functions
# =============================================================================

def _build_outcome_analysis(
    request: FeedbackRequest,
    delay_reduction: int,
    original_delay: int,
) -> str:
    """Build human-readable analysis of the outcome."""
    strategy_name = request.strategy_applied.value.replace('_', ' ').title()
    
    if request.outcome == ResolutionOutcome.SUCCESS:
        reduction_pct = (delay_reduction / original_delay * 100) if original_delay > 0 else 0
        analysis = (
            f"Resolution SUCCESSFUL. {strategy_name} reduced delay by {delay_reduction} minutes "
            f"({reduction_pct:.0f}% reduction). "
            f"This positive outcome will boost confidence in {strategy_name} for similar future conflicts."
        )
    elif request.outcome == ResolutionOutcome.PARTIAL_SUCCESS:
        analysis = (
            f"Resolution PARTIALLY SUCCESSFUL. {strategy_name} achieved partial delay reduction. "
            f"This outcome will be factored into future recommendations with moderate weight."
        )
    else:
        analysis = (
            f"Resolution UNSUCCESSFUL. {strategy_name} did not achieve the desired outcome. "
            f"This feedback will help the system avoid recommending this strategy "
            f"for similar situations in the future."
        )
    
    if request.notes:
        analysis += f" Operator notes recorded for context."
    
    return analysis


def _build_improvement_suggestion(
    request: FeedbackRequest,
    delay_reduction: int,
) -> Optional[str]:
    """Build suggestion for future improvements."""
    if request.outcome == ResolutionOutcome.SUCCESS and delay_reduction >= 10:
        return (
            f"Excellent outcome! This case is now a strong evidence point for "
            f"{request.strategy_applied.value.replace('_', ' ')} effectiveness."
        )
    elif request.outcome == ResolutionOutcome.FAILED and request.deviation_reason:
        return (
            f"Consider adding '{request.deviation_reason}' as a factor in "
            f"recommendation logic to prevent similar issues."
        )
    elif request.outcome == ResolutionOutcome.PARTIAL_SUCCESS:
        return (
            f"For partial successes, consider combining strategies or "
            f"adjusting timing parameters."
        )
    return None


# =============================================================================
# Metrics Endpoints
# =============================================================================

@router.get("/metrics", response_model=LearningMetrics)
async def get_learning_metrics():
    """
    Get system learning metrics.
    
    Returns comprehensive metrics about:
    
    - **Prediction Accuracy**: How often predictions match actual outcomes
    - **Strategy Effectiveness**: Success rates for each resolution strategy
    - **Delay Prediction Error**: Average error in delay predictions
    - **Trends**: Accuracy trends over 7 and 30 days
    - **Learning Rate**: Whether the system is improving over time
    
    **How This Helps:**
    
    - Identify which strategies work best at which stations
    - Spot declining accuracy early (before it impacts operations)
    - Track system improvement over time
    - Make informed decisions about model updates
    
    **Example Metrics:**
    
    ```json
    {
        "overall_prediction_accuracy": 0.78,
        "outcome_prediction_accuracy": 0.85,
        "average_delay_prediction_error": 2.3,
        "strategy_metrics": {
            "platform_change": {
                "success_rate": 0.82,
                "prediction_accuracy": 0.88
            }
        }
    }
    ```
    
    Returns:
        LearningMetrics with accuracy stats and strategy breakdown
    """
    try:
        feedback_service = get_feedback_service()
        return await feedback_service.get_metrics()
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )


@router.get("/metrics/strategy/{strategy}")
async def get_strategy_metrics(strategy: str):
    """
    Get metrics for a specific resolution strategy.
    
    Returns detailed performance data for one strategy:
    
    - Success rate across all applications
    - Average delay reduction achieved
    - Average resolution time
    - Prediction accuracy for this strategy
    - Recommended confidence adjustment
    
    Args:
        strategy: Strategy name (e.g., "platform_change", "reroute", "speed_adjustment")
        
    Returns:
        StrategyMetrics for the specified strategy
    """
    try:
        feedback_service = get_feedback_service()
        metrics = await feedback_service.get_strategy_performance(strategy)
        
        if metrics is None:
            raise HTTPException(
                status_code=404,
                detail=f"No metrics found for strategy '{strategy}'"
            )
        
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get strategy metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve strategy metrics: {str(e)}"
        )


@router.get("/golden-runs")
async def list_golden_runs(
    limit: int = Query(default=50, ge=1, le=500, description="Max results"),
    strategy: Optional[str] = Query(default=None, description="Filter by strategy"),
    outcome: Optional[str] = Query(default=None, description="Filter by outcome"),
    station: Optional[str] = Query(default=None, description="Filter by station"),
):
    """
    List stored golden runs.
    
    Golden runs are verified resolution outcomes stored for future learning.
    They represent high-quality training data where we know:
    
    - The exact conflict situation
    - The strategy that was applied
    - The actual outcome (not predicted)
    - How accurate our prediction was
    
    **Why Golden Runs Matter:**
    
    Golden runs are the foundation of continuous learning:
    
    1. **Similar case lookup**: When a new conflict arrives, we search for
       similar golden runs to see what worked before
       
    2. **Confidence calibration**: If a strategy has many successful golden
       runs at a station, we boost confidence for similar cases
       
    3. **Evidence-based learning**: Unlike simulations, golden runs are
       real-world outcomes - the most trustworthy data
    
    Args:
        limit: Maximum number of golden runs to return
        strategy: Filter by resolution strategy
        outcome: Filter by outcome (success, partial_success, failed)
        station: Filter by station name
        
    Returns:
        List of matching golden runs
    """
    try:
        feedback_service = get_feedback_service()
        runs = await feedback_service.get_golden_runs(
            limit=limit,
            strategy=strategy,
            outcome=outcome,
            station=station,
        )
        
        # Convert to dict for JSON serialization
        return [run.model_dump() for run in runs]
        
    except Exception as e:
        logger.error(f"Failed to list golden runs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve golden runs: {str(e)}"
        )


@router.get("/golden-runs/{golden_run_id}")
async def get_golden_run(golden_run_id: str):
    """
    Get a specific golden run by ID.
    
    Args:
        golden_run_id: The golden run ID
        
    Returns:
        GoldenRun details
    """
    try:
        feedback_service = get_feedback_service()
        runs = await feedback_service.get_golden_runs(limit=1000)
        
        for run in runs:
            if run.id == golden_run_id:
                return run.model_dump()
        
        raise HTTPException(
            status_code=404,
            detail=f"Golden run '{golden_run_id}' not found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get golden run: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve golden run: {str(e)}"
        )

