"""
Conflict data models.

Pydantic models for conflict data validation
and serialization.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, time
from pydantic import BaseModel, Field, field_validator

from app.core.constants import (
    ConflictType, 
    ConflictSeverity, 
    TimeOfDay,
    ResolutionStrategy,
    ResolutionOutcome
)


class RecommendedResolution(BaseModel):
    """
    Recommended resolution for a conflict.
    
    Attributes:
        strategy: The recommended resolution strategy.
        confidence: Confidence score for this recommendation (0-1).
        estimated_delay_reduction: Expected delay reduction in minutes.
        description: Human-readable explanation of the resolution.
    """
    strategy: ResolutionStrategy = Field(
        ...,
        description="Recommended resolution strategy"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1)"
    )
    estimated_delay_reduction: int = Field(
        default=0,
        ge=0,
        description="Expected delay reduction in minutes"
    )
    description: str = Field(
        ...,
        description="Explanation of the resolution"
    )


class FinalOutcome(BaseModel):
    """
    Final outcome after resolution attempt.
    
    Attributes:
        outcome: The result of the resolution attempt.
        actual_delay: Actual delay after resolution in minutes.
        resolution_time_minutes: Time taken to resolve in minutes.
        notes: Additional notes about the outcome.
    """
    outcome: ResolutionOutcome = Field(
        ...,
        description="Resolution outcome"
    )
    actual_delay: int = Field(
        default=0,
        ge=0,
        description="Actual delay after resolution (minutes)"
    )
    resolution_time_minutes: int = Field(
        default=0,
        ge=0,
        description="Time taken to resolve (minutes)"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional outcome notes"
    )


class ConflictBase(BaseModel):
    """
    Base conflict model with common fields.
    
    Attributes:
        conflict_type: Type of rail conflict.
        severity: Severity level of the conflict.
        station: Station where conflict occurs.
        time_of_day: Time period of the conflict.
        affected_trains: List of affected train IDs.
        delay_before: Delay in minutes before resolution.
        description: Human-readable description.
    """
    conflict_type: ConflictType = Field(
        ...,
        description="Type of rail conflict"
    )
    severity: ConflictSeverity = Field(
        default=ConflictSeverity.MEDIUM,
        description="Severity level"
    )
    station: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Station where conflict occurs"
    )
    time_of_day: TimeOfDay = Field(
        ...,
        description="Time period of the conflict"
    )
    affected_trains: List[str] = Field(
        default_factory=list,
        min_length=1,
        description="List of affected train IDs"
    )
    delay_before: int = Field(
        default=0,
        ge=0,
        le=1440,
        description="Delay in minutes before resolution attempt"
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Conflict description"
    )
    platform: Optional[str] = Field(
        default=None,
        description="Platform number if applicable"
    )
    track_section: Optional[str] = Field(
        default=None,
        description="Track section if applicable"
    )
    conflict_time: Optional[datetime] = Field(
        default=None,
        description="Exact time when conflict occurs"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional conflict-specific metadata"
    )


class ConflictCreate(ConflictBase):
    """Model for creating a new conflict."""
    pass


class GeneratedConflict(ConflictBase):
    """
    Synthetic conflict with resolution and outcome.
    
    Used by the conflict generator for creating complete
    conflict scenarios with recommended resolutions and outcomes.
    
    Attributes:
        id: Unique conflict identifier.
        detected_at: When conflict was detected.
        recommended_resolution: AI-recommended resolution.
        final_outcome: Actual outcome after resolution.
    """
    id: str = Field(..., description="Unique conflict ID")
    detected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Detection timestamp"
    )
    recommended_resolution: RecommendedResolution = Field(
        ...,
        description="Recommended resolution for this conflict"
    )
    final_outcome: FinalOutcome = Field(
        ...,
        description="Final outcome after resolution attempt"
    )

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "conflict-abc123",
                "conflict_type": "platform_conflict",
                "severity": "high",
                "station": "Central Station",
                "time_of_day": "morning_peak",
                "affected_trains": ["IC101", "RE205", "S15"],
                "delay_before": 15,
                "description": "Platform 3 double-booked: IC101 arrival conflicts with RE205 departure",
                "platform": "3",
                "detected_at": "2026-01-26T08:30:00Z",
                "recommended_resolution": {
                    "strategy": "platform_change",
                    "confidence": 0.85,
                    "estimated_delay_reduction": 10,
                    "description": "Redirect IC101 to Platform 5 which is available"
                },
                "final_outcome": {
                    "outcome": "success",
                    "actual_delay": 5,
                    "resolution_time_minutes": 8,
                    "notes": "Platform change executed smoothly"
                }
            }
        }


class Conflict(ConflictBase):
    """
    Full conflict model with system-generated fields.
    
    Attributes:
        id: Unique conflict identifier.
        detected_at: When conflict was detected.
        resolved: Whether conflict has been resolved.
        resolution_strategy: Strategy used for resolution.
        resolution_successful: Whether resolution was successful.
    """
    id: str = Field(..., description="Unique conflict ID")
    detected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Detection timestamp"
    )
    resolved: bool = Field(
        default=False,
        description="Resolution status"
    )
    resolution_strategy: Optional[str] = Field(
        default=None,
        description="Applied resolution strategy"
    )
    resolution_successful: Optional[bool] = Field(
        default=None,
        description="Resolution outcome"
    )

    class Config:
        from_attributes = True


class ConflictResponse(Conflict):
    """
    Conflict response model for API responses.
    
    Includes computed fields and formatted data.
    """
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "conflict_type": "platform_conflict",
                "severity": "high",
                "station": "Central Station",
                "time_of_day": "morning_peak",
                "affected_trains": ["IC123", "RE456"],
                "delay_before": 12,
                "description": "Platform 3 double-booked for arrivals",
                "platform": "3",
                "conflict_time": "2026-01-26T14:30:00Z",
                "detected_at": "2026-01-26T10:15:00Z",
                "resolved": False,
                "metadata": {
                    "station_capacity": 10,
                    "available_platforms": 2
                }
            }
        }
