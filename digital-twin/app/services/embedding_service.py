"""
Embedding service for generating vector representations.

Design Rationale:
-----------------
This service uses the sentence-transformers library with the all-MiniLM-L6-v2 model,
which provides an excellent balance between:
1. Performance: ~80MB model size, fast inference even on CPU
2. Quality: Strong semantic understanding for similarity search
3. Dimension: 384-dimensional vectors (compact yet expressive)

The model is cached at module level using a singleton pattern to:
- Avoid expensive model reloading on each request
- Share the model across multiple service instances
- Reduce memory footprint in production

Conflict objects are converted to natural language strings that capture:
- Semantic meaning (conflict type, severity, description)
- Contextual details (station, time of day, trains involved)
- Resolution history (strategy, outcome) when available

This structured text format allows the embedding model to learn meaningful
representations that cluster similar conflicts together in vector space.
"""

from __future__ import annotations

from typing import List, Union, Optional, TYPE_CHECKING
from functools import lru_cache
import logging

import numpy as np
import httpx

from app.core.config import settings
from app.core.exceptions import EmbeddingServiceError

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer
    from app.models.conflict import GeneratedConflict, ConflictBase

logger = logging.getLogger(__name__)

# Module-level model cache for singleton pattern
_model_cache: dict[str, "SentenceTransformer"] = {}


def _get_cached_model(model_name: str) -> "SentenceTransformer":
    """
    Load and cache a sentence-transformer model.
    
    This function implements a module-level singleton pattern for model loading.
    The model is loaded once and reused across all EmbeddingService instances,
    which is critical for production performance as model loading can take
    several seconds and consume significant memory.
    
    Args:
        model_name: Name of the sentence-transformer model to load.
            Supports HuggingFace model hub names (e.g., 'all-MiniLM-L6-v2')
            or local paths to saved models.
    
    Returns:
        Loaded SentenceTransformer model instance.
    
    Raises:
        EmbeddingServiceError: If model loading fails due to network issues,
            invalid model name, or insufficient memory.
    
    Note:
        The cache persists for the lifetime of the application process.
        To clear the cache (e.g., for testing), use clear_model_cache().
    """
    global _model_cache
    
    if model_name not in _model_cache:
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading embedding model: {model_name}")
            _model_cache[model_name] = SentenceTransformer(model_name)
            logger.info(f"Successfully loaded model: {model_name}")
            
        except ImportError as e:
            raise EmbeddingServiceError(
                "sentence-transformers library not installed. "
                "Install with: pip install sentence-transformers",
                {"error": str(e)}
            )
        except Exception as e:
            raise EmbeddingServiceError(
                f"Failed to load embedding model: {model_name}",
                {"error": str(e), "model": model_name}
            )
    
    return _model_cache[model_name]


def clear_model_cache() -> None:
    """
    Clear the model cache to free memory.
    
    Useful for testing or when switching between different models.
    After calling this, the next embed() call will reload the model.
    """
    global _model_cache
    _model_cache.clear()
    logger.info("Embedding model cache cleared")


class EmbeddingService:
    """
    Service for generating text embeddings using sentence-transformers.
    
    This service provides methods to convert text and conflict objects into
    dense vector embeddings suitable for similarity search in Qdrant.
    
    Design Choices:
    --------------
    1. **Model Selection (all-MiniLM-L6-v2)**:
       - 384-dimensional output vectors
       - Trained on 1B+ sentence pairs
       - Optimized for semantic similarity tasks
       - Fast inference (~14k sentences/sec on GPU, ~1k on CPU)
    
    2. **Caching Strategy**:
       - Model loaded once per process (singleton pattern)
       - Shared across all EmbeddingService instances
       - Memory-efficient for multi-threaded applications
    
    3. **Batch Processing**:
       - Supports both single texts and lists for batch efficiency
       - Reduces overhead from multiple model forward passes
       - Recommended for processing multiple conflicts at once
    
    4. **Conflict Text Generation**:
       - Converts structured conflict data to natural language
       - Includes all semantically relevant fields
       - Format optimized for embedding model understanding
    
    Attributes:
        model_name: Name of the sentence-transformer model being used.
        model: Reference to the cached SentenceTransformer instance.
    
    Example:
        >>> service = EmbeddingService()
        >>> embedding = service.embed("Platform conflict at King's Cross")
        >>> print(len(embedding))  # 384
        
        >>> # Batch processing
        >>> texts = ["Conflict A", "Conflict B", "Conflict C"]
        >>> embeddings = service.embed_batch(texts)
        >>> print(embeddings.shape)  # (3, 384)
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the embedding service with a specified model.
        
        The model is loaded lazily and cached globally, so creating multiple
        EmbeddingService instances is cheap and shares the same model.
        
        Args:
            model_name: Name of the sentence-transformer model to use.
                Defaults to settings.EMBEDDING_MODEL (all-MiniLM-L6-v2).
                Can be any model from HuggingFace's sentence-transformers.
        
        Raises:
            EmbeddingServiceError: If the model cannot be loaded.
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model: Optional["SentenceTransformer"] = None
    
    @property
    def model(self) -> "SentenceTransformer":
        """
        Get the cached model instance, loading it if necessary.
        
        Uses lazy loading to defer model initialization until first use,
        which improves application startup time.
        
        Returns:
            The loaded SentenceTransformer model.
        """
        if self._model is None:
            self._model = _get_cached_model(self.model_name)
        return self._model
    
    @property
    def dimension(self) -> int:
        """
        Get the embedding vector dimension.
        
        Returns:
            The dimension of embedding vectors (384 for all-MiniLM-L6-v2).
        """
        return settings.EMBEDDING_DIMENSION
    
    def embed(self, text: str) -> List[float]:
        """
        Generate an embedding for a single text string.
        
        First attempts to use AI Service if enabled, falls back to local model.
        
        Converts the input text into a dense vector representation that
        captures its semantic meaning. Similar texts will have similar
        embeddings (high cosine similarity).
        
        Args:
            text: The text to embed. Can be a sentence, paragraph, or
                short document. Best results with texts under 512 tokens.
        
        Returns:
            A list of floats representing the embedding vector.
            Length equals self.dimension (384 for all-MiniLM-L6-v2).
        
        Raises:
            EmbeddingServiceError: If embedding generation fails.
        
        Example:
            >>> service = EmbeddingService()
            >>> vec = service.embed("Train IC101 delayed at platform 5")
            >>> len(vec)
            384
        """
        # Try AI Service first if enabled
        if settings.AI_SERVICE_ENABLED and settings.AI_SERVICE_URL:
            try:
                return self._embed_via_ai_service(text)
            except Exception as e:
                logger.warning(
                    f"AI Service unavailable, using local model: {e}",
                    extra={"ai_service_url": settings.AI_SERVICE_URL}
                )
        
        # Fallback to local embedding generation
        return self._embed_local(text)
    
    def _embed_via_ai_service(self, text: str) -> List[float]:
        """
        Generate embedding via AI Service HTTP API.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
            
        Raises:
            Exception: If AI Service request fails
        """
        try:
            with httpx.Client(timeout=settings.AI_SERVICE_TIMEOUT) as client:
                response = client.post(
                    f"{settings.AI_SERVICE_URL}/embed",
                    json={"text": text}
                )
                response.raise_for_status()
                result = response.json()
                
                logger.debug(
                    "Generated embedding via AI Service",
                    extra={
                        "text_length": len(text),
                        "dimension": result.get("dimension")
                    }
                )
                
                return result["vector"]
                
        except httpx.TimeoutException as e:
            raise Exception(f"AI Service timeout after {settings.AI_SERVICE_TIMEOUT}s") from e
        except httpx.HTTPStatusError as e:
            raise Exception(f"AI Service HTTP error: {e.response.status_code}") from e
        except (httpx.RequestError, KeyError) as e:
            raise Exception(f"AI Service request failed: {e}") from e
    
    def _embed_local(self, text: str) -> List[float]:
        """
        Generate embedding using local sentence-transformers model.
        
        This is the fallback method when AI Service is unavailable.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
            
        Raises:
            EmbeddingServiceError: If local embedding fails
        """
        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True  # L2 normalize for cosine similarity
            )
            logger.debug(
                "Generated embedding via local model",
                extra={"text_length": len(text)}
            )
            return embedding.tolist()
        except Exception as e:
            raise EmbeddingServiceError(
                "Failed to generate embedding (local model)",
                {"error": str(e), "text_length": len(text)}
            )
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        First attempts to use AI Service if enabled, falls back to local model.
        
        Batch processing is significantly faster than calling embed() in a loop
        because it:
        1. Reduces Python function call overhead
        2. Enables GPU parallelization (if available)
        3. Optimizes memory allocation
        
        Args:
            texts: List of text strings to embed.
            batch_size: Number of texts to process at once. Larger batches
                are faster but use more memory. Default 32 is a good balance.
        
        Returns:
            List of embedding vectors, one per input text.
            Each vector is a list of floats with length self.dimension.
        
        Raises:
            EmbeddingServiceError: If embedding generation fails.
        
        Example:
            >>> service = EmbeddingService()
            >>> texts = ["Conflict at King's Cross", "Delay at Paddington"]
            >>> embeddings = service.embed_batch(texts)
            >>> len(embeddings)
            2
            >>> len(embeddings[0])
            384
        """
        if not texts:
            return []
        
        # Try AI Service first if enabled
        if settings.AI_SERVICE_ENABLED and settings.AI_SERVICE_URL:
            try:
                return self._embed_batch_via_ai_service(texts)
            except Exception as e:
                logger.warning(
                    f"AI Service batch embedding unavailable, using local model: {e}",
                    extra={"ai_service_url": settings.AI_SERVICE_URL, "text_count": len(texts)}
                )
        
        # Fallback to local batch embedding
        return self._embed_batch_local(texts, batch_size)
    
    def _embed_batch_via_ai_service(self, texts: List[str]) -> List[List[float]]:
        """
        Generate batch embeddings via AI Service HTTP API.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            Exception: If AI Service request fails
        """
        try:
            with httpx.Client(timeout=max(settings.AI_SERVICE_TIMEOUT * 2, 30)) as client:
                response = client.post(
                    f"{settings.AI_SERVICE_URL}/embed_batch",
                    json={"texts": texts}
                )
                response.raise_for_status()
                result = response.json()
                
                logger.debug(
                    "Generated batch embeddings via AI Service",
                    extra={"text_count": len(texts), "dimension": result.get("dimension")}
                )
                
                return result["vectors"]
                
        except httpx.TimeoutException as e:
            raise Exception(f"AI Service batch timeout") from e
        except httpx.HTTPStatusError as e:
            raise Exception(f"AI Service HTTP error: {e.response.status_code}") from e
        except (httpx.RequestError, KeyError) as e:
            raise Exception(f"AI Service batch request failed: {e}") from e
    
    def _embed_batch_local(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate batch embeddings using local model.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            List of embedding vectors
            
        Raises:
            EmbeddingServiceError: If local embedding fails
        """
        try:
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 100  # Show progress for large batches
            )
            return embeddings.tolist()
        except Exception as e:
            raise EmbeddingServiceError(
                "Failed to generate batch embeddings",
                {"error": str(e), "batch_size": len(texts)}
            )
    
    def conflict_to_text(self, conflict: Union["GeneratedConflict", "ConflictBase", dict]) -> str:
        """
        Convert a conflict object into a descriptive natural language string.
        
        This method transforms structured conflict data into a human-readable
        text format optimized for embedding generation. The text captures:
        
        1. **Core semantics**: Conflict type, severity, and description
        2. **Context**: Station, time of day, and environmental factors
        3. **Scope**: Affected trains and infrastructure
        4. **History**: Resolution strategy and outcome (if available)
        
        Design Rationale:
        ----------------
        The text format uses natural language rather than key-value pairs because:
        - Embedding models are trained on natural text, not structured data
        - Natural phrasing captures implicit relationships between concepts
        - Similar conflicts produce similar texts, enabling effective clustering
        
        The fields are ordered by semantic importance:
        - Type and severity first (most discriminative)
        - Location and time second (contextual)
        - Details and resolution last (supplementary)
        
        Args:
            conflict: A conflict object. Can be:
                - GeneratedConflict: Full conflict with resolution/outcome
                - ConflictBase: Basic conflict without resolution
                - dict: Dictionary with conflict fields
        
        Returns:
            A natural language description of the conflict suitable for embedding.
        
        Example:
            >>> conflict = GeneratedConflict(
            ...     conflict_type="platform_conflict",
            ...     severity="high",
            ...     station="King's Cross",
            ...     ...
            ... )
            >>> text = service.conflict_to_text(conflict)
            >>> print(text)
            "A high severity platform conflict occurred at King's Cross during 
             morning peak hours. Platform 3 was double-booked, causing IC101 
             arrival to conflict with RE205 departure. Trains affected: IC101, 
             RE205. Initial delay: 15 minutes. Resolution: Platform change with 
             85% confidence. Outcome: Successfully resolved with 5 minute delay."
        """
        # Handle both Pydantic models and dicts
        if hasattr(conflict, 'model_dump'):
            data = conflict.model_dump()
        elif hasattr(conflict, 'dict'):
            data = conflict.dict()
        else:
            data = dict(conflict)
        
        # Extract fields with defaults
        conflict_type = str(data.get('conflict_type', 'unknown')).replace('_', ' ')
        severity = str(data.get('severity', 'unknown'))
        station = data.get('station', 'unknown location')
        time_of_day = str(data.get('time_of_day', '')).replace('_', ' ')
        description = data.get('description', '')
        affected_trains = data.get('affected_trains', [])
        delay_before = data.get('delay_before', 0)
        platform = data.get('platform')
        track_section = data.get('track_section')
        
        # Build natural language text
        parts = []
        
        # Core conflict description
        parts.append(
            f"A {severity} severity {conflict_type} occurred at {station}"
        )
        
        # Time context
        if time_of_day:
            parts.append(f"during {time_of_day} hours")
        
        # Infrastructure details
        if platform:
            parts.append(f"at platform {platform}")
        if track_section:
            parts.append(f"on {track_section}")
        
        # Detailed description
        if description:
            parts.append(f". {description}")
        
        # Affected trains
        if affected_trains:
            train_list = ', '.join(affected_trains[:5])  # Limit to avoid too long text
            if len(affected_trains) > 5:
                train_list += f" and {len(affected_trains) - 5} more"
            parts.append(f". Trains affected: {train_list}")
        
        # Delay information
        if delay_before > 0:
            parts.append(f". Initial delay: {delay_before} minutes")
        
        # Resolution information (if available)
        resolution = data.get('recommended_resolution')
        if resolution:
            if isinstance(resolution, dict):
                strategy = str(resolution.get('strategy', '')).replace('_', ' ')
                confidence = resolution.get('confidence', 0)
                if strategy:
                    parts.append(
                        f". Resolution: {strategy} with {int(confidence * 100)}% confidence"
                    )
        
        # Outcome information (if available)
        outcome = data.get('final_outcome')
        if outcome:
            if isinstance(outcome, dict):
                result = str(outcome.get('outcome', '')).replace('_', ' ')
                actual_delay = outcome.get('actual_delay', 0)
                if result:
                    parts.append(
                        f". Outcome: {result} with {actual_delay} minute delay"
                    )
        
        return ' '.join(parts)
    
    def embed_conflict(self, conflict: Union["GeneratedConflict", "ConflictBase", dict]) -> List[float]:
        """
        Generate an embedding for a single conflict object.
        
        This is a convenience method that combines conflict_to_text() and embed().
        Use this for single conflicts; for multiple conflicts, use embed_conflicts()
        for better performance.
        
        Args:
            conflict: A conflict object (Pydantic model or dict).
        
        Returns:
            A list of floats representing the conflict's embedding vector.
        
        Raises:
            EmbeddingServiceError: If embedding generation fails.
        
        Example:
            >>> conflict = generator.generate(count=1)[0]
            >>> embedding = service.embed_conflict(conflict)
            >>> len(embedding)
            384
        """
        text = self.conflict_to_text(conflict)
        return self.embed(text)
    
    def embed_conflicts(
        self,
        conflicts: List[Union["GeneratedConflict", "ConflictBase", dict]],
        batch_size: int = 32
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple conflicts efficiently.
        
        This method converts all conflicts to text first, then processes them
        as a batch for optimal performance. Recommended for bulk operations
        like seeding a vector database or processing historical data.
        
        Args:
            conflicts: List of conflict objects to embed.
            batch_size: Number of conflicts to process at once.
        
        Returns:
            List of embedding vectors, one per input conflict.
        
        Raises:
            EmbeddingServiceError: If embedding generation fails.
        
        Example:
            >>> conflicts = generator.generate(count=100)
            >>> embeddings = service.embed_conflicts(conflicts)
            >>> len(embeddings)
            100
        """
        texts = [self.conflict_to_text(c) for c in conflicts]
        return self.embed_batch(texts, batch_size=batch_size)


# Factory function for dependency injection
@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """
    Get a singleton EmbeddingService instance.
    
    This factory function is intended for use with FastAPI's dependency
    injection system. The instance is cached, ensuring a single service
    is used throughout the application.
    
    Returns:
        The singleton EmbeddingService instance.
    
    Example:
        >>> from fastapi import Depends
        >>> 
        >>> @app.get("/embed")
        >>> async def embed_text(
        ...     text: str,
        ...     service: EmbeddingService = Depends(get_embedding_service)
        ... ):
        ...     return {"embedding": service.embed(text)}
    """
    return EmbeddingService()
