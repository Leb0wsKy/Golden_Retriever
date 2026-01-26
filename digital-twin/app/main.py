"""
Main entrypoint for the Golden Retriever FastAPI application.

This module initializes and configures the FastAPI application,
including routers, middleware, and startup/shutdown events.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.core.config import settings


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

    @app.on_event("startup")
    async def startup_event():
        """Initialize services on application startup."""
        # TODO: Initialize Qdrant connection
        # TODO: Load embedding model
        pass

    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup resources on application shutdown."""
        # TODO: Close database connections
        # TODO: Cleanup resources
        pass

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": settings.APP_VERSION}

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
