"""
Preventive Alerts API endpoints.

Provides endpoints for:
- Getting current preventive alerts
- Manually triggering pre-conflict pattern scans
- Configuring alert thresholds
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.pre_conflict_scanner import (
    PreConflictScanner,
    PreventiveAlert,
    ScanResult,
    get_pre_conflict_scanner,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class ScanConfigRequest(BaseModel):
    """Configuration for pre-conflict scanning."""
    
    similarity_threshold: float = Field(
        default=0.75, ge=0, le=1,
        description="Minimum similarity to trigger alert (0-1)"
    )
    alert_confidence_threshold: float = Field(
        default=0.6, ge=0, le=1,
        description="Minimum confidence to generate alert (0-1)"
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "/",
    response_model=List[PreventiveAlert],
    summary="Get current preventive alerts",
    description=(
        "Scan current network state for patterns similar to historical "
        "pre-conflict conditions and return preventive alerts for emerging conflicts."
    )
)
async def get_preventive_alerts(
    min_confidence: float = Query(
        default=0.3, ge=0, le=1,
        description="Minimum confidence threshold for returned alerts"
    ),
    max_alerts: int = Query(
        default=10, ge=1, le=100,
        description="Maximum number of alerts to return"
    )
) -> List[PreventiveAlert]:
    """
    Get preventive alerts for emerging conflicts.
    
    This endpoint:
    1. Captures current network state
    2. Searches pre-conflict memory for similar historical patterns
    3. Returns alerts for patterns that previously led to conflicts
    4. Includes preventive recommendations to avoid disruptions
    
    Example response:
    ```json
    [
        {
            "alert_id": "alert-1706472823.123",
            "detected_at": "2026-01-28T14:30:00Z",
            "similarity_score": 0.85,
            "predicted_conflict_type": "track_blockage",
            "predicted_severity": "medium",
            "predicted_location": "London Waterloo",
            "time_to_conflict_minutes": 15,
            "recommended_actions": ["route_modification", "speed_regulation"],
            "explanation": "Current network state matches...",
            "confidence": 0.76
        }
    ]
    ```
    """
    try:
        logger.info("📡 Preventive alerts requested via API")
        
        # Get scanner instance
        scanner = get_pre_conflict_scanner()
        
        # Run scan
        result = await scanner.scan_for_emerging_conflicts()
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=f"Scan failed: {', '.join(result.errors)}"
            )
        
        # Filter by confidence threshold
        filtered_alerts = [
            alert for alert in result.alerts
            if alert.confidence >= min_confidence
        ]
        
        # Limit results
        filtered_alerts = filtered_alerts[:max_alerts]
        
        logger.info(
            f"✅ Returning {len(filtered_alerts)} preventive alerts "
            f"(from {result.alerts_generated} total)"
        )
        
        return filtered_alerts
        
    except Exception as e:
        logger.error(f"Failed to get preventive alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/scan",
    response_model=ScanResult,
    summary="Manually trigger pre-conflict scan",
    description="Immediately scan for emerging conflicts and return full scan results."
)
async def trigger_scan(
    config: Optional[ScanConfigRequest] = None
) -> ScanResult:
    """
    Manually trigger a pre-conflict pattern scan.
    
    Useful for:
    - Testing the scanning system
    - Getting full scan details (not just alerts)
    - Running custom scans with different thresholds
    
    Args:
        config: Optional configuration to override default thresholds
    
    Returns:
        Complete scan result including metadata
    """
    try:
        logger.info("🔍 Manual pre-conflict scan triggered via API")
        
        # Get scanner with optional custom config
        if config:
            scanner = PreConflictScanner(
                similarity_threshold=config.similarity_threshold,
                alert_confidence_threshold=config.alert_confidence_threshold
            )
        else:
            scanner = get_pre_conflict_scanner()
        
        # Run scan
        result = await scanner.scan_for_emerging_conflicts()
        
        logger.info(
            f"✅ Scan complete: {result.alerts_generated} alerts "
            f"from {result.patterns_checked} patterns"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Manual scan failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/health",
    summary="Check preventive alerts system health",
    description="Verify that pre-conflict scanning system is operational."
)
async def health_check():
    """
    Check health of preventive alerts system.
    
    Returns:
        Health status and system information
    """
    try:
        scanner = get_pre_conflict_scanner()
        
        return {
            "status": "healthy",
            "service": "pre_conflict_scanner",
            "similarity_threshold": scanner.similarity_threshold,
            "alert_confidence_threshold": scanner.alert_confidence_threshold,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"System unhealthy: {str(e)}"
        )
