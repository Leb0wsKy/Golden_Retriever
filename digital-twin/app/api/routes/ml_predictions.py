"""
ML Prediction Routes for Digital Twin API
Integrates machine learning conflict predictions with Qdrant storage
"""

import logging
from typing import List, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field

from app.services.qdrant_service import get_qdrant_service
from app.services.embedding_service import get_embedding_service
from app.core.constants import ConflictType, ConflictSeverity

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class MLPredictionRequest(BaseModel):
    """Request for storing ML prediction in Qdrant"""
    
    network_id: str = Field(description="Network identifier")
    train_count: int = Field(description="Number of trains in network")
    
    # Prediction results
    conflict_probability: float = Field(ge=0, le=1, description="Predicted conflict probability")
    confidence: float = Field(ge=0, le=1, description="Model confidence")
    risk_level: str = Field(description="Risk level: MINIMAL/LOW/MEDIUM/HIGH/CRITICAL")
    
    # Network metrics at prediction time
    avg_speed: Optional[float] = None
    avg_delay: Optional[float] = None
    anomaly_ratio: Optional[float] = None
    delayed_ratio: Optional[float] = None
    
    # Contributing factors
    contributing_factors: List[str] = Field(default_factory=list)
    recommended_action: Optional[str] = None
    
    # Alert information
    severity: str = Field(default="medium")
    alert_message: Optional[str] = None
    
    # Metadata
    source: str = Field(default="ml_prediction")
    timestamp: Optional[datetime] = None


class MLPredictionResponse(BaseModel):
    """Response after storing ML prediction"""
    
    success: bool
    prediction_id: str
    stored_in_qdrant: bool
    collection: str
    message: str


class MLPredictionAlert(BaseModel):
    """ML prediction alert for frontend"""
    
    id: str
    network_id: str
    severity: str
    risk_level: str
    probability: float
    confidence: float
    train_count: int
    contributing_factors: List[str]
    recommended_action: Optional[str]
    alert_message: str
    detected_at: datetime
    source: str


# =============================================================================
# Endpoints
# =============================================================================

@router.post(
    "/predictions",
    response_model=MLPredictionResponse,
    summary="Store ML conflict prediction",
    description="Store a machine learning conflict prediction in Qdrant for future retrieval and analysis"
)
async def store_ml_prediction(
    prediction: MLPredictionRequest = Body(...)
) -> MLPredictionResponse:
    """
    Store ML prediction in Qdrant pre_conflict_memory collection.
    
    This integrates ML predictions with the existing pre-conflict system,
    allowing them to be:
    - Retrieved by frontend for Pre-Conflict Alerts display
    - Searched using semantic similarity
    - Analyzed for patterns and trends
    """
    try:
        logger.info(f"📥 Storing ML prediction for network {prediction.network_id}")
        
        # Generate unique prediction ID
        prediction_id = f"ml-pred-{datetime.now().timestamp()}"
        
        # Get services
        qdrant_service = get_qdrant_service()
        embedding_service = get_embedding_service()
        
        # Determine conflict type based on contributing factors
        conflict_type = determine_conflict_type(prediction.contributing_factors)
        
        # Map risk level to severity
        severity_map = {
            "CRITICAL": ConflictSeverity.HIGH,
            "HIGH": ConflictSeverity.HIGH,
            "MEDIUM": ConflictSeverity.MEDIUM,
            "LOW": ConflictSeverity.LOW,
            "MINIMAL": ConflictSeverity.LOW
        }
        mapped_severity = severity_map.get(prediction.risk_level, ConflictSeverity.MEDIUM)
        
        # Build description for embedding
        factors_text = ", ".join(prediction.contributing_factors) if prediction.contributing_factors else "No specific factors"
        description = (
            f"ML predicted {prediction.risk_level} risk network conflict for {prediction.network_id}. "
            f"Probability: {prediction.conflict_probability:.2%}, Confidence: {prediction.confidence:.2%}. "
            f"Network state: {prediction.train_count} trains"
        )
        
        # Add optional metrics if available
        if prediction.avg_speed is not None:
            description += f", avg speed {prediction.avg_speed:.1f} km/h"
        if prediction.avg_delay is not None:
            description += f", avg delay {prediction.avg_delay:.1f} min"
        if prediction.anomaly_ratio is not None:
            description += f", {prediction.anomaly_ratio:.1%} anomalies"
        if prediction.delayed_ratio is not None:
            description += f", {prediction.delayed_ratio:.1%} delayed"
        
        description += f". Contributing factors: {factors_text}. "
        description += f"Recommended action: {prediction.recommended_action or 'Monitor'}"
        
        # Generate embedding
        embedding = embedding_service.embed(description)
        
        # Prepare metadata
        metadata = {
            "prediction_id": prediction_id,
            "network_id": prediction.network_id,
            "source": "ml_prediction",
            "conflict_type": conflict_type.value,
            "severity": mapped_severity.value,
            "risk_level": prediction.risk_level,
            "probability": prediction.conflict_probability,
            "confidence": prediction.confidence,
            "train_count": prediction.train_count,
            "avg_speed": prediction.avg_speed or 0,
            "avg_delay": prediction.avg_delay or 0,
            "anomaly_ratio": prediction.anomaly_ratio or 0,
            "delayed_ratio": prediction.delayed_ratio or 0,
            "contributing_factors": factors_text,
            "recommended_action": prediction.recommended_action or "Monitor",
            "alert_message": prediction.alert_message or f"{prediction.risk_level} risk conflict predicted",
            "detected_at": (prediction.timestamp or datetime.now()).isoformat(),
            "description": description
        }
        
        # Store in Qdrant pre_conflict_memory collection
        from qdrant_client.models import PointStruct
        
        point_id = str(uuid.uuid4())
        
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload=metadata
        )
        
        qdrant_service.client.upsert(
            collection_name="pre_conflict_memory",
            points=[point]
        )
        
        logger.info(f"✅ ML prediction {prediction_id} stored in Qdrant (point: {point_id})")
        return MLPredictionResponse(
            success=True,
            prediction_id=prediction_id,
            stored_in_qdrant=True,
            collection="pre_conflict_memory",
            message=f"ML prediction stored successfully with ID {prediction_id}"
        )
        
    except Exception as e:
        logger.error(f"Error storing ML prediction: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error storing ML prediction: {str(e)}"
        )


@router.get(
    "/predictions",
    response_model=List[MLPredictionAlert],
    summary="Get recent ML predictions",
    description="Retrieve recent ML conflict predictions from Qdrant"
)
async def get_ml_predictions(
    limit: int = 50,
    network_id: Optional[str] = None,
    min_probability: Optional[float] = None
) -> List[MLPredictionAlert]:
    """
    Retrieve ML predictions from Qdrant.
    
    Filters:
    - limit: Maximum number of predictions to return
    - network_id: Filter by specific network
    - min_probability: Minimum conflict probability threshold
    """
    try:
        logger.info(f"📊 Fetching ML predictions (limit={limit}, network={network_id})")
        
        qdrant_service = get_qdrant_service()
        
        # Ensure collection exists
        try:
            qdrant_service.ensure_collections()
        except Exception as e:
            logger.warning(f"Could not ensure collections: {e}")
        
        # Build filter
        filter_conditions = {
            "must": [
                {"key": "source", "match": {"value": "ml_prediction"}}
            ]
        }
        
        if network_id:
            filter_conditions["must"].append({
                "key": "network_id",
                "match": {"value": network_id}
            })
        
        if min_probability is not None:
            filter_conditions["must"].append({
                "key": "probability",
                "range": {"gte": min_probability}
            })
        
        # Use Qdrant client's scroll method to retrieve points with filters
        from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
        
        scroll_filter = None
        if filter_conditions["must"]:
            must_conditions = []
            for condition in filter_conditions["must"]:
                if "match" in condition:
                    must_conditions.append(
                        FieldCondition(key=condition["key"], match=MatchValue(value=condition["match"]["value"]))
                    )
                elif "range" in condition:
                    must_conditions.append(
                        FieldCondition(key=condition["key"], range=Range(**condition["range"]))
                    )
            scroll_filter = Filter(must=must_conditions)
        
        # Check if collection exists and has data
        try:
            collection_info = qdrant_service.client.get_collection("pre_conflict_memory")
            if collection_info.points_count == 0:
                logger.info("No ML predictions stored yet")
                return []
        except Exception as e:
            logger.warning(f"Collection check failed: {e}")
            return []
        
        results, _ = qdrant_service.client.scroll(
            collection_name="pre_conflict_memory",
            scroll_filter=scroll_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        
        # Convert to response format
        alerts = []
        for result in results:
            payload = result.payload
            alerts.append(MLPredictionAlert(
                id=payload.get("prediction_id", str(result.id)),
                network_id=payload.get("network_id", "unknown"),
                severity=payload.get("severity", "medium"),
                risk_level=payload.get("risk_level", "MEDIUM"),
                probability=payload.get("probability", 0.0),
                confidence=payload.get("confidence", 0.0),
                train_count=payload.get("train_count", 0),
                contributing_factors=payload.get("contributing_factors", "").split(", "),
                recommended_action=payload.get("recommended_action"),
                alert_message=payload.get("alert_message", "Conflict predicted"),
                detected_at=datetime.fromisoformat(payload.get("detected_at", datetime.now().isoformat())),
                source=payload.get("source", "ml_prediction")
            ))
        
        logger.info(f"✅ Retrieved {len(alerts)} ML predictions")
        return alerts
        
    except Exception as e:
        logger.error(f"Error retrieving ML predictions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving ML predictions: {str(e)}"
        )


def determine_conflict_type(contributing_factors: List[str]) -> ConflictType:
    """Determine conflict type from contributing factors"""
    factors_text = " ".join(contributing_factors).lower()
    
    if "delay" in factors_text or "schedule" in factors_text:
        return ConflictType.TIMETABLE_CONFLICT
    elif "speed" in factors_text or "slow" in factors_text:
        return ConflictType.HEADWAY_CONFLICT
    elif "congestion" in factors_text or "density" in factors_text or "capacity" in factors_text:
        return ConflictType.CAPACITY_OVERLOAD
    elif "blockage" in factors_text or "occupied" in factors_text:
        return ConflictType.TRACK_BLOCKAGE
    elif "signal" in factors_text:
        return ConflictType.SIGNAL_FAILURE
    elif "platform" in factors_text:
        return ConflictType.PLATFORM_CONFLICT
    else:
        return ConflictType.TIMETABLE_CONFLICT  # Default
