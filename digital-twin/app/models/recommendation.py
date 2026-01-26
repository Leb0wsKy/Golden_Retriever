"""
Recommendation data models.

Pydantic models for recommendation requests
and responses.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.constants import ResolutionStrategy


class RecommendationRequest(BaseModel):
    """
    Request model for getting recommendations.
    
    Attributes:
        conflict_type: Type of rail conflict.
        severity: Severity level.
        location: Conflict location.
        trains: Trains involved.
        description: Conflict description.
        top_k: Maximum recommendations to return.
        similarity_threshold: Minimum similarity score.
    """
    conflict_type: str = Field(..., description="Type of conflict")
    severity: str = Field(default="medium", description="Severity level")
    location: str = Field(..., description="Conflict location")
    trains: List[str] = Field(default_factory=list, description="Trains involved")
    description: str = Field(..., description="Conflict description")
    platform: Optional[str] = Field(default=None, description="Platform if applicable")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional data")
    top_k: int = Field(default=5, ge=1, le=20, description="Max recommendations")
    similarity_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "conflict_type": "platform",
                "severity": "high",
                "location": "Central Station",
                "trains": ["IC123", "RE456"],
                "description": "Platform 3 double-booked for arrivals",
                "platform": "3",
                "top_k": 5,
                "similarity_threshold": 0.75
            }
        }


class SimilarConflict(BaseModel):
    """
    Model for a similar past conflict.
    
    Attributes:
        id: Conflict ID.
        score: Similarity score.
        conflict_type: Type of conflict.
        resolution_strategy: Strategy that was used.
        resolution_successful: Whether it worked.
    """
    id: str = Field(..., description="Conflict ID")
    score: float = Field(..., description="Similarity score")
    conflict_type: str = Field(..., description="Type of conflict")
    location: str = Field(..., description="Conflict location")
    resolution_strategy: Optional[str] = Field(
        default=None,
        description="Resolution strategy used"
    )
    resolution_successful: Optional[bool] = Field(
        default=None,
        description="Whether resolution succeeded"
    )


class SimulationMetrics(BaseModel):
    """
    Metrics from simulation.
    
    Attributes:
        feasibility_score: How feasible the strategy is.
        delay_impact_minutes: Expected delay impact.
        affected_services: Number of affected services.
    """
    feasibility_score: float = Field(..., description="Feasibility (0-1)")
    delay_impact_minutes: Optional[int] = Field(
        default=None,
        description="Expected delay"
    )
    affected_services: Optional[int] = Field(
        default=None,
        description="Number of affected services"
    )
    additional_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Strategy-specific metrics"
    )


class RecommendationResponse(BaseModel):
    """
    Response model for a single recommendation.
    
    Attributes:
        id: Recommendation ID.
        strategy: Recommended resolution strategy.
        confidence: Confidence score.
        similar_conflicts: Similar past conflicts.
        simulation_metrics: Results from simulation.
        explanation: Human-readable explanation.
    """
    id: str = Field(..., description="Recommendation ID")
    strategy: str = Field(..., description="Resolution strategy")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    similar_conflicts: List[SimilarConflict] = Field(
        default_factory=list,
        description="Similar past conflicts"
    )
    simulation_metrics: SimulationMetrics = Field(
        ...,
        description="Simulation results"
    )
    explanation: str = Field(..., description="Recommendation explanation")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "rec-123e4567",
                "strategy": "platform_change",
                "confidence": 0.85,
                "similar_conflicts": [
                    {
                        "id": "conf-abc123",
                        "score": 0.92,
                        "conflict_type": "platform",
                        "location": "Central Station",
                        "resolution_strategy": "platform_change",
                        "resolution_successful": True
                    }
                ],
                "simulation_metrics": {
                    "feasibility_score": 0.88,
                    "delay_impact_minutes": 5,
                    "affected_services": 2
                },
                "explanation": "Recommended strategy: Platform Change. Simulation shows 88% feasibility. Based on 3 similar past conflicts."
            }
        }


class FeedbackRequest(BaseModel):
    """
    Request model for submitting recommendation feedback.
    
    Attributes:
        recommendation_id: ID of the recommendation.
        success: Whether resolution was successful.
        notes: Optional notes about outcome.
    """
    recommendation_id: str = Field(..., description="Recommendation ID")
    success: bool = Field(..., description="Resolution success")
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Outcome notes"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "recommendation_id": "rec-123e4567",
                "success": True,
                "notes": "Platform change executed successfully with minimal passenger impact"
            }
        }
