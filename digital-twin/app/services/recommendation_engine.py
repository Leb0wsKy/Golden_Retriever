"""
Recommendation Engine for Rail Conflict Resolution.

This module implements an AI-powered recommendation engine that combines:
1. Semantic similarity search (via Qdrant vector database)
2. Historical success analysis
3. Digital twin simulation
4. Explainable AI techniques

The engine produces ranked, explainable recommendations that help operators
understand WHY a particular resolution is suggested, not just WHAT to do.

Explainability Architecture:
---------------------------
The engine achieves explainability through multiple layers:

1. **Provenance Tracking**: Every recommendation traces back to the specific
   historical conflicts that influenced it. Operators can see "This worked
   for conflict X at station Y on date Z."

2. **Similarity Explanation**: The semantic similarity score shows how closely
   the current conflict matches historical cases. High similarity means the
   historical evidence is more relevant.

3. **Historical Success Metrics**: For each resolution, we aggregate success
   rates from similar past conflicts. "This strategy succeeded 85% of the time
   in similar situations."

4. **Simulation Transparency**: The digital twin provides predicted outcomes
   with detailed breakdowns (delay_after, recovery_time, side_effects).
   Operators see what the simulation expects to happen.

5. **Score Decomposition**: The final ranking score is broken down into
   components (historical_weight, simulation_weight) so operators understand
   what factors contributed to each recommendation.

6. **Confidence Indicators**: Each recommendation includes confidence levels
   based on (a) number of similar historical cases, (b) similarity scores,
   and (c) simulation confidence.

7. **Natural Language Explanations**: Human-readable text explains the
   recommendation in plain English, suitable for operator dashboards.

Usage:
------
    >>> engine = RecommendationEngine()
    >>> 
    >>> # Get recommendations for a conflict
    >>> recommendations = await engine.recommend(conflict)
    >>> 
    >>> # Top recommendation with explanation
    >>> top = recommendations[0]
    >>> print(f"Recommended: {top.strategy}")
    >>> print(f"Confidence: {top.confidence:.0%}")
    >>> print(f"Explanation: {top.explanation}")
    >>> 
    >>> # Detailed evidence
    >>> for evidence in top.historical_evidence:
    ...     print(f"  Similar case: {evidence.conflict_id}")
    ...     print(f"  Similarity: {evidence.similarity:.0%}")
    ...     print(f"  Outcome: {evidence.outcome}")
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.constants import (
    ConflictType,
    ConflictSeverity,
    ResolutionStrategy,
    ResolutionOutcome,
    DEFAULT_SIMILARITY_THRESHOLD,
)
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.qdrant_service import QdrantService, get_qdrant_service, SearchResult, SimilarConflict
from app.services.simulation_service import (
    DigitalTwinSimulator,
    SimulationOutcome,
    SimulationInput,
    ResolutionCandidate,
    get_digital_twin_simulator,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Explainability Models
# =============================================================================

class HistoricalEvidence(BaseModel):
    """
    Evidence from a similar historical conflict.
    
    This model captures the provenance information that makes recommendations
    explainable. Operators can see exactly which past cases influenced the
    recommendation.
    
    Attributes:
        conflict_id: Unique identifier of the historical conflict.
        similarity_score: How similar this case is to the current conflict (0-1).
        station: Station where the historical conflict occurred.
        timestamp: When the historical conflict occurred.
        resolution_applied: What resolution was applied.
        outcome: Whether the resolution succeeded or failed.
        delay_reduction_achieved: Actual delay reduction in that case.
        context_summary: Brief description of the historical case.
    """
    conflict_id: str = Field(..., description="ID of the historical conflict")
    similarity_score: float = Field(..., ge=0, le=1, description="Semantic similarity (0-1)")
    station: str = Field(default="Unknown", description="Station of historical conflict")
    timestamp: Optional[datetime] = Field(default=None, description="When it occurred")
    resolution_applied: ResolutionStrategy = Field(..., description="Strategy that was used")
    outcome: ResolutionOutcome = Field(..., description="Success/failure of resolution")
    delay_reduction_achieved: int = Field(default=0, ge=0, description="Actual delay reduced (min)")
    recovery_time_actual: int = Field(default=0, ge=0, description="Actual recovery time (min)")
    context_summary: str = Field(default="", description="Brief description of the case")
    
    def to_explanation_text(self) -> str:
        """Generate human-readable explanation of this evidence."""
        outcome_text = "succeeded" if self.outcome == ResolutionOutcome.SUCCESS else "failed"
        time_text = self.timestamp.strftime("%Y-%m-%d") if self.timestamp else "unknown date"
        
        return (
            f"At {self.station} on {time_text}, applying {self.resolution_applied.value} "
            f"{outcome_text} with {self.delay_reduction_achieved}min delay reduction "
            f"(similarity: {self.similarity_score:.0%})"
        )


class SimulationEvidence(BaseModel):
    """
    Evidence from digital twin simulation.
    
    Captures the predicted outcomes from running the resolution through
    the simulation engine.
    
    Attributes:
        predicted_success: Whether simulation predicts success.
        delay_after: Predicted remaining delay.
        delay_reduction: Predicted delay reduction.
        recovery_time: Predicted time to normal operations.
        simulation_score: Raw score from simulator (0-100).
        side_effects: Predicted side effects.
        confidence: Simulation confidence level.
        explanation: Simulator's explanation text.
    """
    predicted_success: bool = Field(..., description="Simulation predicts success")
    delay_after: int = Field(..., ge=0, description="Predicted delay after (min)")
    delay_reduction: int = Field(..., ge=0, description="Predicted reduction (min)")
    recovery_time: int = Field(..., ge=0, description="Predicted recovery (min)")
    simulation_score: float = Field(..., ge=0, le=100, description="Simulator score")
    side_effects: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.8, ge=0, le=1)
    explanation: str = Field(default="")
    
    @classmethod
    def from_outcome(cls, outcome: SimulationOutcome) -> "SimulationEvidence":
        """Create from SimulationOutcome."""
        return cls(
            predicted_success=outcome.success,
            delay_after=outcome.delay_after,
            delay_reduction=outcome.delay_reduction,
            recovery_time=outcome.recovery_time,
            simulation_score=outcome.score,
            side_effects=outcome.side_effects,
            confidence=outcome.confidence,
            explanation=outcome.explanation,
        )


class ScoreBreakdown(BaseModel):
    """
    Breakdown of how the final score was calculated.
    
    This provides transparency into the ranking algorithm, showing
    operators exactly how much each factor contributed.
    
    Attributes:
        historical_score: Score component from historical success.
        historical_weight: Weight applied to historical score.
        simulation_score: Score component from simulation.
        simulation_weight: Weight applied to simulation score.
        similarity_bonus: Bonus for high similarity matches.
        confidence_adjustment: Adjustment based on confidence.
        final_score: The combined final score.
    """
    historical_score: float = Field(default=0, description="Historical success score (0-100)")
    historical_weight: float = Field(default=0.4, description="Weight for historical")
    simulation_score: float = Field(default=0, description="Simulation score (0-100)")
    simulation_weight: float = Field(default=0.5, description="Weight for simulation")
    similarity_bonus: float = Field(default=0, description="Bonus for high similarity")
    confidence_adjustment: float = Field(default=0, description="Confidence-based adjustment")
    final_score: float = Field(default=0, description="Final combined score")
    
    def explain(self) -> str:
        """Generate explanation of score calculation."""
        parts = [
            f"Historical: {self.historical_score:.1f} × {self.historical_weight:.0%} = {self.historical_score * self.historical_weight:.1f}",
            f"Simulation: {self.simulation_score:.1f} × {self.simulation_weight:.0%} = {self.simulation_score * self.simulation_weight:.1f}",
        ]
        if self.similarity_bonus > 0:
            parts.append(f"Similarity bonus: +{self.similarity_bonus:.1f}")
        if self.confidence_adjustment != 0:
            parts.append(f"Confidence adjustment: {self.confidence_adjustment:+.1f}")
        parts.append(f"Final: {self.final_score:.1f}")
        return " | ".join(parts)


class Recommendation(BaseModel):
    """
    A single resolution recommendation with full explainability.
    
    This is the main output of the recommendation engine. Each recommendation
    includes not just the suggested strategy, but comprehensive evidence and
    explanations for why it's recommended.
    
    Attributes:
        rank: Position in the ranked list (1 = best).
        strategy: The recommended resolution strategy.
        final_score: Combined score for ranking (0-100).
        confidence: Overall confidence in this recommendation (0-1).
        
        # Explainability fields
        explanation: Human-readable explanation text.
        score_breakdown: Detailed breakdown of score calculation.
        historical_evidence: List of similar historical cases.
        simulation_evidence: Predictions from digital twin.
        
        # Aggregated metrics
        historical_success_rate: Success rate in similar past cases.
        num_similar_cases: How many similar cases were found.
        avg_similarity: Average similarity of matched cases.
    """
    rank: int = Field(..., ge=1, description="Ranking position")
    strategy: ResolutionStrategy = Field(..., description="Recommended strategy")
    final_score: float = Field(..., ge=0, le=100, description="Combined ranking score")
    confidence: float = Field(..., ge=0, le=1, description="Recommendation confidence")
    
    # Explainability
    explanation: str = Field(..., description="Human-readable explanation")
    score_breakdown: ScoreBreakdown = Field(..., description="Score calculation details")
    historical_evidence: List[HistoricalEvidence] = Field(
        default_factory=list, 
        description="Similar historical cases"
    )
    simulation_evidence: Optional[SimulationEvidence] = Field(
        default=None, 
        description="Simulation predictions"
    )
    
    # Aggregated metrics
    historical_success_rate: float = Field(
        default=0, ge=0, le=1, 
        description="Success rate in similar cases"
    )
    num_similar_cases: int = Field(default=0, ge=0, description="Number of similar cases")
    avg_similarity: float = Field(default=0, ge=0, le=1, description="Average similarity score")
    
    def get_full_explanation(self) -> str:
        """
        Generate comprehensive explanation for operator display.
        
        Returns a multi-line explanation suitable for dashboards.
        """
        lines = [
            f"### Recommendation #{self.rank}: {self.strategy.value.replace('_', ' ').title()}",
            f"**Score:** {self.final_score:.1f}/100 | **Confidence:** {self.confidence:.0%}",
            "",
            f"**Why this is recommended:**",
            self.explanation,
            "",
        ]
        
        if self.simulation_evidence:
            lines.extend([
                f"**Simulation Prediction:**",
                f"- Expected delay reduction: {self.simulation_evidence.delay_reduction} minutes",
                f"- Recovery time: ~{self.simulation_evidence.recovery_time} minutes",
                f"- Success likelihood: {'High' if self.simulation_evidence.predicted_success else 'Moderate'}",
                "",
            ])
        
        if self.historical_evidence:
            lines.extend([
                f"**Historical Evidence ({self.num_similar_cases} similar cases, {self.historical_success_rate:.0%} success rate):**",
            ])
            for i, evidence in enumerate(self.historical_evidence[:3], 1):
                lines.append(f"{i}. {evidence.to_explanation_text()}")
            lines.append("")
        
        lines.extend([
            f"**Score Breakdown:**",
            self.score_breakdown.explain(),
        ])
        
        return "\n".join(lines)


class RecommendationResponse(BaseModel):
    """
    Complete response from the recommendation engine.
    
    Includes the ranked recommendations plus metadata about the
    recommendation process itself.
    """
    conflict_id: str = Field(..., description="ID of the conflict being resolved")
    conflict_type: ConflictType = Field(..., description="Type of conflict")
    recommendations: List[Recommendation] = Field(..., description="Ranked recommendations")
    
    # Process metadata
    total_candidates: int = Field(default=0, description="Total strategies considered")
    similar_conflicts_found: int = Field(default=0, description="Historical matches found")
    processing_time_ms: float = Field(default=0, description="Processing time")
    
    # Global explainability
    summary: str = Field(default="", description="Executive summary")
    
    def get_top_recommendation(self) -> Optional[Recommendation]:
        """Get the highest-ranked recommendation."""
        return self.recommendations[0] if self.recommendations else None


# =============================================================================
# Recommendation Engine Configuration
# =============================================================================

class RecommendationConfig(BaseModel):
    """Configuration for the recommendation engine."""
    
    # Weights for combining scores
    historical_weight: float = Field(default=0.4, ge=0, le=1)
    simulation_weight: float = Field(default=0.5, ge=0, le=1)
    similarity_weight: float = Field(default=0.1, ge=0, le=1)
    
    # Search parameters
    similarity_threshold: float = Field(default=0.6, ge=0, le=1)
    max_similar_conflicts: int = Field(default=10, ge=1)
    min_similar_for_confidence: int = Field(default=3, ge=1)
    
    # Simulation parameters
    simulation_seed: Optional[int] = Field(default=None)
    
    # Output parameters
    max_recommendations: int = Field(default=5, ge=1)
    include_low_confidence: bool = Field(default=False)


# =============================================================================
# Recommendation Engine
# =============================================================================

class RecommendationEngine:
    """
    AI-powered recommendation engine for rail conflict resolution.
    
    This engine combines multiple sources of evidence to produce ranked,
    explainable recommendations:
    
    1. **Historical Analysis**: Finds similar past conflicts using semantic
       search and analyzes which resolutions worked in those cases.
    
    2. **Simulation Prediction**: Runs each candidate through a digital twin
       simulator to predict outcomes.
    
    3. **Score Fusion**: Combines historical success rates with simulation
       scores using configurable weights.
    
    4. **Explainability**: Every recommendation includes detailed evidence
       and natural language explanations.
    
    Example:
        >>> engine = RecommendationEngine()
        >>> 
        >>> conflict = {
        ...     "conflict_type": "platform_conflict",
        ...     "station": "London Waterloo",
        ...     "severity": "high",
        ...     "affected_trains": ["T1", "T2"],
        ...     "delay_before": 15
        ... }
        >>> 
        >>> response = await engine.recommend(conflict)
        >>> 
        >>> print(response.summary)
        >>> for rec in response.recommendations:
        ...     print(rec.get_full_explanation())
    
    Attributes:
        config: Engine configuration.
        embedding_service: Service for generating embeddings.
        qdrant_service: Service for vector similarity search.
        simulator: Digital twin simulator.
    """
    
    def __init__(
        self,
        config: Optional[RecommendationConfig] = None,
        embedding_service: Optional[EmbeddingService] = None,
        qdrant_service: Optional[QdrantService] = None,
        simulator: Optional[DigitalTwinSimulator] = None,
    ):
        """
        Initialize the recommendation engine.
        
        Args:
            config: Engine configuration. Uses defaults if not provided.
            embedding_service: Embedding service instance.
            qdrant_service: Qdrant service instance.
            simulator: Digital twin simulator instance.
        """
        self.config = config or RecommendationConfig()
        self._embedding_service = embedding_service
        self._qdrant_service = qdrant_service
        self._simulator = simulator
        
        logger.info(
            f"RecommendationEngine initialized with weights: "
            f"historical={self.config.historical_weight}, "
            f"simulation={self.config.simulation_weight}"
        )
    
    @property
    def embedding_service(self) -> EmbeddingService:
        """Get or create embedding service."""
        if self._embedding_service is None:
            self._embedding_service = get_embedding_service()
        return self._embedding_service
    
    @property
    def qdrant_service(self) -> QdrantService:
        """Get or create Qdrant service."""
        if self._qdrant_service is None:
            self._qdrant_service = get_qdrant_service()
        return self._qdrant_service
    
    @property
    def simulator(self) -> DigitalTwinSimulator:
        """Get or create simulator."""
        if self._simulator is None:
            self._simulator = get_digital_twin_simulator(
                seed=self.config.simulation_seed
            )
        return self._simulator
    
    # =========================================================================
    # Main Recommendation Pipeline
    # =========================================================================
    
    async def recommend(
        self,
        conflict: Union[Dict[str, Any], Any],
        conflict_id: Optional[str] = None,
    ) -> RecommendationResponse:
        """
        Generate ranked, explainable recommendations for a conflict.
        
        This is the main entry point for the recommendation engine. It
        orchestrates the full pipeline:
        
        1. Embed the conflict
        2. Search for similar historical conflicts
        3. Extract and aggregate resolution outcomes
        4. Simulate each candidate strategy
        5. Combine scores and rank
        6. Generate explanations
        
        Args:
            conflict: The detected conflict. Can be a dict or Pydantic model.
            conflict_id: Optional ID for the conflict.
        
        Returns:
            RecommendationResponse with ranked, explained recommendations.
        """
        import time
        start_time = time.time()
        
        # Normalize conflict to dict
        conflict_data = self._normalize_conflict(conflict)
        conflict_id = conflict_id or conflict_data.get("id", f"conflict_{int(time.time())}")
        conflict_type = self._extract_conflict_type(conflict_data)
        
        logger.info(f"Generating recommendations for conflict {conflict_id}")
        
        # =====================================================================
        # STEP 1: Embed the conflict
        # Convert the conflict to a semantic vector representation
        # =====================================================================
        
        conflict_embedding = self.embedding_service.embed_conflict(conflict_data)
        
        # =====================================================================
        # STEP 2: Search for similar historical conflicts
        # Query Qdrant to find past conflicts with similar characteristics
        # =====================================================================
        
        similar_conflicts = await self._search_similar_conflicts(
            embedding=conflict_embedding,
            conflict_type=conflict_type,
        )
        
        logger.info(f"Found {len(similar_conflicts)} similar historical conflicts")
        
        # =====================================================================
        # STEP 3: Extract and aggregate resolution outcomes
        # Group historical evidence by resolution strategy
        # =====================================================================
        
        historical_evidence_by_strategy = self._aggregate_historical_evidence(
            similar_conflicts
        )
        
        # =====================================================================
        # STEP 4: Determine candidate strategies
        # Get all strategies that have historical precedent or are applicable
        # =====================================================================
        
        candidate_strategies = self._get_candidate_strategies(
            conflict_type=conflict_type,
            historical_strategies=set(historical_evidence_by_strategy.keys()),
        )
        
        logger.info(f"Evaluating {len(candidate_strategies)} candidate strategies")
        
        # =====================================================================
        # STEP 5: Simulate each candidate
        # Run digital twin to predict outcomes
        # =====================================================================
        
        simulation_results = self._simulate_candidates(
            conflict_data=conflict_data,
            strategies=candidate_strategies,
        )
        
        # =====================================================================
        # STEP 6: Score and rank candidates
        # Combine historical success + simulation scores
        # =====================================================================
        
        recommendations = self._rank_candidates(
            strategies=candidate_strategies,
            historical_evidence=historical_evidence_by_strategy,
            simulation_results=simulation_results,
            conflict_data=conflict_data,
        )
        
        # =====================================================================
        # STEP 7: Generate response with explanations
        # =====================================================================
        
        processing_time = (time.time() - start_time) * 1000
        
        response = RecommendationResponse(
            conflict_id=conflict_id,
            conflict_type=conflict_type,
            recommendations=recommendations[:self.config.max_recommendations],
            total_candidates=len(candidate_strategies),
            similar_conflicts_found=len(similar_conflicts),
            processing_time_ms=round(processing_time, 2),
            summary=self._generate_summary(
                conflict_data, recommendations, len(similar_conflicts)
            ),
        )
        
        logger.info(
            f"Generated {len(response.recommendations)} recommendations "
            f"in {processing_time:.0f}ms"
        )
        
        return response
    
    def recommend_sync(
        self,
        conflict: Union[Dict[str, Any], Any],
        conflict_id: Optional[str] = None,
    ) -> RecommendationResponse:
        """
        Synchronous version of recommend().
        
        For use in non-async contexts.
        """
        return asyncio.get_event_loop().run_until_complete(
            self.recommend(conflict, conflict_id)
        )
    
    # =========================================================================
    # Pipeline Steps
    # =========================================================================
    
    async def _search_similar_conflicts(
        self,
        embedding: List[float],
        conflict_type: ConflictType,
    ) -> List[SimilarConflict]:
        """
        Search Qdrant for similar historical conflicts.
        
        Uses the conflict embedding to find semantically similar past cases.
        Optionally filters by conflict type for more relevant matches.
        
        Returns a list of SimilarConflict objects (extracts matches from SearchResult).
        """
        try:
            search_result = self.qdrant_service.search_similar_conflicts(
                query_embedding=embedding,
                limit=self.config.max_similar_conflicts,
                score_threshold=self.config.similarity_threshold,
                filter_conditions={
                    # Optional: filter to same conflict type for higher relevance
                    # "conflict_type": conflict_type.value,
                },
            )
            # Extract matches from SearchResult
            return search_result.matches
        except Exception as e:
            logger.warning(f"Qdrant search failed: {e}. Using empty results.")
            return []
    
    def _aggregate_historical_evidence(
        self,
        similar_conflicts: List[SimilarConflict],
    ) -> Dict[ResolutionStrategy, List[HistoricalEvidence]]:
        """
        Aggregate historical evidence by resolution strategy.
        
        Groups the similar conflicts by which resolution was applied,
        building the evidence base for each strategy.
        """
        evidence_by_strategy: Dict[ResolutionStrategy, List[HistoricalEvidence]] = {}
        
        for match in similar_conflicts:
            # Extract resolution information from the SimilarConflict
            resolution_str = match.resolution_strategy
            if not resolution_str:
                continue
            
            try:
                strategy = ResolutionStrategy(resolution_str)
            except ValueError:
                continue
            
            # Extract outcome
            outcome_str = match.resolution_outcome or "unknown"
            try:
                outcome = ResolutionOutcome(outcome_str)
            except ValueError:
                outcome = ResolutionOutcome.PARTIAL_SUCCESS
            
            # Build evidence record
            evidence = HistoricalEvidence(
                conflict_id=match.id,
                similarity_score=match.score,
                station=match.station,
                timestamp=match.detected_at,
                resolution_applied=strategy,
                outcome=outcome,
                delay_reduction_achieved=match.delay_before - (match.actual_delay_after or match.delay_before),
                recovery_time_actual=match.metadata.get("recovery_time", 0),
                context_summary=self._build_context_summary_from_match(match),
            )
            
            if strategy not in evidence_by_strategy:
                evidence_by_strategy[strategy] = []
            evidence_by_strategy[strategy].append(evidence)
        
        # Sort evidence by similarity score (highest first)
        for strategy in evidence_by_strategy:
            evidence_by_strategy[strategy].sort(
                key=lambda e: e.similarity_score, reverse=True
            )
        
        return evidence_by_strategy
    
    def _get_candidate_strategies(
        self,
        conflict_type: ConflictType,
        historical_strategies: set,
    ) -> List[ResolutionStrategy]:
        """
        Determine candidate strategies to evaluate.
        
        Combines strategies that have historical precedent with
        strategies that are applicable to this conflict type.
        """
        # Strategies applicable to this conflict type (from simulator)
        applicable = set(self.simulator._get_applicable_strategies(conflict_type))
        
        # Include strategies with historical precedent
        candidates = applicable.union(historical_strategies)
        
        # Always include all strategies if we have few candidates
        if len(candidates) < 3:
            candidates = set(ResolutionStrategy)
        
        return list(candidates)
    
    def _simulate_candidates(
        self,
        conflict_data: Dict[str, Any],
        strategies: List[ResolutionStrategy],
    ) -> Dict[ResolutionStrategy, SimulationOutcome]:
        """
        Simulate each candidate strategy.
        
        Runs the digital twin for each strategy and collects predictions.
        """
        results = {}
        
        for strategy in strategies:
            try:
                outcome = self.simulator.simulate(conflict_data, strategy)
                results[strategy] = outcome
            except Exception as e:
                logger.warning(f"Simulation failed for {strategy}: {e}")
                # Continue with other strategies
        
        return results
    
    def _rank_candidates(
        self,
        strategies: List[ResolutionStrategy],
        historical_evidence: Dict[ResolutionStrategy, List[HistoricalEvidence]],
        simulation_results: Dict[ResolutionStrategy, SimulationOutcome],
        conflict_data: Dict[str, Any],
    ) -> List[Recommendation]:
        """
        Rank candidates by combined historical + simulation score.
        
        The ranking formula:
        
        final_score = (historical_weight × historical_score) 
                    + (simulation_weight × simulation_score)
                    + similarity_bonus
                    + confidence_adjustment
        
        Where:
        - historical_score: Success rate × 100, weighted by similarity
        - simulation_score: Raw simulator score (0-100)
        - similarity_bonus: Extra points for high-similarity matches
        - confidence_adjustment: Penalty for low confidence
        """
        recommendations = []
        
        for strategy in strategies:
            # Get evidence for this strategy
            evidence_list = historical_evidence.get(strategy, [])
            sim_outcome = simulation_results.get(strategy)
            
            # Calculate historical score
            historical_score, success_rate, avg_similarity = self._calculate_historical_score(
                evidence_list
            )
            
            # Calculate simulation score
            simulation_score = sim_outcome.score if sim_outcome else 50.0
            
            # Calculate similarity bonus
            # High similarity matches get bonus points
            similarity_bonus = 0.0
            if evidence_list and avg_similarity > 0.8:
                similarity_bonus = 5.0 * (avg_similarity - 0.8) / 0.2  # Up to 5 points
            
            # Calculate confidence
            confidence = self._calculate_confidence(
                num_cases=len(evidence_list),
                avg_similarity=avg_similarity,
                sim_confidence=sim_outcome.confidence if sim_outcome else 0.5,
            )
            
            # Confidence adjustment
            # Low confidence reduces score
            confidence_adjustment = 0.0
            if confidence < 0.5:
                confidence_adjustment = -10 * (0.5 - confidence)  # Up to -5 points
            
            # Calculate final score
            final_score = (
                self.config.historical_weight * historical_score
                + self.config.simulation_weight * simulation_score
                + self.config.similarity_weight * (avg_similarity * 100)
                + similarity_bonus
                + confidence_adjustment
            )
            
            # Clamp to [0, 100]
            final_score = max(0, min(100, final_score))
            
            # Build score breakdown
            breakdown = ScoreBreakdown(
                historical_score=historical_score,
                historical_weight=self.config.historical_weight,
                simulation_score=simulation_score,
                simulation_weight=self.config.simulation_weight,
                similarity_bonus=similarity_bonus,
                confidence_adjustment=confidence_adjustment,
                final_score=final_score,
            )
            
            # Build simulation evidence
            sim_evidence = None
            if sim_outcome:
                sim_evidence = SimulationEvidence.from_outcome(sim_outcome)
            
            # Generate explanation
            explanation = self._generate_recommendation_explanation(
                strategy=strategy,
                evidence_list=evidence_list,
                sim_outcome=sim_outcome,
                success_rate=success_rate,
                confidence=confidence,
            )
            
            # Create recommendation
            rec = Recommendation(
                rank=len(recommendations) + 1,  # Temporary rank, will be updated after sorting
                strategy=strategy,
                final_score=round(final_score, 1),
                confidence=round(confidence, 2),
                explanation=explanation,
                score_breakdown=breakdown,
                historical_evidence=evidence_list[:5],  # Top 5 evidence
                simulation_evidence=sim_evidence,
                historical_success_rate=success_rate,
                num_similar_cases=len(evidence_list),
                avg_similarity=round(avg_similarity, 2),
            )
            
            # Filter low confidence if configured
            if not self.config.include_low_confidence and confidence < 0.3:
                continue
            
            recommendations.append(rec)
        
        # Sort by final score (descending)
        recommendations.sort(key=lambda r: r.final_score, reverse=True)
        
        # Assign ranks
        for i, rec in enumerate(recommendations, 1):
            rec.rank = i
        
        return recommendations
    
    def _calculate_historical_score(
        self,
        evidence_list: List[HistoricalEvidence],
    ) -> Tuple[float, float, float]:
        """
        Calculate historical success score.
        
        Returns:
            Tuple of (score 0-100, success_rate 0-1, avg_similarity 0-1)
        """
        if not evidence_list:
            return 50.0, 0.0, 0.0  # Neutral score if no history
        
        # Weight successes by similarity score
        total_weight = 0.0
        weighted_success = 0.0
        
        for evidence in evidence_list:
            weight = evidence.similarity_score
            is_success = evidence.outcome == ResolutionOutcome.SUCCESS
            
            total_weight += weight
            if is_success:
                weighted_success += weight
        
        # Calculate success rate
        success_rate = weighted_success / total_weight if total_weight > 0 else 0.0
        
        # Calculate average similarity
        avg_similarity = sum(e.similarity_score for e in evidence_list) / len(evidence_list)
        
        # Convert to 0-100 score
        # Base: 50, then add/subtract based on success rate
        score = 50 + (success_rate - 0.5) * 100  # Range: 0-100
        
        return score, success_rate, avg_similarity
    
    def _calculate_confidence(
        self,
        num_cases: int,
        avg_similarity: float,
        sim_confidence: float,
    ) -> float:
        """
        Calculate overall confidence in the recommendation.
        
        Confidence is based on:
        - Number of similar historical cases (more = higher confidence)
        - Average similarity (higher = more relevant evidence)
        - Simulation confidence
        """
        # Base confidence from number of cases
        # 0 cases = 0.3, 3+ cases = 0.7 max from this factor
        case_confidence = min(0.7, 0.3 + 0.133 * num_cases)
        
        # Similarity factor (0.6-1.0 similarity adds confidence)
        similarity_factor = max(0, (avg_similarity - 0.5) * 2)  # 0-1 range
        
        # Combine factors
        confidence = (
            0.4 * case_confidence +
            0.3 * similarity_factor +
            0.3 * sim_confidence
        )
        
        return min(0.95, max(0.2, confidence))
    
    # =========================================================================
    # Explanation Generation
    # =========================================================================
    
    def _generate_recommendation_explanation(
        self,
        strategy: ResolutionStrategy,
        evidence_list: List[HistoricalEvidence],
        sim_outcome: Optional[SimulationOutcome],
        success_rate: float,
        confidence: float,
    ) -> str:
        """
        Generate human-readable explanation for a recommendation.
        
        This is a key explainability feature - operators can understand
        WHY this strategy is recommended in plain English.
        """
        strategy_name = strategy.value.replace("_", " ")
        parts = []
        
        # Historical evidence explanation
        if evidence_list:
            num_cases = len(evidence_list)
            success_pct = success_rate * 100
            
            if success_rate >= 0.8:
                parts.append(
                    f"Historically highly effective: {strategy_name} succeeded in "
                    f"{success_pct:.0f}% of {num_cases} similar cases."
                )
            elif success_rate >= 0.6:
                parts.append(
                    f"Good historical track record: {strategy_name} succeeded in "
                    f"{success_pct:.0f}% of {num_cases} similar cases."
                )
            elif success_rate >= 0.4:
                parts.append(
                    f"Mixed historical results: {strategy_name} succeeded in "
                    f"{success_pct:.0f}% of {num_cases} similar cases."
                )
            else:
                parts.append(
                    f"Limited historical success: {strategy_name} succeeded in only "
                    f"{success_pct:.0f}% of {num_cases} similar cases."
                )
        else:
            parts.append(
                f"No directly similar historical cases found for {strategy_name}. "
                f"Recommendation based primarily on simulation."
            )
        
        # Simulation explanation
        if sim_outcome:
            if sim_outcome.success:
                parts.append(
                    f"Simulation predicts success with {sim_outcome.delay_reduction} minutes "
                    f"delay reduction and ~{sim_outcome.recovery_time} minutes to recovery."
                )
            else:
                parts.append(
                    f"Simulation predicts challenges, but still expects "
                    f"{sim_outcome.delay_reduction} minutes delay reduction."
                )
        
        # Confidence note
        if confidence < 0.5:
            parts.append(
                "Note: Lower confidence due to limited similar cases or mixed evidence."
            )
        elif confidence > 0.8:
            parts.append(
                "High confidence based on strong historical evidence and simulation alignment."
            )
        
        return " ".join(parts)
    
    def _generate_summary(
        self,
        conflict_data: Dict[str, Any],
        recommendations: List[Recommendation],
        num_similar: int,
    ) -> str:
        """Generate executive summary of recommendations."""
        if not recommendations:
            return "Unable to generate recommendations due to insufficient data."
        
        top = recommendations[0]
        conflict_type = conflict_data.get("conflict_type", "conflict")
        station = conflict_data.get("station", "the station")
        
        summary_parts = [
            f"For this {conflict_type} at {station}, "
            f"we analyzed {num_similar} similar historical cases and simulated "
            f"{len(recommendations)} resolution strategies."
        ]
        
        summary_parts.append(
            f"The top recommendation is **{top.strategy.value.replace('_', ' ')}** "
            f"with {top.confidence:.0%} confidence."
        )
        
        if top.simulation_evidence:
            summary_parts.append(
                f"Expected outcome: {top.simulation_evidence.delay_reduction} minutes "
                f"delay reduction, {top.simulation_evidence.recovery_time} minutes to recovery."
            )
        
        return " ".join(summary_parts)
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _normalize_conflict(self, conflict: Any) -> Dict[str, Any]:
        """Convert conflict to dictionary format."""
        if isinstance(conflict, dict):
            return conflict
        if hasattr(conflict, "model_dump"):
            return conflict.model_dump()
        if hasattr(conflict, "dict"):
            return conflict.dict()
        return dict(conflict)
    
    def _extract_conflict_type(self, conflict_data: Dict[str, Any]) -> ConflictType:
        """Extract conflict type from conflict data."""
        conflict_type = conflict_data.get("conflict_type")
        
        if isinstance(conflict_type, ConflictType):
            return conflict_type
        
        if isinstance(conflict_type, str):
            try:
                return ConflictType(conflict_type)
            except ValueError:
                pass
        
        return ConflictType.TRACK_BLOCKAGE  # Default
    
    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        """Parse timestamp from various formats."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None
    
    def _build_context_summary(self, payload: Dict[str, Any]) -> str:
        """Build a brief context summary from payload."""
        parts = []
        
        if "conflict_type" in payload:
            parts.append(payload["conflict_type"])
        
        if "severity" in payload:
            parts.append(f"severity: {payload['severity']}")
        
        if "affected_trains" in payload:
            trains = payload["affected_trains"]
            if isinstance(trains, list):
                parts.append(f"{len(trains)} trains affected")
            else:
                parts.append(f"{trains} trains affected")
        
        return ", ".join(parts) if parts else "No additional context"
    
    def _build_context_summary_from_match(self, match: SimilarConflict) -> str:
        """Build a brief context summary from a SimilarConflict."""
        parts = []
        
        if match.conflict_type:
            parts.append(match.conflict_type)
        
        if match.severity:
            parts.append(f"severity: {match.severity}")
        
        if match.affected_trains:
            parts.append(f"{len(match.affected_trains)} trains affected")
        
        return ", ".join(parts) if parts else "No additional context"


# =============================================================================
# Factory Functions
# =============================================================================

_engine_instance: Optional[RecommendationEngine] = None


def get_recommendation_engine(
    config: Optional[RecommendationConfig] = None,
) -> RecommendationEngine:
    """
    Get a singleton RecommendationEngine instance.
    
    For use with FastAPI dependency injection.
    """
    global _engine_instance
    
    if _engine_instance is None:
        _engine_instance = RecommendationEngine(config=config)
    
    return _engine_instance


def clear_engine_cache() -> None:
    """Clear the singleton instance (useful for testing)."""
    global _engine_instance
    _engine_instance = None
