"""
Main entrypoint for the Golden Retriever FastAPI application.

This module initializes and configures the FastAPI application,
including routers, middleware, and startup/shutdown events.
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.core.config import settings


logger = logging.getLogger(__name__)


# Background task for periodic Transitland conflict generation
_background_task: asyncio.Task = None
_pre_conflict_scan_task: asyncio.Task = None  # NEW: Pre-conflict scanning task
_should_run_background = True


async def periodic_transitland_conflict_generation():
    """
    Background task that periodically generates conflicts from Transitland schedules.
    
    This runs every 30 minutes (configurable) and automatically:
    1. Fetches real schedule data from Transitland
    2. Generates conflicts based on actual timetables
    3. Stores them in Qdrant with embeddings
    
    This keeps the system populated with fresh, realistic conflict data.
    """
    from app.services.transitland_conflict_service import get_transitland_conflict_service
    
    # Wait 60 seconds after startup before first generation
    await asyncio.sleep(60)
    
    while _should_run_background:
        try:
            logger.info("🚂 Starting periodic Transitland conflict generation...")
            
            service = get_transitland_conflict_service()
            result = await service.generate_and_store_conflicts()
            
            if result.success:
                logger.info(
                    f"✅ Generated {result.conflicts_generated} conflicts "
                    f"({result.schedule_based_count} from schedules, "
                    f"{result.synthetic_count} synthetic). "
                    f"{result.conflicts_stored} stored in Qdrant."
                )
            else:
                logger.warning(
                    f"⚠️ Conflict generation had errors: {result.errors}"
                )
            
        except Exception as e:
            logger.error(f"Background conflict generation failed: {e}", exc_info=True)
        
        # Wait 30 minutes before next run (1800 seconds)
        # Set to 600 (10 min) for testing, or 1800 (30 min) for production
        await asyncio.sleep(1800)


async def periodic_pre_conflict_scanning():
    """
    Background task for predictive conflict detection.
    
    This runs every 10 minutes and:
    1. Captures current network state
    2. Searches pre-conflict memory for similar historical patterns
    3. Identifies patterns that previously led to conflicts
    4. Generates preventive alerts for operators
    
    This implements the proposal requirement for "predictive capability
    that identifies conflicts before they materialize."
    """
    from app.services.pre_conflict_scanner import get_pre_conflict_scanner
    
    # Wait 90 seconds after startup before first scan
    await asyncio.sleep(90)
    
    while _should_run_background:
        try:
            logger.info("🔍 Starting periodic pre-conflict pattern scan...")
            
            scanner = get_pre_conflict_scanner()
            result = await scanner.scan_for_emerging_conflicts()
            
            if result.success:
                if result.alerts_generated > 0:
                    logger.warning(
                        f"⚠️ PREVENTIVE ALERTS: {result.alerts_generated} emerging "
                        f"conflicts detected from {result.patterns_checked} patterns"
                    )
                    for alert in result.alerts:
                        logger.warning(
                            f"   Alert: {alert.predicted_conflict_type.value} at "
                            f"{alert.predicted_location} in ~{alert.time_to_conflict_minutes}min "
                            f"(confidence: {alert.confidence:.0%})"
                        )
                else:
                    logger.info(
                        f"✅ No emerging conflicts detected "
                        f"({result.patterns_checked} patterns checked)"
                    )
            else:
                logger.warning(
                    f"⚠️ Pre-conflict scan had errors: {result.errors}"
                )
            
        except Exception as e:
            logger.error(f"Background pre-conflict scan failed: {e}", exc_info=True)
        
        # Wait 10 minutes before next scan (600 seconds)
        await asyncio.sleep(600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    Handles:
    - Service initialization on startup
    - Background task management
    - Cleanup on shutdown
    """
    global _background_task, _pre_conflict_scan_task, _should_run_background
    
    # Startup
    logger.info("🚀 Starting Golden Retriever Digital Twin...")
    
    try:
        # Initialize Qdrant collections
        from app.services.qdrant_service import get_qdrant_service
        qdrant = get_qdrant_service()
        qdrant.ensure_collections()
        logger.info("✅ Qdrant collections initialized")
        
    except Exception as e:
        logger.error(f"⚠️ Qdrant initialization failed: {e}")
    
    try:
        # Load embedding model
        from app.services.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()
        # Trigger model load by embedding a test string
        _ = embedding_service.embed("test")
        logger.info("✅ Embedding model loaded")
        
    except Exception as e:
        logger.error(f"⚠️ Embedding model failed to load: {e}")
    
    # Start background Transitland conflict generation task
    try:
        _should_run_background = True
        _background_task = asyncio.create_task(periodic_transitland_conflict_generation())
        logger.info("✅ Background Transitland conflict generation started (runs every 30 min)")
    except Exception as e:
        logger.error(f"⚠️ Failed to start background task: {e}")
    
    # Start background pre-conflict scanning task (NEW)
    try:
        _pre_conflict_scan_task = asyncio.create_task(periodic_pre_conflict_scanning())
        logger.info("✅ Background pre-conflict scanning started (runs every 10 min)")
    except Exception as e:
        logger.error(f"⚠️ Failed to start pre-conflict scanner: {e}")
    
    logger.info("✅ Digital Twin ready!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Digital Twin...")
    
    # Stop background tasks
    _should_run_background = False
    
    if _background_task:
        _background_task.cancel()
        try:
            await _background_task
        except asyncio.CancelledError:
            pass
        logger.info("✅ Conflict generation task stopped")
    
    if _pre_conflict_scan_task:
        _pre_conflict_scan_task.cancel()
        try:
            await _pre_conflict_scan_task
        except asyncio.CancelledError:
            pass
        logger.info("✅ Pre-conflict scanning task stopped")
    
    logger.info("✅ Shutdown complete")


def create_app() -> FastAPI:
    """
    Application factory for creating the FastAPI instance.
    
    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-powered rail conflict resolution system using vector similarity search",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "background_tasks": {
                "conflict_generation": _background_task is not None and not _background_task.done(),
                "pre_conflict_scanning": _pre_conflict_scan_task is not None and not _pre_conflict_scan_task.done()
            }
        }

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
