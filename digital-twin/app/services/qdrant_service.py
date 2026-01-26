"""
Qdrant Cloud vector database service.

This service handles all interactions with the Qdrant Cloud vector database
for storing and retrieving conflict embeddings and pre-conflict states.

Design Rationale:
----------------
1. **Two Collections Architecture**:
   - `conflict_memory`: Stores resolved conflicts with their resolutions and outcomes.
     Used for similarity search to find relevant historical conflicts.
   - `pre_conflict_memory`: Stores pre-conflict network states (train positions,
     platform occupancy, etc.) for pattern recognition and prediction.

2. **Vector Configuration**:
   - 384 dimensions to match the all-MiniLM-L6-v2 embedding model
   - Cosine distance for semantic similarity (works best with normalized vectors)

3. **Type Safety**:
   - All methods accept and return Pydantic models
   - Strong typing enables IDE support and runtime validation
   - Clear contracts between service and consumers

4. **Connection Management**:
   - Lazy connection (connects on first use)
   - Connection pooling via Qdrant client
   - Automatic reconnection on failure
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from datetime import datetime
from enum import Enum
import uuid
import logging

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import QdrantConnectionError, QdrantQueryError

if TYPE_CHECKING:
    from qdrant_client import QdrantClient
    from app.models.conflict import GeneratedConflict, ConflictBase

logger = logging.getLogger(__name__)


# =============================================================================
# Collection Names
# =============================================================================

class CollectionName(str, Enum):
    """
    Qdrant collection names used by the service.
    
    Using an enum prevents typos and enables autocomplete.
    """
    CONFLICT_MEMORY = "conflict_memory"
    PRE_CONFLICT_MEMORY = "pre_conflict_memory"


def _string_to_uuid(s: str) -> str:
    """
    Convert a string ID to a valid UUID for Qdrant.
    
    Qdrant Cloud requires either unsigned integers or UUIDs as point IDs.
    This function deterministically converts any string to a valid UUID.
    
    Args:
        s: Any string ID (e.g., "conflict-abc123")
    
    Returns:
        A valid UUID string derived from the input
    """
    # Use uuid5 with a namespace to create deterministic UUIDs from strings
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, s))


# =============================================================================
# Response Models
# =============================================================================

class SimilarConflict(BaseModel):
    """
    A conflict returned from similarity search.
    
    Attributes:
        id: Unique identifier of the conflict in Qdrant.
        score: Similarity score (0-1 for cosine, higher is more similar).
        conflict_type: Type of the conflict.
        severity: Severity level.
        station: Station where conflict occurred.
        time_of_day: Time period of the conflict.
        affected_trains: List of affected train IDs.
        delay_before: Initial delay in minutes.
        description: Conflict description.
        resolution_strategy: Strategy that was used to resolve.
        resolution_outcome: Outcome of the resolution attempt.
        resolution_confidence: Confidence of the original recommendation.
        actual_delay_after: Actual delay after resolution.
        detected_at: When the conflict was originally detected.
    """
    id: str = Field(..., description="Qdrant point ID")
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    
    # Conflict details
    conflict_type: str = Field(..., description="Type of conflict")
    severity: str = Field(..., description="Severity level")
    station: str = Field(..., description="Station name")
    time_of_day: str = Field(..., description="Time period")
    affected_trains: List[str] = Field(default_factory=list)
    delay_before: int = Field(default=0, ge=0)
    description: str = Field(default="")
    
    # Resolution details
    resolution_strategy: Optional[str] = Field(default=None)
    resolution_outcome: Optional[str] = Field(default=None)
    resolution_confidence: Optional[float] = Field(default=None)
    actual_delay_after: Optional[int] = Field(default=None)
    
    # Timestamps
    detected_at: Optional[datetime] = Field(default=None)
    
    # Full payload for additional data
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """
    Result of a similarity search operation.
    
    Attributes:
        query_id: Optional ID of the query conflict.
        matches: List of similar conflicts found.
        total_matches: Total number of matches found.
        search_time_ms: Time taken for the search in milliseconds.
    """
    query_id: Optional[str] = Field(default=None)
    matches: List[SimilarConflict] = Field(default_factory=list)
    total_matches: int = Field(default=0, ge=0)
    search_time_ms: Optional[float] = Field(default=None)


class UpsertResult(BaseModel):
    """
    Result of an upsert operation.
    
    Attributes:
        id: ID of the upserted point.
        collection: Collection name where point was upserted.
        success: Whether the operation was successful.
    """
    id: str = Field(..., description="Point ID")
    collection: str = Field(..., description="Collection name")
    success: bool = Field(default=True)


class PreConflictState(BaseModel):
    """
    Pre-conflict network state for pattern recognition.
    
    Captures the state of the rail network before a conflict occurs,
    enabling predictive analytics and early warning systems.
    
    Attributes:
        id: Unique identifier for this state snapshot.
        timestamp: When this state was captured.
        station: Primary station for this state.
        time_of_day: Time period of the state.
        platform_occupancy: Map of platform -> train ID or None.
        approaching_trains: List of trains approaching the station.
        departing_trains: List of trains scheduled to depart.
        current_delays: Map of train ID -> current delay in minutes.
        track_status: Map of track section -> status.
        conflict_occurred: Whether a conflict occurred after this state.
        conflict_type: Type of conflict that occurred (if any).
        conflict_id: ID of the resulting conflict (if any).
        metadata: Additional state information.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    station: str = Field(..., description="Primary station")
    time_of_day: str = Field(..., description="Time period")
    
    # Platform state
    platform_occupancy: Dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Map of platform -> train ID (None if empty)"
    )
    
    # Train movements
    approaching_trains: List[str] = Field(default_factory=list)
    departing_trains: List[str] = Field(default_factory=list)
    
    # Delay information
    current_delays: Dict[str, int] = Field(
        default_factory=dict,
        description="Map of train ID -> delay in minutes"
    )
    
    # Track status
    track_status: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of track section -> status"
    )
    
    # Conflict outcome
    conflict_occurred: bool = Field(default=False)
    conflict_type: Optional[str] = Field(default=None)
    conflict_id: Optional[str] = Field(default=None)
    
    # Additional data
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Qdrant Service
# =============================================================================

class QdrantService:
    """
    Service for interacting with Qdrant Cloud vector database.
    
    Manages two collections:
    - `conflict_memory`: Historical conflicts with resolutions and outcomes
    - `pre_conflict_memory`: Pre-conflict network states for pattern matching
    
    All methods accept Pydantic models and return typed results for
    full type safety and IDE support.
    
    Example:
        >>> from app.services.qdrant_service import QdrantService
        >>> from app.services.embedding_service import EmbeddingService
        >>> 
        >>> qdrant = QdrantService()
        >>> embedder = EmbeddingService()
        >>> 
        >>> # Upsert a conflict
        >>> conflict = generator.generate(count=1)[0]
        >>> embedding = embedder.embed_conflict(conflict)
        >>> result = qdrant.upsert_conflict(conflict, embedding)
        >>> 
        >>> # Search for similar conflicts
        >>> query_embedding = embedder.embed("Platform conflict at King's Cross")
        >>> results = qdrant.search_similar_conflicts(query_embedding, limit=5)
        >>> for match in results.matches:
        ...     print(f"{match.score:.2f}: {match.description}")
    
    Attributes:
        url: Qdrant Cloud cluster URL.
        api_key: Qdrant Cloud API key.
        _client: Lazy-loaded Qdrant client instance.
        _collections_initialized: Whether collections have been created.
    """
    
    # Vector configuration
    VECTOR_SIZE: int = 384  # Matches all-MiniLM-L6-v2
    
    def __init__(
        self,
        url: Optional[str] = None,
        api_key: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        """
        Initialize the Qdrant service.
        
        Connection is established lazily on first use.
        Supports both local (host:port) and cloud (url) configurations.
        
        Args:
            url: Optional Qdrant Cloud URL override.
            api_key: Optional API key override.
            host: Optional host for local Qdrant (default: localhost).
            port: Optional port for local Qdrant (default: 6333).
        """
        # Cloud URL takes precedence if provided
        self.url = url or settings.QDRANT_URL
        self.api_key = api_key or settings.QDRANT_API_KEY
        self.host = host or settings.QDRANT_HOST
        self.port = port or settings.QDRANT_PORT
        self._client: Optional["QdrantClient"] = None
        self._collections_initialized: bool = False
    
    @property
    def client(self) -> "QdrantClient":
        """
        Get the Qdrant client, connecting if necessary.
        
        Uses lazy initialization to defer connection until first use.
        
        Returns:
            Connected QdrantClient instance.
        
        Raises:
            QdrantConnectionError: If connection fails.
        """
        if self._client is None:
            self._connect()
        return self._client
    
    def _connect(self) -> None:
        """
        Establish connection to Qdrant (local or cloud).
        
        If QDRANT_URL is set, connects to Qdrant Cloud.
        Otherwise, connects to local Qdrant at host:port.
        
        Raises:
            QdrantConnectionError: If connection fails.
        """
        try:
            from qdrant_client import QdrantClient
            
            # Use cloud URL if provided, otherwise local
            if self.url:
                logger.info(f"Connecting to Qdrant Cloud at {self.url}")
                self._client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    timeout=settings.QDRANT_TIMEOUT,
                )
            else:
                logger.info(f"Connecting to local Qdrant at {self.host}:{self.port}")
                self._client = QdrantClient(
                    host=self.host,
                    port=self.port,
                    timeout=settings.QDRANT_TIMEOUT,
                )
            
            # Verify connection
            self._client.get_collections()
            logger.info("Successfully connected to Qdrant")
            
        except Exception as e:
            location = self.url if self.url else f"{self.host}:{self.port}"
            raise QdrantConnectionError(
                f"Failed to connect to Qdrant at {location}",
                {"error": str(e)}
            )
    
    def ensure_collections(self) -> None:
        """
        Ensure required collections exist, creating them if necessary.
        
        Creates both `conflict_memory` and `pre_conflict_memory` collections
        with the appropriate vector configuration.
        
        This method is idempotent - safe to call multiple times.
        """
        if self._collections_initialized:
            return
        
        try:
            from qdrant_client.models import Distance, VectorParams
            
            # Get existing collections
            existing = {c.name for c in self.client.get_collections().collections}
            
            # Create conflict_memory if missing
            if CollectionName.CONFLICT_MEMORY.value not in existing:
                logger.info(f"Creating collection: {CollectionName.CONFLICT_MEMORY.value}")
                self.client.create_collection(
                    collection_name=CollectionName.CONFLICT_MEMORY.value,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
            
            # Create pre_conflict_memory if missing
            if CollectionName.PRE_CONFLICT_MEMORY.value not in existing:
                logger.info(f"Creating collection: {CollectionName.PRE_CONFLICT_MEMORY.value}")
                self.client.create_collection(
                    collection_name=CollectionName.PRE_CONFLICT_MEMORY.value,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
            
            self._collections_initialized = True
            logger.info("All collections initialized")
            
        except Exception as e:
            raise QdrantQueryError(
                "Failed to ensure collections exist",
                {"error": str(e)}
            )
    
    def upsert_conflict(
        self,
        conflict: "GeneratedConflict",
        embedding: List[float],
        conflict_id: Optional[str] = None,
    ) -> UpsertResult:
        """
        Insert or update a conflict in the conflict_memory collection.
        
        Stores the conflict along with its resolution and outcome information
        for future similarity searches.
        
        Args:
            conflict: The conflict to store (Pydantic model).
            embedding: Vector embedding of the conflict (384 dimensions).
            conflict_id: Optional custom ID (uses conflict.id if not provided).
        
        Returns:
            UpsertResult with the point ID and success status.
        
        Raises:
            QdrantQueryError: If the upsert operation fails.
        
        Example:
            >>> conflict = generator.generate(count=1)[0]
            >>> embedding = embedder.embed_conflict(conflict)
            >>> result = qdrant.upsert_conflict(conflict, embedding)
            >>> print(f"Stored conflict with ID: {result.id}")
        """
        self.ensure_collections()
        
        try:
            from qdrant_client.models import PointStruct
            
            # Use provided ID or conflict's ID, convert to valid UUID for Qdrant
            original_id = conflict_id or conflict.id
            point_id = _string_to_uuid(original_id)
            
            # Build payload from conflict model (store original ID in payload)
            payload = self._conflict_to_payload(conflict)
            payload["original_conflict_id"] = original_id
            
            # Create point
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            
            # Upsert to Qdrant
            self.client.upsert(
                collection_name=CollectionName.CONFLICT_MEMORY.value,
                points=[point]
            )
            
            logger.debug(f"Upserted conflict {point_id} to conflict_memory")
            
            return UpsertResult(
                id=point_id,
                collection=CollectionName.CONFLICT_MEMORY.value,
                success=True
            )
            
        except Exception as e:
            raise QdrantQueryError(
                f"Failed to upsert conflict {conflict.id}",
                {"error": str(e), "conflict_id": conflict.id}
            )
    
    def upsert_conflict_raw(
        self,
        conflict_id: str,
        embedding: List[float],
        payload: Dict[str, Any],
    ) -> UpsertResult:
        """
        Insert or update a conflict with raw payload data.
        
        Use this method when you have pre-built payload data instead
        of a GeneratedConflict model (e.g., for analyzed conflicts).
        
        Args:
            conflict_id: Unique identifier for the conflict.
            embedding: Vector embedding of the conflict (384 dimensions).
            payload: Raw payload dictionary to store.
        
        Returns:
            UpsertResult with the point ID and success status.
        
        Raises:
            QdrantQueryError: If the upsert operation fails.
        """
        self.ensure_collections()
        
        try:
            from qdrant_client.models import PointStruct
            
            # Convert string ID to valid UUID for Qdrant
            point_id = _string_to_uuid(conflict_id)
            
            # Store original ID in payload
            payload["original_conflict_id"] = conflict_id
            
            # Create point
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            
            # Upsert to Qdrant
            self.client.upsert(
                collection_name=CollectionName.CONFLICT_MEMORY.value,
                points=[point]
            )
            
            logger.debug(f"Upserted raw conflict {conflict_id} (UUID: {point_id}) to conflict_memory")
            
            return UpsertResult(
                id=conflict_id,  # Return original ID for consistency
                collection=CollectionName.CONFLICT_MEMORY.value,
                success=True
            )
            
        except Exception as e:
            raise QdrantQueryError(
                f"Failed to upsert raw conflict {conflict_id}",
                {"error": str(e), "conflict_id": conflict_id}
            )
    
    def upsert_conflicts_batch(
        self,
        conflicts: List["GeneratedConflict"],
        embeddings: List[List[float]],
    ) -> List[UpsertResult]:
        """
        Batch upsert multiple conflicts efficiently.
        
        More efficient than calling upsert_conflict() in a loop as it
        uses a single network round-trip.
        
        Args:
            conflicts: List of conflicts to store.
            embeddings: List of embeddings (must match conflicts length).
        
        Returns:
            List of UpsertResult for each conflict.
        
        Raises:
            QdrantQueryError: If the batch upsert fails.
            ValueError: If conflicts and embeddings lengths don't match.
        """
        if len(conflicts) != len(embeddings):
            raise ValueError(
                f"Conflicts and embeddings count mismatch: "
                f"{len(conflicts)} vs {len(embeddings)}"
            )
        
        if not conflicts:
            return []
        
        self.ensure_collections()
        
        try:
            from qdrant_client.models import PointStruct
            
            points = []
            for conflict, embedding in zip(conflicts, embeddings):
                payload = self._conflict_to_payload(conflict)
                payload["original_conflict_id"] = conflict.id
                points.append(
                    PointStruct(
                        id=_string_to_uuid(conflict.id),
                        vector=embedding,
                        payload=payload
                    )
                )
            
            self.client.upsert(
                collection_name=CollectionName.CONFLICT_MEMORY.value,
                points=points
            )
            
            logger.info(f"Batch upserted {len(points)} conflicts")
            
            return [
                UpsertResult(
                    id=conflict.id,  # Return original ID
                    collection=CollectionName.CONFLICT_MEMORY.value,
                    success=True
                )
                for conflict in conflicts
            ]
            
        except Exception as e:
            raise QdrantQueryError(
                f"Failed to batch upsert {len(conflicts)} conflicts",
                {"error": str(e)}
            )
    
    def search_similar_conflicts(
        self,
        query_embedding: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> SearchResult:
        """
        Search for conflicts similar to a query embedding.
        
        Uses cosine similarity to find historical conflicts that are
        semantically similar to the query.
        
        Args:
            query_embedding: Vector embedding of the query (384 dimensions).
            limit: Maximum number of results to return (default 10).
            score_threshold: Minimum similarity score (0-1) to include.
            filter_conditions: Optional Qdrant filter conditions.
        
        Returns:
            SearchResult containing matching conflicts and metadata.
        
        Raises:
            QdrantQueryError: If the search fails.
        
        Example:
            >>> # Search for similar conflicts
            >>> embedding = embedder.embed("Platform 3 double-booking at rush hour")
            >>> results = qdrant.search_similar_conflicts(embedding, limit=5)
            >>> 
            >>> for match in results.matches:
            ...     print(f"Score: {match.score:.2f}")
            ...     print(f"  Type: {match.conflict_type}")
            ...     print(f"  Resolution: {match.resolution_strategy}")
            ...     print(f"  Outcome: {match.resolution_outcome}")
        """
        self.ensure_collections()
        
        try:
            import time
            start_time = time.time()
            
            # Build filter if provided
            query_filter = None
            if filter_conditions:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                
                conditions = []
                for field, value in filter_conditions.items():
                    conditions.append(
                        FieldCondition(key=field, match=MatchValue(value=value))
                    )
                query_filter = Filter(must=conditions)
            
            # Execute search
            results = self.client.search(
                collection_name=CollectionName.CONFLICT_MEMORY.value,
                query_vector=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter
            )
            
            search_time_ms = (time.time() - start_time) * 1000
            
            # Convert to typed models
            matches = [
                self._hit_to_similar_conflict(hit)
                for hit in results
            ]
            
            return SearchResult(
                matches=matches,
                total_matches=len(matches),
                search_time_ms=round(search_time_ms, 2)
            )
            
        except Exception as e:
            raise QdrantQueryError(
                "Failed to search similar conflicts",
                {"error": str(e), "limit": limit}
            )
    
    def upsert_pre_conflict_state(
        self,
        state: PreConflictState,
        embedding: List[float],
    ) -> UpsertResult:
        """
        Insert or update a pre-conflict state in the pre_conflict_memory collection.
        
        Pre-conflict states capture the network conditions before a conflict
        occurs, enabling pattern recognition and early warning systems.
        
        Args:
            state: The pre-conflict state to store (Pydantic model).
            embedding: Vector embedding of the state (384 dimensions).
        
        Returns:
            UpsertResult with the point ID and success status.
        
        Raises:
            QdrantQueryError: If the upsert operation fails.
        
        Example:
            >>> state = PreConflictState(
            ...     station="King's Cross",
            ...     time_of_day="morning_peak",
            ...     platform_occupancy={"1": "IC101", "2": None, "3": "RE205"},
            ...     approaching_trains=["S15", "IC102"],
            ...     conflict_occurred=True,
            ...     conflict_type="platform_conflict"
            ... )
            >>> embedding = embedder.embed(state_to_text(state))
            >>> result = qdrant.upsert_pre_conflict_state(state, embedding)
        """
        self.ensure_collections()
        
        try:
            from qdrant_client.models import PointStruct
            
            # Build payload from state model
            payload = state.model_dump(mode='json')
            payload["original_state_id"] = state.id
            
            # Convert string ID to valid UUID for Qdrant
            point_id = _string_to_uuid(state.id)
            
            # Create point
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            
            # Upsert to Qdrant
            self.client.upsert(
                collection_name=CollectionName.PRE_CONFLICT_MEMORY.value,
                points=[point]
            )
            
            logger.debug(f"Upserted pre-conflict state {state.id} (UUID: {point_id})")
            
            return UpsertResult(
                id=state.id,  # Return original ID
                collection=CollectionName.PRE_CONFLICT_MEMORY.value,
                success=True
            )
            
        except Exception as e:
            raise QdrantQueryError(
                f"Failed to upsert pre-conflict state {state.id}",
                {"error": str(e), "state_id": state.id}
            )
    
    def search_similar_pre_conflict_states(
        self,
        query_embedding: List[float],
        limit: int = 10,
        conflict_occurred_only: bool = False,
    ) -> List[PreConflictState]:
        """
        Search for pre-conflict states similar to a query.
        
        Useful for predicting conflicts based on current network state.
        
        Args:
            query_embedding: Vector embedding of the current state.
            limit: Maximum number of results.
            conflict_occurred_only: If True, only return states where conflicts occurred.
        
        Returns:
            List of similar PreConflictState objects.
        """
        self.ensure_collections()
        
        try:
            # Build filter for conflict_occurred if requested
            query_filter = None
            if conflict_occurred_only:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                
                query_filter = Filter(
                    must=[
                        FieldCondition(
                            key="conflict_occurred",
                            match=MatchValue(value=True)
                        )
                    ]
                )
            
            results = self.client.search(
                collection_name=CollectionName.PRE_CONFLICT_MEMORY.value,
                query_vector=query_embedding,
                limit=limit,
                query_filter=query_filter
            )
            
            return [
                PreConflictState(**hit.payload)
                for hit in results
            ]
            
        except Exception as e:
            raise QdrantQueryError(
                "Failed to search pre-conflict states",
                {"error": str(e)}
            )
    
    def get_conflict_by_id(self, conflict_id: str) -> Optional[SimilarConflict]:
        """
        Retrieve a specific conflict by its ID.
        
        Args:
            conflict_id: The ID of the conflict to retrieve.
        
        Returns:
            SimilarConflict if found, None otherwise.
        """
        self.ensure_collections()
        
        try:
            results = self.client.retrieve(
                collection_name=CollectionName.CONFLICT_MEMORY.value,
                ids=[conflict_id]
            )
            
            if not results:
                return None
            
            point = results[0]
            return SimilarConflict(
                id=str(point.id),
                score=1.0,  # Exact match
                **self._extract_conflict_fields(point.payload)
            )
            
        except Exception as e:
            raise QdrantQueryError(
                f"Failed to get conflict {conflict_id}",
                {"error": str(e)}
            )
    
    def delete_conflict(self, conflict_id: str) -> bool:
        """
        Delete a conflict from the conflict_memory collection.
        
        Args:
            conflict_id: ID of the conflict to delete.
        
        Returns:
            True if deletion was successful.
        """
        self.ensure_collections()
        
        try:
            self.client.delete(
                collection_name=CollectionName.CONFLICT_MEMORY.value,
                points_selector=[conflict_id]
            )
            logger.debug(f"Deleted conflict {conflict_id}")
            return True
            
        except Exception as e:
            raise QdrantQueryError(
                f"Failed to delete conflict {conflict_id}",
                {"error": str(e)}
            )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collections.
        
        Returns:
            Dictionary with collection statistics.
        """
        self.ensure_collections()
        
        stats = {}
        
        for collection in CollectionName:
            try:
                info = self.client.get_collection(collection.value)
                stats[collection.value] = {
                    "vectors_count": info.vectors_count,
                    "points_count": info.points_count,
                    "status": info.status.value if info.status else "unknown",
                }
            except Exception:
                stats[collection.value] = {"error": "Failed to get collection info"}
        
        return stats
    
    # =========================================================================
    # Private Helper Methods
    # =========================================================================
    
    def _conflict_to_payload(self, conflict: "GeneratedConflict") -> Dict[str, Any]:
        """
        Convert a GeneratedConflict to a Qdrant payload dictionary.
        
        Flattens nested structures for efficient filtering and retrieval.
        """
        # Get base fields via model_dump
        payload = conflict.model_dump(mode='json')
        
        # Flatten resolution fields for easier filtering
        if conflict.recommended_resolution:
            payload["resolution_strategy"] = str(conflict.recommended_resolution.strategy.value)
            payload["resolution_confidence"] = conflict.recommended_resolution.confidence
            payload["estimated_delay_reduction"] = conflict.recommended_resolution.estimated_delay_reduction
        
        # Flatten outcome fields
        if conflict.final_outcome:
            payload["resolution_outcome"] = str(conflict.final_outcome.outcome.value)
            payload["actual_delay_after"] = conflict.final_outcome.actual_delay
            payload["resolution_time_minutes"] = conflict.final_outcome.resolution_time_minutes
        
        # Convert enum values to strings for Qdrant compatibility
        payload["conflict_type"] = str(conflict.conflict_type.value)
        payload["severity"] = str(conflict.severity.value)
        payload["time_of_day"] = str(conflict.time_of_day.value)
        
        return payload
    
    def _hit_to_similar_conflict(self, hit) -> SimilarConflict:
        """
        Convert a Qdrant search hit to a SimilarConflict model.
        """
        payload = hit.payload or {}
        
        return SimilarConflict(
            id=str(hit.id),
            score=hit.score,
            **self._extract_conflict_fields(payload)
        )
    
    def _extract_conflict_fields(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and type conflict fields from a payload dictionary.
        """
        # Parse detected_at if present
        detected_at = None
        if payload.get("detected_at"):
            try:
                detected_at = datetime.fromisoformat(
                    payload["detected_at"].replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                pass
        
        return {
            "conflict_type": payload.get("conflict_type", "unknown"),
            "severity": payload.get("severity", "unknown"),
            "station": payload.get("station", ""),
            "time_of_day": payload.get("time_of_day", ""),
            "affected_trains": payload.get("affected_trains", []),
            "delay_before": payload.get("delay_before", 0),
            "description": payload.get("description", ""),
            "resolution_strategy": payload.get("resolution_strategy"),
            "resolution_outcome": payload.get("resolution_outcome"),
            "resolution_confidence": payload.get("resolution_confidence"),
            "actual_delay_after": payload.get("actual_delay_after"),
            "detected_at": detected_at,
            "metadata": {
                k: v for k, v in payload.items()
                if k not in {
                    "conflict_type", "severity", "station", "time_of_day",
                    "affected_trains", "delay_before", "description",
                    "resolution_strategy", "resolution_outcome",
                    "resolution_confidence", "actual_delay_after", "detected_at"
                }
            }
        }


# =============================================================================
# Factory Function
# =============================================================================

_qdrant_service_instance: Optional[QdrantService] = None


def get_qdrant_service() -> QdrantService:
    """
    Get a singleton QdrantService instance.
    
    This factory function is intended for use with FastAPI's dependency
    injection system.
    
    Returns:
        The singleton QdrantService instance.
    
    Example:
        >>> from fastapi import Depends
        >>> 
        >>> @app.post("/conflicts")
        >>> async def create_conflict(
        ...     service: QdrantService = Depends(get_qdrant_service)
        ... ):
        ...     ...
    """
    global _qdrant_service_instance
    
    if _qdrant_service_instance is None:
        _qdrant_service_instance = QdrantService()
    
    return _qdrant_service_instance


def clear_qdrant_service_cache() -> None:
    """Clear the singleton instance (useful for testing)."""
    global _qdrant_service_instance
    _qdrant_service_instance = None
