"""
Qdrant Cloud database connection and initialization.

Handles Qdrant client creation and collection setup for cloud deployment.
"""

from typing import Optional
from functools import lru_cache

from app.core.config import settings
from app.core.exceptions import QdrantConnectionError


@lru_cache()
def get_qdrant_client():
    """
    Get or create a Qdrant Cloud client instance.
    
    Connects to Qdrant Cloud using URL and API key authentication.
    The client is cached for reuse across the application.
    
    Returns:
        QdrantClient: Connected Qdrant Cloud client.
        
    Raises:
        QdrantConnectionError: If connection fails.
    
    Example:
        >>> from app.db.qdrant import get_qdrant_client
        >>> client = get_qdrant_client()
        >>> collections = client.get_collections()
    """
    try:
        from qdrant_client import QdrantClient
        
        # Connect to Qdrant Cloud with URL and API key
        client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=settings.QDRANT_TIMEOUT,
        )
        
        # Test connection by fetching collections
        client.get_collections()
        
        return client
    except Exception as e:
        raise QdrantConnectionError(
            f"Failed to connect to Qdrant Cloud at {settings.QDRANT_URL}",
            {"error": str(e)}
        )


def init_collections(client=None, recreate: bool = False):
    """
    Initialize required Qdrant collections.
    
    Creates the necessary collections for storing conflict vectors
    if they don't already exist.
    
    Args:
        client: Optional Qdrant client (uses default if not provided).
        recreate: Whether to recreate existing collections (WARNING: deletes data).
    
    Example:
        >>> from app.db.qdrant import init_collections
        >>> init_collections()  # Create collections if missing
        >>> init_collections(recreate=True)  # Recreate collections (deletes data)
    """
    from qdrant_client.models import Distance, VectorParams
    
    if client is None:
        client = get_qdrant_client()
    
    # Define collections to create
    collections_config = [
        {
            "name": settings.QDRANT_COLLECTION,
            "vector_size": settings.EMBEDDING_DIMENSION,
            "distance": Distance.COSINE
        },
        {
            "name": f"{settings.QDRANT_COLLECTION}_outcomes",
            "vector_size": settings.EMBEDDING_DIMENSION,
            "distance": Distance.COSINE
        }
    ]
    
    # Get existing collections
    existing = {c.name for c in client.get_collections().collections}
    
    for config in collections_config:
        if config["name"] in existing:
            if recreate:
                client.delete_collection(config["name"])
            else:
                continue
        
        # Create new collection
        client.create_collection(
            collection_name=config["name"],
            vectors_config=VectorParams(
                size=config["vector_size"],
                distance=config["distance"]
            )
        )


def get_collection_info(collection_name: str = None) -> dict:
    """
    Get information about a Qdrant collection.
    
    Args:
        collection_name: Name of collection (defaults to main collection).
        
    Returns:
        Dictionary with collection info (vectors_count, status, etc.).
    """
    client = get_qdrant_client()
    name = collection_name or settings.QDRANT_COLLECTION
    
    info = client.get_collection(name)
    return {
        "name": name,
        "vectors_count": info.vectors_count,
        "points_count": info.points_count,
        "status": info.status.value,
        "optimizer_status": info.optimizer_status.status.value,
    }


async def close_qdrant_connection():
    """Close the Qdrant connection and clear cache."""
    get_qdrant_client.cache_clear()
