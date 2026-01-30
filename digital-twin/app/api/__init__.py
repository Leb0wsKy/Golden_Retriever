"""
API layer for the Golden Retriever application.

This package contains all FastAPI routers and endpoint definitions
for handling HTTP requests related to rail conflict resolution.
"""

from fastapi import APIRouter

from app.api.routes import conflicts, recommendations, preventive_alerts, ml_predictions

# Main API router that aggregates all route modules
router = APIRouter()

# Include sub-routers
router.include_router(conflicts.router, prefix="/conflicts", tags=["Conflicts"])
router.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])
router.include_router(preventive_alerts.router, prefix="/preventive-alerts", tags=["Preventive Alerts"])
router.include_router(ml_predictions.router, prefix="/ml", tags=["ML Predictions"])
