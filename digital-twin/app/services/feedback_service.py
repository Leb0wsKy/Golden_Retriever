"""
Feedback Loop Service for Golden Retriever.

This service implements a continuous learning feedback loop that:
1. Accepts actual outcomes from applied resolutions
2. Compares predicted vs actual outcomes
3. Stores resolved conflicts as "golden runs" in Qdrant
4. Tracks and updates success metrics over time

The feedback loop enables the system to learn from real-world outcomes,
improving recommendation accuracy for future conflicts.

Example:
    >>> from app.services.feedback_service import FeedbackLoopService
    >>> 
    >>> service = FeedbackLoopService()
    >>> 
    >>> # Process feedback with prediction comparison
    >>> result = await service.process_feedback(
    ...     conflict_id="conf-123",
    ...     strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
    ...     actual_outcome=ResolutionOutcome.SUCCESS,
    ...     actual_delay_after=5,
    ...     predicted_outcome=ResolutionOutcome.SUCCESS,
    ...     predicted_delay_after=3,
    ...     resolution_time_minutes=8,
    ... )
    >>> 
    >>> # Get learning metrics
    >>> metrics = await service.get_metrics()
    >>> print(f"Prediction accuracy: {metrics.prediction_accuracy:.1%}")
"""

import logging
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from pydantic import BaseModel, Field

from app.core.constants import ResolutionStrategy, ResolutionOutcome
from app.core.config import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Thresholds for outcome matching
DELAY_MATCH_THRESHOLD_MINUTES = 5  # Within 5 min = accurate prediction
DELAY_MATCH_PERCENTAGE = 0.25  # Within 25% = accurate prediction

# Golden run confidence boost
GOLDEN_RUN_CONFIDENCE_BOOST = 0.15  # 15% confidence boost for verified outcomes


# =============================================================================
# Models
# =============================================================================

class PredictionAccuracy(str, Enum):
    """How accurate was the prediction."""
    EXACT = "exact"  # Outcome and delay match exactly
    CLOSE = "close"  # Outcome matches, delay within threshold
    OUTCOME_ONLY = "outcome_only"  # Outcome matches, delay significantly different
    MISS = "miss"  # Outcome did not match


class GoldenRun(BaseModel):
    """
    A verified resolution outcome stored for future learning.
    
    Golden runs are historical conflicts where we know the actual outcome,
    making them valuable training data for improving recommendations.
    
    Attributes:
        id: Unique identifier for this golden run.
        conflict_id: Original conflict ID.
        conflict_type: Type of conflict.
        severity: Severity level.
        station: Station where conflict occurred.
        time_of_day: Time period.
        affected_trains: List of affected train IDs.
        description: Conflict description.
        delay_before: Delay before resolution (minutes).
        strategy_applied: Resolution strategy that was applied.
        actual_outcome: What actually happened.
        actual_delay_after: Real delay after resolution (minutes).
        resolution_time_minutes: How long resolution took.
        delay_reduction: Actual delay reduction achieved.
        delay_reduction_percentage: Percentage delay reduction.
        operator_notes: Notes from the operator.
        verified_at: When this outcome was verified.
        prediction_accuracy: How accurate the original prediction was.
        original_prediction: What the system originally predicted.
        is_golden: Whether this is considered a high-quality golden run.
    """
    id: str = Field(..., description="Golden run ID")
    conflict_id: str = Field(..., description="Original conflict ID")
    
    # Conflict details
    conflict_type: str = Field(..., description="Type of conflict")
    severity: str = Field(..., description="Severity level")
    station: str = Field(..., description="Station name")
    time_of_day: str = Field(..., description="Time period")
    affected_trains: List[str] = Field(default_factory=list)
    description: str = Field(default="")
    delay_before: int = Field(default=0, ge=0)
    platform: Optional[str] = Field(default=None)
    
    # Resolution details
    strategy_applied: str = Field(..., description="Strategy that was used")
    actual_outcome: str = Field(..., description="Actual outcome")
    actual_delay_after: int = Field(..., ge=0, description="Delay after resolution")
    resolution_time_minutes: Optional[int] = Field(default=None)
    
    # Computed metrics
    delay_reduction: int = Field(default=0, description="Minutes of delay reduced")
    delay_reduction_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    
    # Operator input
    operator_notes: Optional[str] = Field(default=None)
    deviation_reason: Optional[str] = Field(default=None)
    
    # Verification metadata
    verified_at: datetime = Field(default_factory=datetime.utcnow)
    prediction_accuracy: str = Field(default="unknown")
    original_prediction: Optional[Dict[str, Any]] = Field(default=None)
    
    # Quality indicators
    is_golden: bool = Field(
        default=True,
        description="High-quality run suitable for boosting confidence"
    )


class OutcomeComparison(BaseModel):
    """
    Comparison between predicted and actual outcomes.
    
    This model captures the accuracy of the system's prediction,
    enabling metrics tracking and model improvement.
    
    Attributes:
        predicted_outcome: What the system predicted.
        actual_outcome: What actually happened.
        predicted_delay: Predicted delay after resolution.
        actual_delay: Actual delay after resolution.
        outcome_matched: Whether outcomes matched.
        delay_difference: Difference between predicted and actual delay.
        delay_accuracy_percentage: How accurate the delay prediction was.
        overall_accuracy: Classification of prediction accuracy.
        learning_value: How valuable this comparison is for learning (0-1).
    """
    predicted_outcome: str = Field(..., description="Predicted outcome")
    actual_outcome: str = Field(..., description="Actual outcome")
    predicted_delay: int = Field(..., ge=0, description="Predicted delay (min)")
    actual_delay: int = Field(..., ge=0, description="Actual delay (min)")
    
    outcome_matched: bool = Field(..., description="Did outcomes match?")
    delay_difference: int = Field(..., description="Delay prediction error (min)")
    delay_accuracy_percentage: float = Field(..., description="Delay prediction accuracy")
    overall_accuracy: str = Field(..., description="Classification of accuracy")
    
    learning_value: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="How valuable for learning (higher = more valuable)"
    )
    
    insights: List[str] = Field(
        default_factory=list,
        description="Human-readable insights from comparison"
    )


class StrategyMetrics(BaseModel):
    """
    Metrics for a specific resolution strategy.
    
    Tracks how well a strategy performs in real-world conditions.
    """
    strategy: str = Field(..., description="Strategy name")
    total_applications: int = Field(default=0, ge=0)
    successful_outcomes: int = Field(default=0, ge=0)
    partial_outcomes: int = Field(default=0, ge=0)
    failed_outcomes: int = Field(default=0, ge=0)
    
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    average_delay_reduction: float = Field(default=0.0)
    average_resolution_time: float = Field(default=0.0)
    
    # Prediction accuracy for this strategy
    predictions_made: int = Field(default=0, ge=0)
    accurate_predictions: int = Field(default=0, ge=0)
    prediction_accuracy: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Confidence adjustment
    confidence_adjustment: float = Field(
        default=0.0,
        description="Adjustment to apply to future recommendations"
    )
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class LearningMetrics(BaseModel):
    """
    Overall system learning metrics.
    
    Tracks how the system is learning and improving over time.
    """
    total_feedbacks: int = Field(default=0, ge=0)
    golden_runs_stored: int = Field(default=0, ge=0)
    
    # Outcome prediction accuracy
    outcome_predictions_total: int = Field(default=0, ge=0)
    outcome_predictions_correct: int = Field(default=0, ge=0)
    outcome_prediction_accuracy: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Delay prediction accuracy
    delay_predictions_total: int = Field(default=0, ge=0)
    delay_predictions_accurate: int = Field(default=0, ge=0)  # Within threshold
    average_delay_prediction_error: float = Field(default=0.0)
    
    # Overall system accuracy
    overall_prediction_accuracy: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Strategy breakdown
    strategy_metrics: Dict[str, StrategyMetrics] = Field(default_factory=dict)
    
    # Time-based trends
    accuracy_trend_7d: Optional[float] = Field(default=None)
    accuracy_trend_30d: Optional[float] = Field(default=None)
    
    # System health
    learning_rate: float = Field(
        default=0.0,
        description="Rate of improvement over time"
    )
    data_freshness_hours: float = Field(
        default=0.0,
        description="Hours since last feedback"
    )
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class FeedbackResult(BaseModel):
    """
    Result of processing feedback.
    
    Contains the golden run, comparison results, and updated metrics.
    """
    feedback_id: str = Field(..., description="Unique feedback ID")
    conflict_id: str = Field(..., description="Original conflict ID")
    
    # Golden run
    golden_run: GoldenRun = Field(..., description="Stored golden run")
    stored_in_qdrant: bool = Field(default=False)
    
    # Comparison
    comparison: Optional[OutcomeComparison] = Field(default=None)
    prediction_was_accurate: bool = Field(default=False)
    
    # Learning impact
    confidence_adjustment: float = Field(
        default=0.0,
        description="How much to adjust confidence for similar cases"
    )
    learning_insights: List[str] = Field(default_factory=list)
    
    # Status
    status: str = Field(default="processed")
    processed_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# In-Memory Storage (for demo/testing)
# =============================================================================

# Golden runs storage
_golden_runs_store: Dict[str, GoldenRun] = {}

# Metrics storage
_metrics_store: Dict[str, Any] = {
    "total_feedbacks": 0,
    "golden_runs": 0,
    "outcome_correct": 0,
    "outcome_total": 0,
    "delay_accurate": 0,
    "delay_total": 0,
    "delay_errors": [],
    "strategy_metrics": defaultdict(lambda: {
        "total": 0,
        "success": 0,
        "partial": 0,
        "failed": 0,
        "delay_reductions": [],
        "resolution_times": [],
        "predictions_correct": 0,
        "predictions_total": 0,
    }),
    "last_feedback_at": None,
    "feedback_history": [],  # For trend calculation
}


# =============================================================================
# Feedback Loop Service
# =============================================================================

class FeedbackLoopService:
    """
    Service for processing feedback and enabling continuous learning.
    
    This service implements the core feedback loop that:
    1. Compares predicted vs actual outcomes
    2. Stores resolved conflicts as golden runs in Qdrant
    3. Updates success metrics for strategy performance
    4. Adjusts confidence scores for future recommendations
    
    The feedback loop is critical for system improvement because:
    - Real-world outcomes validate or correct predictions
    - Golden runs provide high-quality training data
    - Metrics track system accuracy over time
    - Confidence adjustments fine-tune recommendations
    
    Example:
        >>> service = FeedbackLoopService()
        >>> 
        >>> # Process feedback
        >>> result = await service.process_feedback(
        ...     conflict_id="conf-123",
        ...     conflict_data={"type": "platform_conflict", ...},
        ...     strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
        ...     actual_outcome=ResolutionOutcome.SUCCESS,
        ...     actual_delay_after=5,
        ...     predicted_outcome=ResolutionOutcome.SUCCESS,
        ...     predicted_delay_after=3,
        ... )
        >>> 
        >>> print(f"Stored golden run: {result.golden_run.id}")
        >>> print(f"Prediction accuracy: {result.comparison.overall_accuracy}")
    
    Attributes:
        embedding_service: Service for generating embeddings.
        qdrant_service: Service for vector storage.
    """
    
    def __init__(
        self,
        embedding_service: Optional[Any] = None,
        qdrant_service: Optional[Any] = None,
    ):
        """
        Initialize the feedback loop service.
        
        Services are lazily loaded if not provided.
        
        Args:
            embedding_service: Optional embedding service instance.
            qdrant_service: Optional Qdrant service instance.
        """
        self._embedding_service = embedding_service
        self._qdrant_service = qdrant_service
    
    @property
    def embedding_service(self):
        """Get or initialize embedding service."""
        if self._embedding_service is None:
            from app.services.embedding_service import get_embedding_service
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    @property
    def qdrant_service(self):
        """Get or initialize Qdrant service."""
        if self._qdrant_service is None:
            from app.services.qdrant_service import get_qdrant_service
            self._qdrant_service = get_qdrant_service()
        return self._qdrant_service
    
    # =========================================================================
    # Main Feedback Processing
    # =========================================================================
    
    async def process_feedback(
        self,
        conflict_id: str,
        conflict_data: Dict[str, Any],
        strategy_applied: ResolutionStrategy,
        actual_outcome: ResolutionOutcome,
        actual_delay_after: int,
        predicted_outcome: Optional[ResolutionOutcome] = None,
        predicted_delay_after: Optional[int] = None,
        predicted_confidence: Optional[float] = None,
        resolution_time_minutes: Optional[int] = None,
        operator_notes: Optional[str] = None,
        deviation_reason: Optional[str] = None,
    ) -> FeedbackResult:
        """
        Process feedback and store as golden run.
        
        This is the main entry point for the feedback loop. It:
        1. Creates a golden run from the feedback
        2. Compares predicted vs actual outcomes
        3. Stores the golden run in Qdrant
        4. Updates metrics and calculates confidence adjustments
        
        Args:
            conflict_id: ID of the original conflict.
            conflict_data: Full conflict data dict.
            strategy_applied: Strategy that was used.
            actual_outcome: What actually happened.
            actual_delay_after: Delay after resolution (minutes).
            predicted_outcome: What the system predicted (optional).
            predicted_delay_after: Predicted delay (optional).
            predicted_confidence: Original prediction confidence (optional).
            resolution_time_minutes: How long resolution took (optional).
            operator_notes: Operator's notes (optional).
            deviation_reason: Why outcome deviated from prediction (optional).
        
        Returns:
            FeedbackResult with golden run, comparison, and metrics.
        
        Example:
            >>> result = await service.process_feedback(
            ...     conflict_id="conf-123",
            ...     conflict_data={"conflict_type": "platform_conflict", ...},
            ...     strategy_applied=ResolutionStrategy.PLATFORM_CHANGE,
            ...     actual_outcome=ResolutionOutcome.SUCCESS,
            ...     actual_delay_after=5,
            ...     predicted_outcome=ResolutionOutcome.SUCCESS,
            ...     predicted_delay_after=3,
            ... )
        """
        feedback_id = f"fb-{uuid.uuid4().hex[:12]}"
        
        # Extract conflict details
        delay_before = conflict_data.get("delay_before", 0)
        delay_reduction = max(0, delay_before - actual_delay_after)
        delay_reduction_pct = (delay_reduction / delay_before * 100) if delay_before > 0 else 0.0
        
        # Build comparison if we have predictions
        comparison = None
        prediction_accurate = False
        confidence_adjustment = 0.0
        
        if predicted_outcome is not None and predicted_delay_after is not None:
            comparison = self._compare_outcomes(
                predicted_outcome=predicted_outcome,
                actual_outcome=actual_outcome,
                predicted_delay=predicted_delay_after,
                actual_delay=actual_delay_after,
            )
            prediction_accurate = comparison.overall_accuracy in ["exact", "close"]
            
            # Calculate confidence adjustment based on accuracy
            confidence_adjustment = self._calculate_confidence_adjustment(
                comparison=comparison,
                actual_outcome=actual_outcome,
                original_confidence=predicted_confidence,
            )
        
        # Determine if this is a high-quality golden run
        is_golden = self._is_golden_run(
            actual_outcome=actual_outcome,
            delay_reduction=delay_reduction,
            has_notes=bool(operator_notes),
            prediction_accurate=prediction_accurate,
        )
        
        # Create golden run
        golden_run = GoldenRun(
            id=f"golden-{uuid.uuid4().hex[:12]}",
            conflict_id=conflict_id,
            conflict_type=self._extract_value(conflict_data.get("conflict_type", "unknown")),
            severity=self._extract_value(conflict_data.get("severity", "medium")),
            station=conflict_data.get("station", "Unknown"),
            time_of_day=self._extract_value(conflict_data.get("time_of_day", "off_peak")),
            affected_trains=conflict_data.get("affected_trains", []),
            description=conflict_data.get("description", ""),
            delay_before=delay_before,
            platform=conflict_data.get("platform"),
            strategy_applied=strategy_applied.value,
            actual_outcome=actual_outcome.value,
            actual_delay_after=actual_delay_after,
            resolution_time_minutes=resolution_time_minutes,
            delay_reduction=delay_reduction,
            delay_reduction_percentage=delay_reduction_pct,
            operator_notes=operator_notes,
            deviation_reason=deviation_reason,
            prediction_accuracy=comparison.overall_accuracy if comparison else "unknown",
            original_prediction={
                "outcome": predicted_outcome.value if predicted_outcome else None,
                "delay_after": predicted_delay_after,
                "confidence": predicted_confidence,
            } if predicted_outcome else None,
            is_golden=is_golden,
        )
        
        # Store in memory
        _golden_runs_store[golden_run.id] = golden_run
        
        # Update metrics
        self._update_metrics(
            strategy=strategy_applied.value,
            outcome=actual_outcome,
            delay_reduction=delay_reduction,
            resolution_time=resolution_time_minutes,
            comparison=comparison,
        )
        
        # Store in Qdrant
        stored_in_qdrant = await self._store_golden_run_in_qdrant(
            golden_run=golden_run,
            conflict_data=conflict_data,
        )
        
        # Generate learning insights
        learning_insights = self._generate_learning_insights(
            golden_run=golden_run,
            comparison=comparison,
            confidence_adjustment=confidence_adjustment,
        )
        
        return FeedbackResult(
            feedback_id=feedback_id,
            conflict_id=conflict_id,
            golden_run=golden_run,
            stored_in_qdrant=stored_in_qdrant,
            comparison=comparison,
            prediction_was_accurate=prediction_accurate,
            confidence_adjustment=confidence_adjustment,
            learning_insights=learning_insights,
        )
    
    # =========================================================================
    # Outcome Comparison
    # =========================================================================
    
    def _compare_outcomes(
        self,
        predicted_outcome: ResolutionOutcome,
        actual_outcome: ResolutionOutcome,
        predicted_delay: int,
        actual_delay: int,
    ) -> OutcomeComparison:
        """
        Compare predicted vs actual outcomes.
        
        Classifies the prediction accuracy:
        - EXACT: Outcome matches AND delay within 2 minutes
        - CLOSE: Outcome matches AND delay within threshold
        - OUTCOME_ONLY: Outcome matches but delay significantly off
        - MISS: Outcome did not match
        
        Args:
            predicted_outcome: What the system predicted.
            actual_outcome: What actually happened.
            predicted_delay: Predicted delay after resolution.
            actual_delay: Actual delay after resolution.
        
        Returns:
            OutcomeComparison with accuracy classification and insights.
        """
        outcome_matched = predicted_outcome == actual_outcome
        delay_difference = abs(predicted_delay - actual_delay)
        
        # Calculate delay accuracy percentage
        if predicted_delay > 0:
            delay_accuracy = max(0, 1 - (delay_difference / predicted_delay))
        elif actual_delay == 0:
            delay_accuracy = 1.0
        else:
            delay_accuracy = 0.0
        
        # Classify overall accuracy
        if outcome_matched:
            if delay_difference <= 2:
                overall_accuracy = PredictionAccuracy.EXACT.value
            elif delay_difference <= DELAY_MATCH_THRESHOLD_MINUTES:
                overall_accuracy = PredictionAccuracy.CLOSE.value
            elif delay_accuracy >= (1 - DELAY_MATCH_PERCENTAGE):
                overall_accuracy = PredictionAccuracy.CLOSE.value
            else:
                overall_accuracy = PredictionAccuracy.OUTCOME_ONLY.value
        else:
            overall_accuracy = PredictionAccuracy.MISS.value
        
        # Calculate learning value
        # Misses are valuable for learning what NOT to do
        # Exact matches validate existing patterns
        learning_value = self._calculate_learning_value(
            accuracy=overall_accuracy,
            delay_difference=delay_difference,
            outcome_matched=outcome_matched,
        )
        
        # Generate insights
        insights = self._generate_comparison_insights(
            predicted_outcome=predicted_outcome,
            actual_outcome=actual_outcome,
            predicted_delay=predicted_delay,
            actual_delay=actual_delay,
            accuracy=overall_accuracy,
        )
        
        return OutcomeComparison(
            predicted_outcome=predicted_outcome.value,
            actual_outcome=actual_outcome.value,
            predicted_delay=predicted_delay,
            actual_delay=actual_delay,
            outcome_matched=outcome_matched,
            delay_difference=delay_difference,
            delay_accuracy_percentage=delay_accuracy * 100,
            overall_accuracy=overall_accuracy,
            learning_value=learning_value,
            insights=insights,
        )
    
    def _calculate_learning_value(
        self,
        accuracy: str,
        delay_difference: int,
        outcome_matched: bool,
    ) -> float:
        """
        Calculate how valuable this feedback is for learning.
        
        Both accurate predictions and clear misses are valuable:
        - Accurate: Confirms patterns, boosts confidence
        - Misses: Reveals weaknesses, helps avoid future errors
        """
        if accuracy == PredictionAccuracy.EXACT.value:
            return 1.0  # Perfect confirmation
        elif accuracy == PredictionAccuracy.CLOSE.value:
            return 0.9  # Strong confirmation
        elif accuracy == PredictionAccuracy.OUTCOME_ONLY.value:
            return 0.7  # Partial insight (delay calibration needed)
        else:  # MISS
            # Misses are valuable for learning
            return 0.85  # High learning value - need to understand why
    
    def _generate_comparison_insights(
        self,
        predicted_outcome: ResolutionOutcome,
        actual_outcome: ResolutionOutcome,
        predicted_delay: int,
        actual_delay: int,
        accuracy: str,
    ) -> List[str]:
        """Generate human-readable insights from the comparison."""
        insights = []
        
        if accuracy == PredictionAccuracy.EXACT.value:
            insights.append(
                "✅ Prediction was highly accurate - both outcome and delay matched"
            )
        elif accuracy == PredictionAccuracy.CLOSE.value:
            insights.append(
                f"✅ Outcome prediction correct, delay off by "
                f"{abs(predicted_delay - actual_delay)} minutes"
            )
        elif accuracy == PredictionAccuracy.OUTCOME_ONLY.value:
            insights.append(
                f"⚠️ Outcome correct but delay prediction needs calibration "
                f"(predicted {predicted_delay} min, actual {actual_delay} min)"
            )
        else:
            insights.append(
                f"❌ Outcome mismatch: predicted {predicted_outcome.value}, "
                f"actual {actual_outcome.value}"
            )
        
        # Add delay-specific insights
        delay_diff = actual_delay - predicted_delay
        if delay_diff > 5:
            insights.append(
                f"📊 Resolution took {delay_diff} min longer than predicted - "
                "consider adjusting time estimates for similar cases"
            )
        elif delay_diff < -5:
            insights.append(
                f"📊 Resolution was {-delay_diff} min faster than predicted - "
                "strategy may be undervalued for similar cases"
            )
        
        return insights
    
    # =========================================================================
    # Confidence Adjustment
    # =========================================================================
    
    def _calculate_confidence_adjustment(
        self,
        comparison: OutcomeComparison,
        actual_outcome: ResolutionOutcome,
        original_confidence: Optional[float],
    ) -> float:
        """
        Calculate confidence adjustment based on prediction accuracy.
        
        Accurate predictions boost confidence, misses reduce it.
        The magnitude depends on the severity of the error.
        
        Returns:
            Float between -0.2 and +0.2 for confidence adjustment.
        """
        if comparison.overall_accuracy == PredictionAccuracy.EXACT.value:
            # Perfect prediction - significant boost
            return GOLDEN_RUN_CONFIDENCE_BOOST
        elif comparison.overall_accuracy == PredictionAccuracy.CLOSE.value:
            # Close prediction - moderate boost
            return GOLDEN_RUN_CONFIDENCE_BOOST * 0.7
        elif comparison.overall_accuracy == PredictionAccuracy.OUTCOME_ONLY.value:
            # Outcome right but delay wrong - small boost
            return GOLDEN_RUN_CONFIDENCE_BOOST * 0.3
        else:
            # Prediction miss - reduce confidence
            # Larger reduction if original confidence was high
            base_reduction = -0.1
            if original_confidence and original_confidence > 0.8:
                return base_reduction - 0.05  # Over-confident, bigger penalty
            return base_reduction
    
    # =========================================================================
    # Golden Run Quality Assessment
    # =========================================================================
    
    def _is_golden_run(
        self,
        actual_outcome: ResolutionOutcome,
        delay_reduction: int,
        has_notes: bool,
        prediction_accurate: bool,
    ) -> bool:
        """
        Determine if this is a high-quality golden run.
        
        Golden runs are used to boost confidence in similar future cases.
        Criteria for a golden run:
        - Successful outcome with significant delay reduction, OR
        - Has operator notes providing context, OR
        - Accurate prediction confirmation
        """
        if actual_outcome == ResolutionOutcome.SUCCESS:
            if delay_reduction >= 5:  # Meaningful improvement
                return True
            if has_notes:
                return True
        
        if prediction_accurate:
            return True
        
        # Even failures can be golden if well-documented
        if actual_outcome == ResolutionOutcome.FAILED and has_notes:
            return True
        
        return False
    
    # =========================================================================
    # Qdrant Storage
    # =========================================================================
    
    async def _store_golden_run_in_qdrant(
        self,
        golden_run: GoldenRun,
        conflict_data: Dict[str, Any],
    ) -> bool:
        """
        Store golden run in Qdrant for future similarity searches.
        
        The golden run is embedded and stored with enriched metadata
        including the verified outcome, enabling the system to find
        similar resolved conflicts in the future.
        
        Args:
            golden_run: The golden run to store.
            conflict_data: Original conflict data for embedding.
        
        Returns:
            True if stored successfully, False otherwise.
        """
        try:
            # Build rich description for embedding
            embedding_text = self._build_golden_run_embedding_text(
                golden_run=golden_run,
                conflict_data=conflict_data,
            )
            
            # Generate embedding
            embedding = self.embedding_service.embed(embedding_text)
            
            # Build payload with golden run details
            payload = {
                # Original conflict info
                "conflict_id": golden_run.conflict_id,
                "conflict_type": golden_run.conflict_type,
                "severity": golden_run.severity,
                "station": golden_run.station,
                "time_of_day": golden_run.time_of_day,
                "affected_trains": golden_run.affected_trains,
                "delay_before": golden_run.delay_before,
                "description": golden_run.description,
                "platform": golden_run.platform,
                
                # Resolution details (VERIFIED)
                "resolution_strategy": golden_run.strategy_applied,
                "resolution_outcome": golden_run.actual_outcome,
                "actual_delay_after": golden_run.actual_delay_after,
                "resolution_time_minutes": golden_run.resolution_time_minutes,
                "delay_reduction": golden_run.delay_reduction,
                "delay_reduction_percentage": golden_run.delay_reduction_percentage,
                
                # Golden run metadata
                "is_golden_run": True,
                "golden_run_id": golden_run.id,
                "is_golden": golden_run.is_golden,
                "verified_at": golden_run.verified_at.isoformat(),
                "prediction_accuracy": golden_run.prediction_accuracy,
                "operator_notes": golden_run.operator_notes,
                
                # For filtering
                "has_verified_outcome": True,
            }
            
            # Store in Qdrant
            # Using a method that accepts dict payload directly
            from qdrant_client.models import PointStruct
            
            point_id = golden_run.id
            
            self.qdrant_service.ensure_collections()
            self.qdrant_service.client.upsert(
                collection_name="conflict_memory",
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload,
                    )
                ]
            )
            
            logger.info(f"Stored golden run {golden_run.id} in Qdrant")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to store golden run in Qdrant: {e}")
            return False
    
    def _build_golden_run_embedding_text(
        self,
        golden_run: GoldenRun,
        conflict_data: Dict[str, Any],
    ) -> str:
        """
        Build rich text for embedding the golden run.
        
        The text includes both the conflict description and the
        resolution outcome, so similar conflicts AND similar
        resolutions are found together.
        """
        parts = [
            f"{golden_run.conflict_type.replace('_', ' ')} at {golden_run.station}",
            f"during {golden_run.time_of_day.replace('_', ' ')}",
            f"severity {golden_run.severity}",
        ]
        
        if golden_run.description:
            parts.append(golden_run.description)
        
        # Include resolution info for better matching
        outcome_text = golden_run.actual_outcome.replace("_", " ")
        parts.append(
            f"resolved with {golden_run.strategy_applied.replace('_', ' ')} - {outcome_text}"
        )
        
        if golden_run.delay_reduction > 0:
            parts.append(f"reduced delay by {golden_run.delay_reduction} minutes")
        
        return ". ".join(parts)
    
    # =========================================================================
    # Metrics Management
    # =========================================================================
    
    def _update_metrics(
        self,
        strategy: str,
        outcome: ResolutionOutcome,
        delay_reduction: int,
        resolution_time: Optional[int],
        comparison: Optional[OutcomeComparison],
    ) -> None:
        """Update in-memory metrics with feedback data."""
        _metrics_store["total_feedbacks"] += 1
        _metrics_store["golden_runs"] += 1
        _metrics_store["last_feedback_at"] = datetime.utcnow()
        
        # Update strategy metrics
        strategy_data = _metrics_store["strategy_metrics"][strategy]
        strategy_data["total"] += 1
        strategy_data["delay_reductions"].append(delay_reduction)
        
        if resolution_time:
            strategy_data["resolution_times"].append(resolution_time)
        
        if outcome == ResolutionOutcome.SUCCESS:
            strategy_data["success"] += 1
        elif outcome == ResolutionOutcome.PARTIAL_SUCCESS:
            strategy_data["partial"] += 1
        else:
            strategy_data["failed"] += 1
        
        # Update prediction metrics if we have comparison
        if comparison:
            _metrics_store["outcome_total"] += 1
            _metrics_store["delay_total"] += 1
            _metrics_store["delay_errors"].append(comparison.delay_difference)
            
            if comparison.outcome_matched:
                _metrics_store["outcome_correct"] += 1
                strategy_data["predictions_correct"] += 1
            
            strategy_data["predictions_total"] += 1
            
            if comparison.overall_accuracy in ["exact", "close"]:
                _metrics_store["delay_accurate"] += 1
            
            # Store for trend calculation
            _metrics_store["feedback_history"].append({
                "timestamp": datetime.utcnow(),
                "outcome_correct": comparison.outcome_matched,
                "delay_accurate": comparison.overall_accuracy in ["exact", "close"],
                "strategy": strategy,
            })
    
    async def get_metrics(self) -> LearningMetrics:
        """
        Get current learning metrics.
        
        Returns:
            LearningMetrics with accuracy stats and strategy breakdown.
        """
        # Calculate overall accuracies
        outcome_accuracy = 0.0
        if _metrics_store["outcome_total"] > 0:
            outcome_accuracy = _metrics_store["outcome_correct"] / _metrics_store["outcome_total"]
        
        delay_accuracy_rate = 0.0
        if _metrics_store["delay_total"] > 0:
            delay_accuracy_rate = _metrics_store["delay_accurate"] / _metrics_store["delay_total"]
        
        avg_delay_error = 0.0
        if _metrics_store["delay_errors"]:
            avg_delay_error = sum(_metrics_store["delay_errors"]) / len(_metrics_store["delay_errors"])
        
        # Overall = weighted average
        overall_accuracy = (outcome_accuracy * 0.6 + delay_accuracy_rate * 0.4)
        
        # Build strategy metrics
        strategy_metrics = {}
        for strategy, data in _metrics_store["strategy_metrics"].items():
            if data["total"] > 0:
                success_rate = data["success"] / data["total"]
                avg_delay_red = sum(data["delay_reductions"]) / len(data["delay_reductions"])
                avg_res_time = sum(data["resolution_times"]) / len(data["resolution_times"]) if data["resolution_times"] else 0
                pred_accuracy = data["predictions_correct"] / data["predictions_total"] if data["predictions_total"] > 0 else 0
                
                # Calculate confidence adjustment
                if pred_accuracy > 0.8:
                    conf_adj = 0.1
                elif pred_accuracy > 0.6:
                    conf_adj = 0.05
                elif pred_accuracy < 0.4 and data["predictions_total"] >= 5:
                    conf_adj = -0.1
                else:
                    conf_adj = 0.0
                
                strategy_metrics[strategy] = StrategyMetrics(
                    strategy=strategy,
                    total_applications=data["total"],
                    successful_outcomes=data["success"],
                    partial_outcomes=data["partial"],
                    failed_outcomes=data["failed"],
                    success_rate=success_rate,
                    average_delay_reduction=avg_delay_red,
                    average_resolution_time=avg_res_time,
                    predictions_made=data["predictions_total"],
                    accurate_predictions=data["predictions_correct"],
                    prediction_accuracy=pred_accuracy,
                    confidence_adjustment=conf_adj,
                )
        
        # Calculate trends
        trend_7d = self._calculate_accuracy_trend(days=7)
        trend_30d = self._calculate_accuracy_trend(days=30)
        
        # Data freshness
        freshness = 0.0
        if _metrics_store["last_feedback_at"]:
            delta = datetime.utcnow() - _metrics_store["last_feedback_at"]
            freshness = delta.total_seconds() / 3600  # Hours
        
        # Learning rate (improvement over time)
        learning_rate = 0.0
        if trend_7d is not None and trend_30d is not None:
            learning_rate = trend_7d - trend_30d  # Positive = improving
        
        return LearningMetrics(
            total_feedbacks=_metrics_store["total_feedbacks"],
            golden_runs_stored=_metrics_store["golden_runs"],
            outcome_predictions_total=_metrics_store["outcome_total"],
            outcome_predictions_correct=_metrics_store["outcome_correct"],
            outcome_prediction_accuracy=outcome_accuracy,
            delay_predictions_total=_metrics_store["delay_total"],
            delay_predictions_accurate=_metrics_store["delay_accurate"],
            average_delay_prediction_error=avg_delay_error,
            overall_prediction_accuracy=overall_accuracy,
            strategy_metrics=strategy_metrics,
            accuracy_trend_7d=trend_7d,
            accuracy_trend_30d=trend_30d,
            learning_rate=learning_rate,
            data_freshness_hours=freshness,
        )
    
    def _calculate_accuracy_trend(self, days: int) -> Optional[float]:
        """Calculate accuracy trend for the given period."""
        history = _metrics_store["feedback_history"]
        if not history:
            return None
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [h for h in history if h["timestamp"] >= cutoff]
        
        if len(recent) < 3:  # Need at least 3 data points
            return None
        
        # Calculate accuracy for this period
        correct = sum(1 for h in recent if h["outcome_correct"])
        return correct / len(recent)
    
    async def get_golden_runs(
        self,
        limit: int = 100,
        strategy: Optional[str] = None,
        outcome: Optional[str] = None,
        station: Optional[str] = None,
    ) -> List[GoldenRun]:
        """
        Retrieve stored golden runs with optional filtering.
        
        Args:
            limit: Maximum number to return.
            strategy: Filter by strategy.
            outcome: Filter by outcome.
            station: Filter by station.
        
        Returns:
            List of matching golden runs.
        """
        runs = list(_golden_runs_store.values())
        
        if strategy:
            runs = [r for r in runs if r.strategy_applied == strategy]
        if outcome:
            runs = [r for r in runs if r.actual_outcome == outcome]
        if station:
            runs = [r for r in runs if r.station.lower() == station.lower()]
        
        # Sort by verification time (most recent first)
        runs.sort(key=lambda r: r.verified_at, reverse=True)
        
        return runs[:limit]
    
    async def get_strategy_performance(
        self,
        strategy: str,
    ) -> Optional[StrategyMetrics]:
        """
        Get performance metrics for a specific strategy.
        
        Args:
            strategy: Strategy name to get metrics for.
        
        Returns:
            StrategyMetrics for the strategy, or None if no data.
        """
        metrics = await self.get_metrics()
        return metrics.strategy_metrics.get(strategy)
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    def _extract_value(self, value: Any) -> str:
        """Extract string value from enum or return as-is."""
        if hasattr(value, "value"):
            return value.value
        return str(value)
    
    def _generate_learning_insights(
        self,
        golden_run: GoldenRun,
        comparison: Optional[OutcomeComparison],
        confidence_adjustment: float,
    ) -> List[str]:
        """Generate insights about how this feedback helps the system."""
        insights = []
        
        # Golden run storage insight
        insights.append(
            f"📚 Stored as golden run '{golden_run.id}' - "
            f"this verified outcome will help similar future conflicts"
        )
        
        # Comparison insights
        if comparison:
            insights.extend(comparison.insights)
        
        # Confidence adjustment insight
        if confidence_adjustment > 0:
            insights.append(
                f"📈 Confidence for {golden_run.strategy_applied.replace('_', ' ')} "
                f"boosted by {confidence_adjustment:.1%} for similar cases"
            )
        elif confidence_adjustment < 0:
            insights.append(
                f"📉 Confidence for {golden_run.strategy_applied.replace('_', ' ')} "
                f"reduced by {abs(confidence_adjustment):.1%} - will be more cautious "
                f"for similar cases"
            )
        
        # Strategy-specific insight
        strategy_data = _metrics_store["strategy_metrics"].get(golden_run.strategy_applied)
        if strategy_data and strategy_data["total"] >= 5:
            success_rate = strategy_data["success"] / strategy_data["total"]
            insights.append(
                f"📊 {golden_run.strategy_applied.replace('_', ' ')} now has "
                f"{success_rate:.0%} success rate across {strategy_data['total']} applications"
            )
        
        return insights


# =============================================================================
# Factory Function
# =============================================================================

_feedback_service_instance: Optional[FeedbackLoopService] = None


def get_feedback_service() -> FeedbackLoopService:
    """
    Get or create the feedback loop service singleton.
    
    Returns:
        FeedbackLoopService instance.
    """
    global _feedback_service_instance
    if _feedback_service_instance is None:
        _feedback_service_instance = FeedbackLoopService()
    return _feedback_service_instance


def reset_feedback_service() -> None:
    """Reset the feedback service (for testing)."""
    global _feedback_service_instance
    _feedback_service_instance = None
    _golden_runs_store.clear()
    _metrics_store["total_feedbacks"] = 0
    _metrics_store["golden_runs"] = 0
    _metrics_store["outcome_correct"] = 0
    _metrics_store["outcome_total"] = 0
    _metrics_store["delay_accurate"] = 0
    _metrics_store["delay_total"] = 0
    _metrics_store["delay_errors"] = []
    _metrics_store["strategy_metrics"] = defaultdict(lambda: {
        "total": 0,
        "success": 0,
        "partial": 0,
        "failed": 0,
        "delay_reductions": [],
        "resolution_times": [],
        "predictions_correct": 0,
        "predictions_total": 0,
    })
    _metrics_store["last_feedback_at"] = None
    _metrics_store["feedback_history"] = []
