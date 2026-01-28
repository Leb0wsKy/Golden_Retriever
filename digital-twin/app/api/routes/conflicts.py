"""
Conflict-related API endpoints.

Handles CRUD operations, conflict generation, analysis, and recommendation
retrieval for rail conflicts.
"""

import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field

from app.models.conflict import Conflict, ConflictCreate, ConflictResponse, GeneratedConflict
from app.core.constants import (
    ConflictType,
    ConflictSeverity,
    TimeOfDay,
    ResolutionStrategy,
    ResolutionOutcome,
)
from app.services.conflict_generator import (
    ConflictGenerator,
    get_conflict_generator,
)
from app.services.schedule_conflict_generator import (
    get_hybrid_generator,
    get_schedule_conflict_generator,
)
from app.services.transitland_conflict_service import (
    TransitlandConflictService,
    get_transitland_conflict_service,
    GenerationConfig,
)
from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.qdrant_service import QdrantService, get_qdrant_service
from app.services.recommendation_engine import (
    RecommendationEngine,
    RecommendationResponse as EngineRecommendationResponse,
    RecommendationConfig,
    get_recommendation_engine,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class GenerateConflictsRequest(BaseModel):
    """Request model for conflict generation."""
    count: int = Field(
        default=10, ge=1, le=1000,
        description="Number of conflicts to generate"
    )
    conflict_types: Optional[List[ConflictType]] = Field(
        default=None,
        description="Specific conflict types to generate (None = all types)"
    )
    severity_distribution: Optional[Dict[str, float]] = Field(
        default=None,
        description="Custom severity distribution, e.g., {'high': 0.2, 'medium': 0.5, 'low': 0.3}"
    )
    stations: Optional[List[str]] = Field(
        default=None,
        description="Specific stations to use (None = random stations)"
    )
    success_rate_target: Optional[float] = Field(
        default=None, ge=0, le=1,
        description="Target success rate for resolutions (None = random)"
    )
    include_embeddings: bool = Field(
        default=False,
        description="Whether to generate embeddings and store in Qdrant"
    )
    
    # Schedule-based generation options
    use_schedule_data: bool = Field(
        default=True,
        description="Use real schedule data from Transitland API for realistic conflicts"
    )
    schedule_date: Optional[str] = Field(
        default=None,
        description="Date for schedule data (YYYY-MM-DD format), default: today"
    )
    schedule_ratio: float = Field(
        default=0.7,
        ge=0, le=1,
        description="Ratio of schedule-based vs synthetic conflicts (0-1)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "count": 50,
                "conflict_types": ["platform_conflict", "headway_conflict"],
                "severity_distribution": {"high": 0.3, "medium": 0.5, "low": 0.2},
                "stations": ["London Euston", "Manchester Piccadilly"],
                "success_rate_target": 0.85,
                "include_embeddings": True,
                "use_schedule_data": True,
                "schedule_date": "2026-01-26",
                "schedule_ratio": 0.7
            }
        }


class GenerateConflictsResponse(BaseModel):
    """Response model for conflict generation."""
    generated_count: int = Field(..., description="Number of conflicts generated")
    conflicts: List[GeneratedConflict] = Field(..., description="Generated conflicts")
    stored_in_qdrant: bool = Field(default=False, description="Whether stored in vector DB")
    embeddings_generated: int = Field(default=0, description="Embeddings created")
    generation_time_ms: float = Field(default=0, description="Time to generate (ms)")
    summary: str = Field(..., description="Human-readable summary")
    
    class Config:
        json_schema_extra = {
            "example": {
                "generated_count": 50,
                "stored_in_qdrant": True,
                "embeddings_generated": 50,
                "generation_time_ms": 1250.5,
                "summary": "Generated 50 conflicts (20 platform, 15 track, 15 schedule). "
                           "Severity: 15 high, 25 medium, 10 low. 85% success rate."
            }
        }


class AnalyzeConflictRequest(BaseModel):
    """Request model for conflict analysis."""
    conflict_type: ConflictType = Field(..., description="Type of rail conflict")
    severity: ConflictSeverity = Field(
        default=ConflictSeverity.MEDIUM,
        description="Severity level"
    )
    station: str = Field(..., min_length=1, description="Station name")
    time_of_day: TimeOfDay = Field(..., description="Time period")
    affected_trains: List[str] = Field(..., min_length=1, description="Train IDs")
    delay_before: int = Field(default=0, ge=0, le=1440, description="Current delay (min)")
    description: str = Field(..., min_length=10, description="Conflict description")
    platform: Optional[str] = Field(default=None, description="Platform number")
    track_section: Optional[str] = Field(default=None, description="Track section")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional data")
    
    # Analysis options
    store_in_qdrant: bool = Field(
        default=True,
        description="Whether to store the embedded conflict in Qdrant"
    )
    find_similar: bool = Field(
        default=True,
        description="Whether to search for similar historical conflicts"
    )
    similarity_threshold: float = Field(
        default=0.6, ge=0, le=1,
        description="Minimum similarity score for matches"
    )
    top_k: int = Field(
        default=5, ge=1, le=50,
        description="Maximum similar conflicts to return"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "conflict_type": "platform_conflict",
                "severity": "high",
                "station": "London Waterloo",
                "time_of_day": "morning_peak",
                "affected_trains": ["IC101", "RE205", "S15"],
                "delay_before": 15,
                "description": "Platform 3 double-booked: IC101 arrival conflicts with RE205 departure",
                "platform": "3",
                "store_in_qdrant": True,
                "find_similar": True,
                "similarity_threshold": 0.7,
                "top_k": 5
            }
        }


class SimilarConflictInfo(BaseModel):
    """Information about a similar historical conflict."""
    conflict_id: str = Field(..., description="Conflict ID")
    similarity_score: float = Field(..., ge=0, le=1, description="Similarity (0-1)")
    station: str = Field(..., description="Station")
    conflict_type: str = Field(..., description="Type")
    severity: str = Field(..., description="Severity")
    resolution_strategy: Optional[str] = Field(default=None, description="What worked")
    resolution_outcome: Optional[str] = Field(default=None, description="Outcome")
    delay_reduction: Optional[int] = Field(default=None, description="Delay reduced")
    explanation: str = Field(default="", description="Why this is similar")


class AnalyzeConflictResponse(BaseModel):
    """Response model for conflict analysis."""
    conflict_id: str = Field(..., description="Assigned conflict ID")
    stored: bool = Field(..., description="Whether stored in Qdrant")
    embedding_generated: bool = Field(..., description="Whether embedding was created")
    embedding_dimension: int = Field(default=384, description="Embedding dimensions")
    
    # Similar conflicts
    similar_conflicts_found: int = Field(default=0, description="Matches found")
    similar_conflicts: List[SimilarConflictInfo] = Field(
        default_factory=list,
        description="Similar historical conflicts"
    )
    
    # Analysis insights
    analysis_summary: str = Field(..., description="Human-readable analysis")
    recommended_next_step: str = Field(
        default="",
        description="Suggested next action"
    )
    processing_time_ms: float = Field(default=0, description="Processing time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "conflict_id": "conf-abc123",
                "stored": True,
                "embedding_generated": True,
                "embedding_dimension": 384,
                "similar_conflicts_found": 3,
                "similar_conflicts": [
                    {
                        "conflict_id": "hist-001",
                        "similarity_score": 0.92,
                        "station": "London Waterloo",
                        "conflict_type": "platform_conflict",
                        "severity": "high",
                        "resolution_strategy": "platform_change",
                        "resolution_outcome": "success",
                        "delay_reduction": 12,
                        "explanation": "Similar platform conflict at same station during peak hours"
                    }
                ],
                "analysis_summary": "Found 3 similar conflicts. Platform change was successful 67% of the time.",
                "recommended_next_step": "Get recommendations via GET /conflicts/conf-abc123/recommendations"
            }
        }


class RecommendationSummary(BaseModel):
    """Summary of a single recommendation."""
    rank: int = Field(..., ge=1, description="Ranking (1 = best)")
    strategy: str = Field(..., description="Resolution strategy")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level")
    score: float = Field(..., ge=0, le=100, description="Combined score")
    historical_success_rate: float = Field(default=0, ge=0, le=1)
    predicted_delay_reduction: int = Field(default=0, ge=0)
    explanation: str = Field(..., description="Human-readable explanation")


class GetRecommendationsResponse(BaseModel):
    """Response model for getting recommendations."""
    conflict_id: str = Field(..., description="Conflict ID")
    conflict_type: str = Field(..., description="Type of conflict")
    recommendations: List[RecommendationSummary] = Field(
        ...,
        description="Ranked recommendations"
    )
    
    # Context
    top_recommendation: str = Field(..., description="Best strategy")
    top_confidence: float = Field(..., description="Confidence in top recommendation")
    similar_cases_analyzed: int = Field(default=0, description="Historical cases used")
    
    # Explainability
    executive_summary: str = Field(..., description="Summary for operators")
    detailed_explanation: str = Field(..., description="Full explanation with evidence")
    
    processing_time_ms: float = Field(default=0, description="Processing time")
    
    class Config:
        json_schema_extra = {
            "example": {
                "conflict_id": "conf-abc123",
                "conflict_type": "platform_conflict",
                "recommendations": [
                    {
                        "rank": 1,
                        "strategy": "platform_change",
                        "confidence": 0.87,
                        "score": 82.5,
                        "historical_success_rate": 0.85,
                        "predicted_delay_reduction": 12,
                        "explanation": "Platform change recommended based on 85% historical success rate and simulation predicting 12-minute delay reduction."
                    }
                ],
                "top_recommendation": "platform_change",
                "top_confidence": 0.87,
                "similar_cases_analyzed": 5,
                "executive_summary": "Recommend PLATFORM CHANGE with 87% confidence. Historical data shows 85% success rate for similar conflicts.",
                "detailed_explanation": "Based on analysis of 5 similar conflicts..."
            }
        }


# =============================================================================
# In-Memory Storage (for demo - replace with actual DB in production)
# =============================================================================

# Simple in-memory storage for conflicts
_conflict_store: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/", response_model=List[ConflictResponse])
async def list_conflicts(
    limit: int = Query(default=50, ge=1, le=500, description="Max conflicts to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
):
    """
    Retrieve all conflicts.
    
    Returns:
        List of conflict records.
    """
    conflicts = list(_conflict_store.values())[offset:offset + limit]
    return conflicts


@router.get("/{conflict_id}", response_model=ConflictResponse)
async def get_conflict(conflict_id: str):
    """
    Retrieve a specific conflict by ID.
    
    Args:
        conflict_id: Unique identifier for the conflict.
        
    Returns:
        Conflict details.
    """
    if conflict_id not in _conflict_store:
        raise HTTPException(
            status_code=404, 
            detail=f"Conflict '{conflict_id}' not found. Use POST /conflicts/analyze to create one."
        )
    return _conflict_store[conflict_id]


@router.post("/", response_model=ConflictResponse, status_code=201)
async def create_conflict(
    request: AnalyzeConflictRequest,
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    qdrant_service: QdrantService = Depends(get_qdrant_service),
):
    """
    Create a new conflict record.
    
    Creates a conflict and optionally stores it in Qdrant vector database
    with embeddings for similarity search.
    
    Args:
        request: Conflict details
        embedding_service: Service for generating embeddings
        qdrant_service: Service for vector storage
        
    Returns:
        Created conflict with ID
    """
    try:
        # Generate conflict ID
        conflict_id = f"conf-{uuid.uuid4().hex[:12]}"
        
        # Build conflict text for embedding
        conflict_text = (
            f"{request.conflict_type.value} at {request.station} "
            f"during {request.time_of_day.value}. "
            f"Severity: {request.severity.value}. "
            f"{request.description}"
        )
        
        # Create conflict record
        conflict_data = {
            "id": conflict_id,
            "conflict_type": request.conflict_type.value,
            "severity": request.severity.value,
            "station": request.station,
            "time_of_day": request.time_of_day.value,
            "affected_trains": request.affected_trains,
            "delay_before": request.delay_before,
            "description": request.description,
            "platform": request.platform,
            "track_section": request.track_section,
            "metadata": request.metadata,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # Store in memory
        _conflict_store[conflict_id] = conflict_data
        
        # Store in Qdrant if requested
        if request.store_in_qdrant:
            try:
                # Generate embedding
                embedding = embedding_service.embed(conflict_text)
                
                # Store in Qdrant
                qdrant_service.upsert_conflict(
                    conflict_id=conflict_id,
                    embedding=embedding,
                    payload=conflict_data
                )
                
                logger.info(f"Stored conflict {conflict_id} in Qdrant")
            except Exception as e:
                logger.error(f"Failed to store in Qdrant: {e}")
                # Don't fail the request if Qdrant storage fails
        
        return conflict_data
        
    except Exception as e:
        logger.error(f"Error creating conflict: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create conflict: {str(e)}"
        )


@router.post("/generate", response_model=GenerateConflictsResponse)
async def generate_conflicts(
    request: GenerateConflictsRequest,
):
    """
    Generate conflicts for testing and training.
    
    This endpoint supports two modes of conflict generation:
    
    **Schedule-Based Generation (default, use_schedule_data=True):**
    Uses real transit schedule data from Transitland API to detect
    realistic conflict scenarios:
    - **Platform conflicts**: Detected when two trains are scheduled
      for the same platform within 3 minutes
    - **Headway violations**: Detected when consecutive trains on
      the same route are closer than minimum safe headway (3 min)
    - **Capacity overload**: Detected when too many trains are
      scheduled in a time window
    
    **Synthetic Generation (use_schedule_data=False):**
    Generates fully synthetic conflicts with realistic patterns
    for testing when schedule data is not needed.
    
    **Use Cases:**
    - Populate the vector database with training data
    - Generate test scenarios for validation
    - Create diverse conflict datasets for ML training
    - Test with realistic schedule-based conflicts
    
    Args:
        request: Generation parameters including schedule options
        
    Returns:
        Generated conflicts with generation statistics
    """
    import time
    from datetime import date as date_type
    
    start_time = time.time()
    
    try:
        generated = []
        
        # Choose generation mode
        if request.use_schedule_data:
            # Use hybrid generator (schedule-based + synthetic fallback)
            hybrid_generator = get_hybrid_generator(
                schedule_ratio=request.schedule_ratio
            )
            
            # Parse schedule date if provided
            schedule_date = None
            if request.schedule_date:
                try:
                    schedule_date = date_type.fromisoformat(request.schedule_date)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid schedule_date format: {request.schedule_date}. Use YYYY-MM-DD."
                    )
            
            # Generate using hybrid approach
            generated = await hybrid_generator.generate(
                count=request.count,
                stations=request.stations,
                schedule_date=schedule_date,
            )
            
        else:
            # Use original synthetic generator
            generator = get_conflict_generator()
            
            # Generate conflicts
            if request.conflict_types:
                # Generate for specific types
                conflicts = []
                per_type = request.count // len(request.conflict_types)
                remainder = request.count % len(request.conflict_types)
                
                for i, conflict_type in enumerate(request.conflict_types):
                    type_count = per_type + (1 if i < remainder else 0)
                    if type_count > 0:
                        type_conflicts = generator.generate_by_type(
                            conflict_type=conflict_type,
                            count=type_count,
                        )
                        conflicts.extend(type_conflicts)
                generated = conflicts
            else:
                # Generate random types
                generated = generator.generate(count=request.count)
        
        embeddings_count = 0
        stored = False
        
        # Optionally generate embeddings and store in Qdrant
        if request.include_embeddings:
            try:
                embedding_service = get_embedding_service()
                qdrant_service = get_qdrant_service()
                
                for conflict in generated:
                    # Generate embedding
                    text = _conflict_to_text(conflict)
                    embedding = embedding_service.embed(text)
                    
                    # Store in Qdrant - pass the conflict object directly
                    qdrant_service.upsert_conflict(
                        conflict=conflict,
                        embedding=embedding,
                    )
                    embeddings_count += 1
                
                stored = True
            except Exception as e:
                logger.warning(f"Failed to store embeddings: {e}")
        
        # Calculate statistics for summary
        type_counts = {}
        severity_counts = {}
        success_count = 0
        schedule_based_count = 0
        
        for c in generated:
            ct = c.conflict_type.value if hasattr(c.conflict_type, 'value') else str(c.conflict_type)
            type_counts[ct] = type_counts.get(ct, 0) + 1
            
            sev = c.severity.value if hasattr(c.severity, 'value') else str(c.severity)
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
            if c.final_outcome.outcome == ResolutionOutcome.SUCCESS:
                success_count += 1
            
            # Check if schedule-based
            if c.metadata and c.metadata.get("source") == "schedule_based":
                schedule_based_count += 1
        
        success_rate = success_count / len(generated) if generated else 0
        
        type_summary = ", ".join(f"{count} {t}" for t, count in type_counts.items())
        severity_summary = ", ".join(f"{count} {s}" for s, count in severity_counts.items())
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        summary = (
            f"Generated {len(generated)} conflicts ({type_summary}). "
            f"Severity: {severity_summary}. "
            f"Success rate: {success_rate:.0%}."
        )
        
        if request.use_schedule_data:
            summary += f" Schedule-based: {schedule_based_count}, Synthetic: {len(generated) - schedule_based_count}."
        
        if stored:
            summary += f" All conflicts embedded and stored in Qdrant."
        
        return GenerateConflictsResponse(
            generated_count=len(generated),
            conflicts=generated,
            stored_in_qdrant=stored,
            embeddings_generated=embeddings_count,
            generation_time_ms=elapsed_ms,
            summary=summary,
        )
        
    except Exception as e:
        logger.error(f"Conflict generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate conflicts: {str(e)}"
        )


@router.post("/analyze", response_model=AnalyzeConflictResponse)
async def analyze_conflict(
    request: AnalyzeConflictRequest,
):
    """
    Analyze a detected conflict.
    
    This endpoint:
    1. Creates an embedding of the conflict description
    2. Optionally stores it in Qdrant for future similarity matching
    3. Searches for similar historical conflicts
    4. Returns analysis insights and similar cases
    
    **Explanation:**
    The embedding captures semantic meaning of the conflict,
    enabling similarity search that goes beyond keyword matching.
    For example, "platform double-booking" and "scheduling overlap"
    would be recognized as similar even without shared keywords.
    
    Similar historical conflicts provide valuable context:
    - What strategies worked before?
    - What was the success rate?
    - How much delay was reduced?
    
    **Next Steps:**
    After analysis, use GET /conflicts/{conflict_id}/recommendations
    to get ranked resolution recommendations.
    
    Args:
        request: Conflict details and analysis options
        
    Returns:
        Analysis results with similar conflicts and insights
    """
    import time
    start_time = time.time()
    
    try:
        # Generate conflict ID
        conflict_id = f"conf-{uuid.uuid4().hex[:12]}"
        
        # Get services
        embedding_service = get_embedding_service()
        qdrant_service = get_qdrant_service()
        
        # Build conflict text for embedding
        conflict_text = (
            f"{request.conflict_type.value} at {request.station} during {request.time_of_day.value}. "
            f"Severity: {request.severity.value}. "
            f"Affected trains: {', '.join(request.affected_trains)}. "
            f"Current delay: {request.delay_before} minutes. "
            f"{request.description}"
        )
        
        if request.platform:
            conflict_text += f" Platform: {request.platform}."
        if request.track_section:
            conflict_text += f" Track section: {request.track_section}."
        
        # Generate embedding
        embedding = embedding_service.embed(conflict_text)
        embedding_generated = True
        
        # Store in Qdrant if requested
        stored = False
        if request.store_in_qdrant:
            try:
                payload = {
                    "conflict_id": conflict_id,
                    "conflict_type": request.conflict_type.value,
                    "severity": request.severity.value,
                    "station": request.station,
                    "time_of_day": request.time_of_day.value,
                    "affected_trains": request.affected_trains,
                    "delay_before": request.delay_before,
                    "description": request.description,
                    "platform": request.platform,
                    "track_section": request.track_section,
                    "metadata": request.metadata,
                    "analyzed_at": datetime.utcnow().isoformat(),
                }
                qdrant_service.upsert_conflict_raw(
                    conflict_id=conflict_id,
                    embedding=embedding,
                    payload=payload,
                )
                stored = True
            except Exception as e:
                logger.warning(f"Failed to store in Qdrant: {e}")
        
        # Search for similar conflicts
        similar_conflicts = []
        if request.find_similar:
            try:
                search_result = await qdrant_service.search_similar_conflicts(
                    query_embedding=embedding,
                    limit=request.top_k,
                    score_threshold=request.similarity_threshold,
                )
                
                for match in search_result.matches:
                    # Build explanation
                    explanation = _build_similarity_explanation(
                        match, 
                        request.conflict_type.value, 
                        request.station
                    )
                    
                    similar_conflicts.append(SimilarConflictInfo(
                        conflict_id=match.id,
                        similarity_score=match.score,
                        station=match.station,
                        conflict_type=match.conflict_type,
                        severity=match.severity,
                        resolution_strategy=match.resolution_strategy,
                        resolution_outcome=match.resolution_outcome,
                        delay_reduction=match.actual_delay_after,
                        explanation=explanation,
                    ))
            except Exception as e:
                logger.warning(f"Similar conflict search failed: {e}")
        
        # Build analysis summary
        analysis_summary = _build_analysis_summary(
            request, similar_conflicts
        )
        
        # Store in local cache for recommendations
        _conflict_store[conflict_id] = {
            "id": conflict_id,
            "conflict_type": request.conflict_type,
            "severity": request.severity,
            "station": request.station,
            "time_of_day": request.time_of_day,
            "affected_trains": request.affected_trains,
            "delay_before": request.delay_before,
            "description": request.description,
            "platform": request.platform,
            "track_section": request.track_section,
            "metadata": request.metadata,
            "detected_at": datetime.utcnow(),
            "resolved": False,
            "embedding": embedding,
        }
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return AnalyzeConflictResponse(
            conflict_id=conflict_id,
            stored=stored,
            embedding_generated=embedding_generated,
            embedding_dimension=len(embedding),
            similar_conflicts_found=len(similar_conflicts),
            similar_conflicts=similar_conflicts,
            analysis_summary=analysis_summary,
            recommended_next_step=f"Get recommendations: GET /api/v1/conflicts/{conflict_id}/recommendations",
            processing_time_ms=elapsed_ms,
        )
        
    except Exception as e:
        logger.error(f"Conflict analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze conflict: {str(e)}"
        )


@router.get("/{conflict_id}/recommendations", response_model=GetRecommendationsResponse)
async def get_conflict_recommendations(
    conflict_id: str,
    max_recommendations: int = Query(
        default=5, ge=1, le=10,
        description="Maximum recommendations to return"
    ),
    include_simulation: bool = Query(
        default=True,
        description="Whether to run digital twin simulation"
    ),
):
    """
    Get resolution recommendations for a conflict.
    
    This endpoint orchestrates the full recommendation pipeline:
    1. Retrieves the conflict from storage
    2. Embeds it and searches for similar historical conflicts
    3. Aggregates historical success rates per strategy
    4. Runs each candidate through the digital twin simulator
    5. Ranks strategies by combined historical + simulation scores
    6. Returns explainable recommendations
    
    **Explainability:**
    Each recommendation includes:
    - **Why this strategy?** - Historical success rates from similar cases
    - **What to expect?** - Simulation predictions (delay reduction, recovery time)
    - **How confident?** - Based on number of similar cases and similarity scores
    - **Score breakdown** - Transparent calculation showing all factors
    
    **Confidence Levels:**
    - High (>80%): Strong historical evidence + positive simulation
    - Medium (50-80%): Moderate evidence or mixed signals
    - Low (<50%): Limited data or uncertain predictions
    
    Args:
        conflict_id: ID from POST /conflicts/analyze
        max_recommendations: Limit on recommendations
        include_simulation: Whether to simulate each strategy
        
    Returns:
        Ranked recommendations with full explanations
    """
    import time
    start_time = time.time()
    
    # Check conflict exists
    if conflict_id not in _conflict_store:
        raise HTTPException(
            status_code=404,
            detail=f"Conflict '{conflict_id}' not found. "
                   f"First analyze the conflict with POST /api/v1/conflicts/analyze"
        )
    
    conflict_data = _conflict_store[conflict_id]
    
    try:
        # Get recommendation engine
        engine = get_recommendation_engine()
        
        # Build conflict dict for engine
        conflict_input = {
            "id": conflict_id,
            "conflict_type": conflict_data["conflict_type"].value if hasattr(conflict_data["conflict_type"], 'value') else conflict_data["conflict_type"],
            "severity": conflict_data["severity"].value if hasattr(conflict_data["severity"], 'value') else conflict_data["severity"],
            "station": conflict_data["station"],
            "time_of_day": conflict_data["time_of_day"].value if hasattr(conflict_data["time_of_day"], 'value') else conflict_data["time_of_day"],
            "affected_trains": conflict_data["affected_trains"],
            "delay_before": conflict_data["delay_before"],
            "description": conflict_data["description"],
            "platform": conflict_data.get("platform"),
            "track_section": conflict_data.get("track_section"),
            "metadata": conflict_data.get("metadata", {}),
        }
        
        # Get recommendations from engine
        response = await engine.recommend(conflict_input)
        
        # Convert to API response format
        recommendations = []
        for rec in response.recommendations[:max_recommendations]:
            recommendations.append(RecommendationSummary(
                rank=rec.rank,
                strategy=rec.strategy.value,
                confidence=rec.confidence,
                score=rec.final_score,
                historical_success_rate=rec.historical_success_rate,
                predicted_delay_reduction=rec.simulation_evidence.delay_reduction if rec.simulation_evidence else 0,
                explanation=rec.explanation,
            ))
        
        # Get top recommendation
        top_rec = recommendations[0] if recommendations else None
        
        # Build executive summary
        executive_summary = _build_executive_summary(
            conflict_data, recommendations, response.similar_conflicts_found
        )
        
        # Build detailed explanation
        detailed_explanation = ""
        if top_rec:
            top_full = response.recommendations[0] if response.recommendations else None
            if top_full:
                detailed_explanation = top_full.get_full_explanation()
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return GetRecommendationsResponse(
            conflict_id=conflict_id,
            conflict_type=conflict_input["conflict_type"],
            recommendations=recommendations,
            top_recommendation=top_rec.strategy if top_rec else "none",
            top_confidence=top_rec.confidence if top_rec else 0,
            similar_cases_analyzed=response.similar_conflicts_found,
            executive_summary=executive_summary,
            detailed_explanation=detailed_explanation,
            processing_time_ms=elapsed_ms,
        )
        
    except Exception as e:
        logger.error(f"Recommendation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


# =============================================================================
# Helper Functions
# =============================================================================


@router.post("/generate-from-schedules")
async def generate_conflicts_from_transitland(
    stations: Optional[List[str]] = None,
    count: int = Query(default=10, ge=1, le=100, description="Conflicts to generate"),
    schedule_date: Optional[str] = Query(default=None, description="Date (YYYY-MM-DD)"),
    auto_store: bool = Query(default=True, description="Auto-store in Qdrant"),
):
    """
    🚂 Generate conflicts from real Transitland schedule data.
    
    This endpoint automatically:
    1. Fetches real train schedules from Transitland API
    2. Analyzes schedules for conflicts (platform conflicts, headway violations, etc.)
    3. Generates realistic conflicts based on actual timetables
    4. Optionally stores them in Qdrant with embeddings
    
    **Key Features:**
    - Uses REAL schedule data from UK rail networks
    - Detects actual platform conflicts and timing issues
    - Generates embeddings for similarity search
    - Stores in Qdrant for historical analysis
    
    **Example:**
    Generate 20 conflicts from London Euston and Manchester Piccadilly:
    ```
    POST /api/v1/conflicts/generate-from-schedules?count=20
    Body: ["London Euston", "Manchester Piccadilly"]
    ```
    
    Args:
        stations: List of station names (None = use configured UK stations).
        count: Number of conflicts to generate (max 100).
        schedule_date: Date for schedules in YYYY-MM-DD format (None = today).
        auto_store: Whether to automatically store in Qdrant.
    
    Returns:
        Generation result with conflicts and statistics.
    """
    import time
    from datetime import date as dt_date
    
    start_time = time.time()
    
    try:
        # Parse date if provided
        target_date = None
        if schedule_date:
            try:
                target_date = dt_date.fromisoformat(schedule_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid date format: {schedule_date}. Use YYYY-MM-DD"
                )
        
        # Get Transitland conflict service
        service = get_transitland_conflict_service()
        
        # Update config for this request
        service.config.auto_store_in_qdrant = auto_store
        service.config.generate_embeddings = auto_store
        
        logger.info(
            f"Generating {count} conflicts from Transitland for stations: "
            f"{stations or 'all configured'}"
        )
        
        # Generate conflicts
        result = await service.generate_and_store_conflicts(
            stations=stations,
            count=count,
            schedule_date=target_date,
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        # Build response
        response = {
            "success": result.success,
            "generated_count": result.conflicts_generated,
            "schedule_based_count": result.schedule_based_count,
            "synthetic_count": result.synthetic_count,
            "stored_in_qdrant": result.conflicts_stored,
            "embeddings_created": result.embeddings_created,
            "stations_processed": result.stations_processed,
            "errors": result.errors,
            "generation_time_ms": elapsed_ms,
            "timestamp": result.timestamp.isoformat(),
            "summary": (
                f"✅ Generated {result.conflicts_generated} conflicts "
                f"({result.schedule_based_count} from real schedules, "
                f"{result.synthetic_count} synthetic) "
                f"from {len(result.stations_processed)} stations. "
                f"{result.conflicts_stored} stored in Qdrant."
            ) if result.success else f"❌ Generation failed with {len(result.errors)} errors",
            "next_steps": [
                "View conflicts: GET /api/v1/conflicts/",
                "Get recommendations: POST /api/v1/recommendations/",
                "View statistics: GET /api/v1/conflicts/transitland/stats",
            ]
        }
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transitland conflict generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate conflicts from Transitland: {str(e)}"
        )


@router.get("/transitland/stats")
async def get_transitland_stats():
    """
    Get statistics about Transitland conflict generation.
    
    Returns:
        Service statistics including total runs, conflicts generated, etc.
    """
    try:
        from app.services.transitland_client import TransitlandClient
        
        service = get_transitland_conflict_service()
        stats = service.get_statistics()
        
        return {
            "status": "active",
            "statistics": stats,
            "transitland_available_stations": list(TransitlandClient.UK_STATIONS.keys()),
            "total_stations": len(TransitlandClient.UK_STATIONS),
        }
        
    except Exception as e:
        logger.error(f"Failed to get Transitland stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )


# =============================================================================
# Helper Functions
# =============================================================================

def _conflict_to_text(conflict: GeneratedConflict) -> str:
    """Convert a conflict to text for embedding."""
    return (
        f"{conflict.conflict_type.value} at {conflict.station} during {conflict.time_of_day.value}. "
        f"Severity: {conflict.severity.value}. "
        f"Affected trains: {', '.join(conflict.affected_trains)}. "
        f"Delay: {conflict.delay_before} minutes. "
        f"{conflict.description}"
    )


def _conflict_to_payload(conflict: GeneratedConflict) -> Dict[str, Any]:
    """Convert a conflict to Qdrant payload."""
    return {
        "conflict_id": conflict.id,
        "conflict_type": conflict.conflict_type.value,
        "severity": conflict.severity.value,
        "station": conflict.station,
        "time_of_day": conflict.time_of_day.value,
        "affected_trains": conflict.affected_trains,
        "delay_before": conflict.delay_before,
        "description": conflict.description,
        "platform": conflict.platform,
        "detected_at": conflict.detected_at.isoformat(),
        "resolution_strategy": conflict.recommended_resolution.strategy.value,
        "resolution_outcome": conflict.final_outcome.outcome.value,
        "actual_delay_after": conflict.final_outcome.actual_delay,
    }


def _build_similarity_explanation(match, conflict_type: str, station: str) -> str:
    """Build explanation of why a historical conflict is similar."""
    reasons = []
    
    if match.conflict_type == conflict_type:
        reasons.append("same conflict type")
    if match.station == station:
        reasons.append("same station")
    
    if match.resolution_outcome == "success":
        reasons.append(f"{match.resolution_strategy} resolved it successfully")
    elif match.resolution_outcome:
        reasons.append(f"{match.resolution_strategy} had {match.resolution_outcome} outcome")
    
    if reasons:
        return f"Similar case: {', '.join(reasons)} (similarity: {match.score:.0%})"
    return f"Similar conflict pattern (similarity: {match.score:.0%})"


def _build_analysis_summary(
    request: AnalyzeConflictRequest, 
    similar_conflicts: List[SimilarConflictInfo]
) -> str:
    """Build human-readable analysis summary."""
    parts = [
        f"Analyzed {request.conflict_type.value} at {request.station}.",
    ]
    
    if not similar_conflicts:
        parts.append("No similar historical conflicts found - this may be a novel situation.")
        return " ".join(parts)
    
    parts.append(f"Found {len(similar_conflicts)} similar historical conflicts.")
    
    # Calculate success rate per strategy
    strategy_outcomes = {}
    for sc in similar_conflicts:
        if sc.resolution_strategy:
            if sc.resolution_strategy not in strategy_outcomes:
                strategy_outcomes[sc.resolution_strategy] = {"success": 0, "total": 0}
            strategy_outcomes[sc.resolution_strategy]["total"] += 1
            if sc.resolution_outcome == "success":
                strategy_outcomes[sc.resolution_strategy]["success"] += 1
    
    if strategy_outcomes:
        best_strategy = None
        best_rate = 0
        for strategy, outcomes in strategy_outcomes.items():
            rate = outcomes["success"] / outcomes["total"] if outcomes["total"] > 0 else 0
            if rate > best_rate:
                best_rate = rate
                best_strategy = strategy
        
        if best_strategy:
            parts.append(
                f"{best_strategy.replace('_', ' ').title()} was successful "
                f"{best_rate:.0%} of the time in similar cases."
            )
    
    return " ".join(parts)


def _build_executive_summary(
    conflict_data: Dict[str, Any],
    recommendations: List[RecommendationSummary],
    similar_count: int,
) -> str:
    """Build executive summary for operators."""
    if not recommendations:
        return (
            f"Unable to generate recommendations for this {conflict_data['conflict_type'].value}. "
            f"Consider manual assessment."
        )
    
    top = recommendations[0]
    confidence_level = "high" if top.confidence > 0.8 else "medium" if top.confidence > 0.5 else "low"
    
    summary = (
        f"Recommend {top.strategy.upper().replace('_', ' ')} with {confidence_level} confidence "
        f"({top.confidence:.0%}). "
    )
    
    if top.historical_success_rate > 0:
        summary += f"Historical success rate: {top.historical_success_rate:.0%}. "
    
    if top.predicted_delay_reduction > 0:
        summary += f"Expected delay reduction: {top.predicted_delay_reduction} minutes. "
    
    if similar_count > 0:
        summary += f"Based on {similar_count} similar historical cases."
    
    return summary
