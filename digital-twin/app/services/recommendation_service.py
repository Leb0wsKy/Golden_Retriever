"""
Recommendation engine service.

Combines vector similarity search, simulation results,
and business rules to generate ranked conflict resolutions.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.core.config import settings
from app.core.constants import DEFAULT_SIMILARITY_THRESHOLD, DEFAULT_TOP_K_RESULTS
from app.core.exceptions import RecommendationError
from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService
from app.services.simulation_service import SimulationService, SimulationResult


@dataclass
class Recommendation:
    """
    A ranked conflict resolution recommendation.
    
    Attributes:
        id: Unique recommendation ID.
        strategy: Recommended resolution strategy.
        confidence: Confidence score (0-1).
        similar_conflicts: Similar past conflicts that informed this recommendation.
        simulation_result: Result from digital twin simulation.
        explanation: Human-readable explanation.
    """
    id: str
    strategy: str
    confidence: float
    similar_conflicts: List[Dict[str, Any]]
    simulation_result: Dict[str, Any]
    explanation: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "similar_conflicts": self.similar_conflicts,
            "simulation_result": self.simulation_result,
            "explanation": self.explanation
        }


class RecommendationService:
    """
    Service for generating conflict resolution recommendations.
    
    Orchestrates the recommendation pipeline:
    1. Find similar past conflicts via vector search
    2. Extract successful resolution patterns
    3. Simulate candidate resolutions
    4. Rank and return recommendations
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService = None,
        qdrant_service: QdrantService = None,
        simulation_service: SimulationService = None
    ):
        """
        Initialize the recommendation service.
        
        Args:
            embedding_service: Optional embedding service instance.
            qdrant_service: Optional Qdrant service instance.
            simulation_service: Optional simulation service instance.
        """
        self.embedding_service = embedding_service or EmbeddingService()
        self.qdrant_service = qdrant_service or QdrantService()
        self.simulation_service = simulation_service or SimulationService()
    
    def get_recommendations(
        self,
        conflict: Dict[str, Any],
        top_k: int = None,
        similarity_threshold: float = None
    ) -> List[Recommendation]:
        """
        Generate ranked recommendations for a conflict.
        
        Args:
            conflict: Conflict data dictionary.
            top_k: Maximum number of recommendations.
            similarity_threshold: Minimum similarity score for past conflicts.
            
        Returns:
            List of ranked Recommendation objects.
        """
        top_k = top_k or settings.MAX_RECOMMENDATIONS
        similarity_threshold = similarity_threshold or DEFAULT_SIMILARITY_THRESHOLD
        
        try:
            # Step 1: Generate embedding for current conflict
            conflict_embedding = self.embedding_service.embed_conflict(conflict)
            
            # Step 2: Find similar past conflicts
            similar_conflicts = self.qdrant_service.search(
                query_vector=conflict_embedding.tolist(),
                limit=DEFAULT_TOP_K_RESULTS,
                score_threshold=similarity_threshold
            )
            
            # Step 3: Extract successful strategies from similar conflicts
            candidate_strategies = self._extract_strategies(similar_conflicts)
            
            # Step 4: Simulate candidate strategies
            simulation_results = self.simulation_service.simulate_all(
                conflict=conflict,
                strategies=candidate_strategies
            )
            
            # Step 5: Rank and create recommendations
            recommendations = self._rank_and_create_recommendations(
                conflict=conflict,
                similar_conflicts=similar_conflicts,
                simulation_results=simulation_results,
                top_k=top_k
            )
            
            return recommendations
            
        except Exception as e:
            raise RecommendationError(
                "Failed to generate recommendations",
                {"error": str(e)}
            )
    
    def _extract_strategies(
        self,
        similar_conflicts: List[Dict[str, Any]]
    ) -> List:
        """Extract successful strategies from similar past conflicts."""
        from app.core.constants import ResolutionStrategy
        
        strategies = set()
        
        for conflict in similar_conflicts:
            payload = conflict.get("payload", {})
            if payload.get("resolution_successful"):
                strategy = payload.get("resolution_strategy")
                if strategy:
                    try:
                        strategies.add(ResolutionStrategy(strategy))
                    except ValueError:
                        pass
        
        # If no strategies found, return all available
        if not strategies:
            return list(ResolutionStrategy)
        
        return list(strategies)
    
    def _rank_and_create_recommendations(
        self,
        conflict: Dict[str, Any],
        similar_conflicts: List[Dict[str, Any]],
        simulation_results: List[SimulationResult],
        top_k: int
    ) -> List[Recommendation]:
        """Rank simulation results and create recommendation objects."""
        import uuid
        
        recommendations = []
        
        for sim_result in simulation_results:
            if not sim_result.success:
                continue
            
            # Calculate confidence score based on:
            # - Simulation feasibility
            # - Similar conflict success rate
            # - Strategy-specific metrics
            confidence = self._calculate_confidence(
                sim_result, similar_conflicts
            )
            
            # Generate explanation
            explanation = self._generate_explanation(
                conflict, sim_result, similar_conflicts
            )
            
            recommendation = Recommendation(
                id=str(uuid.uuid4()),
                strategy=sim_result.strategy.value,
                confidence=confidence,
                similar_conflicts=similar_conflicts[:3],  # Top 3 similar
                simulation_result=sim_result.to_dict(),
                explanation=explanation
            )
            
            recommendations.append(recommendation)
        
        # Sort by confidence and return top_k
        recommendations.sort(key=lambda r: r.confidence, reverse=True)
        return recommendations[:top_k]
    
    def _calculate_confidence(
        self,
        sim_result: SimulationResult,
        similar_conflicts: List[Dict[str, Any]]
    ) -> float:
        """Calculate confidence score for a recommendation."""
        # Base confidence from simulation
        base_confidence = sim_result.metrics.get("feasibility_score", 0.5)
        
        # Boost from similar successful resolutions
        strategy_successes = sum(
            1 for c in similar_conflicts
            if c.get("payload", {}).get("resolution_strategy") == sim_result.strategy.value
            and c.get("payload", {}).get("resolution_successful")
        )
        
        similarity_boost = min(0.2, strategy_successes * 0.05)
        
        # Combine scores
        confidence = min(1.0, base_confidence + similarity_boost)
        return round(confidence, 3)
    
    def _generate_explanation(
        self,
        conflict: Dict[str, Any],
        sim_result: SimulationResult,
        similar_conflicts: List[Dict[str, Any]]
    ) -> str:
        """Generate human-readable explanation for recommendation."""
        strategy_name = sim_result.strategy.value.replace("_", " ").title()
        
        explanation_parts = [
            f"Recommended strategy: {strategy_name}.",
            f"Simulation shows {sim_result.metrics.get('feasibility_score', 0):.0%} feasibility."
        ]
        
        if similar_conflicts:
            explanation_parts.append(
                f"Based on {len(similar_conflicts)} similar past conflicts."
            )
        
        if sim_result.metrics.get("delay_impact_minutes"):
            explanation_parts.append(
                f"Expected delay impact: {sim_result.metrics['delay_impact_minutes']} minutes."
            )
        
        return " ".join(explanation_parts)
    
    def store_outcome(
        self,
        conflict: Dict[str, Any],
        recommendation_id: str,
        success: bool,
        notes: str = None
    ):
        """
        Store resolution outcome for continuous learning.
        
        Args:
            conflict: Original conflict data.
            recommendation_id: ID of the applied recommendation.
            success: Whether the resolution was successful.
            notes: Optional notes about the outcome.
        """
        # Generate embedding for the conflict
        embedding = self.embedding_service.embed_conflict(conflict)
        
        # Add outcome metadata
        payload = {
            **conflict,
            "resolution_successful": success,
            "recommendation_id": recommendation_id,
            "outcome_notes": notes
        }
        
        # Store in Qdrant
        self.qdrant_service.upsert(
            vectors=[embedding.tolist()],
            payloads=[payload]
        )
