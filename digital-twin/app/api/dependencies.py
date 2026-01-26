"""
FastAPI dependency injection functions.

Provides reusable dependencies for route handlers,
including database connections, services, and authentication.
"""

from typing import Generator

from app.services.embedding_service import EmbeddingService
from app.services.qdrant_service import QdrantService
from app.services.simulation_service import SimulationService
from app.services.recommendation_service import RecommendationService


def get_embedding_service() -> EmbeddingService:
    """
    Dependency for embedding service.
    
    Returns:
        EmbeddingService instance.
    """
    # TODO: Return singleton or create new instance
    return EmbeddingService()


def get_qdrant_service() -> QdrantService:
    """
    Dependency for Qdrant vector database service.
    
    Returns:
        QdrantService instance.
    """
    # TODO: Return configured Qdrant service
    return QdrantService()


def get_simulation_service() -> SimulationService:
    """
    Dependency for digital twin simulation service.
    
    Returns:
        SimulationService instance.
    """
    return SimulationService()


def get_recommendation_service() -> RecommendationService:
    """
    Dependency for recommendation engine service.
    
    Returns:
        RecommendationService instance.
    """
    return RecommendationService()
