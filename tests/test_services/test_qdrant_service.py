"""
Unit tests for the Qdrant service.

Tests cover:
- Connection management
- Collection creation
- Conflict upsert and search
- Pre-conflict state operations
- Typed results
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from app.services.qdrant_service import (
    QdrantService,
    CollectionName,
    SimilarConflict,
    SearchResult,
    UpsertResult,
    PreConflictState,
    get_qdrant_service,
    clear_qdrant_service_cache,
)
from app.core.constants import (
    ConflictType,
    ConflictSeverity,
    TimeOfDay,
    ResolutionStrategy,
    ResolutionOutcome,
)

# Patch target for QdrantClient
QDRANT_CLIENT_PATH = 'qdrant_client.QdrantClient'


class TestCollectionNames:
    """Tests for collection name enum."""
    
    def test_conflict_memory_name(self):
        """Test conflict_memory collection name."""
        assert CollectionName.CONFLICT_MEMORY.value == "conflict_memory"
    
    def test_pre_conflict_memory_name(self):
        """Test pre_conflict_memory collection name."""
        assert CollectionName.PRE_CONFLICT_MEMORY.value == "pre_conflict_memory"


class TestQdrantServiceInit:
    """Tests for QdrantService initialization."""
    
    def test_default_initialization(self):
        """Test service initializes with default settings."""
        service = QdrantService()
        
        # Should not connect immediately (lazy)
        assert service._client is None
        assert service._collections_initialized is False
    
    def test_custom_url_and_api_key(self):
        """Test service accepts custom URL and API key."""
        service = QdrantService(
            url="https://custom.qdrant.io",
            api_key="custom-api-key"
        )
        
        assert service.url == "https://custom.qdrant.io"
        assert service.api_key == "custom-api-key"
    
    def test_vector_size_constant(self):
        """Test vector size is 384."""
        assert QdrantService.VECTOR_SIZE == 384


class TestConnectionManagement:
    """Tests for connection management."""
    
    @patch(QDRANT_CLIENT_PATH)
    def test_lazy_connection(self, mock_client_class):
        """Test that connection is lazy (not established on init)."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        service = QdrantService()
        
        # Client not created yet
        assert mock_client_class.call_count == 0
        
        # Access client property triggers connection
        _ = service.client
        
        assert mock_client_class.call_count == 1
    
    @patch(QDRANT_CLIENT_PATH)
    def test_connection_reuse(self, mock_client_class):
        """Test that client is reused on subsequent calls."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        service = QdrantService()
        
        # Multiple accesses
        _ = service.client
        _ = service.client
        _ = service.client
        
        # Still only one connection
        assert mock_client_class.call_count == 1


class TestCollectionCreation:
    """Tests for collection creation."""
    
    @pytest.fixture
    def mock_service(self):
        """Create service with mocked client."""
        with patch(QDRANT_CLIENT_PATH) as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_collections.return_value = MagicMock(collections=[])
            mock_client_class.return_value = mock_client
            
            service = QdrantService()
            yield service, mock_client
    
    def test_creates_both_collections(self, mock_service):
        """Test that ensure_collections creates both required collections."""
        service, mock_client = mock_service
        
        service.ensure_collections()
        
        # Should create both collections
        assert mock_client.create_collection.call_count == 2
        
        # Check collection names
        call_args_list = mock_client.create_collection.call_args_list
        collection_names = [call[1]['collection_name'] for call in call_args_list]
        
        assert "conflict_memory" in collection_names
        assert "pre_conflict_memory" in collection_names
    
    def test_skips_existing_collections(self, mock_service):
        """Test that existing collections are not recreated."""
        service, mock_client = mock_service
        
        # Simulate existing collections
        mock_collection1 = MagicMock()
        mock_collection1.name = "conflict_memory"
        mock_collection2 = MagicMock()
        mock_collection2.name = "pre_conflict_memory"
        
        mock_client.get_collections.return_value = MagicMock(
            collections=[mock_collection1, mock_collection2]
        )
        
        service.ensure_collections()
        
        # Should not create any collections
        assert mock_client.create_collection.call_count == 0
    
    def test_idempotent_collection_creation(self, mock_service):
        """Test that ensure_collections is idempotent."""
        service, mock_client = mock_service
        
        # Call multiple times
        service.ensure_collections()
        service.ensure_collections()
        service.ensure_collections()
        
        # Should only create once
        assert mock_client.create_collection.call_count == 2


class TestUpsertConflict:
    """Tests for conflict upsert operations."""
    
    @pytest.fixture
    def mock_service(self):
        """Create service with mocked client."""
        with patch(QDRANT_CLIENT_PATH) as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_collections.return_value = MagicMock(collections=[])
            mock_client_class.return_value = mock_client
            
            service = QdrantService()
            yield service, mock_client
    
    @pytest.fixture
    def sample_conflict(self):
        """Create a sample generated conflict."""
        from app.models.conflict import (
            GeneratedConflict,
            RecommendedResolution,
            FinalOutcome
        )
        
        return GeneratedConflict(
            id="test-conflict-123",
            conflict_type=ConflictType.PLATFORM_CONFLICT,
            severity=ConflictSeverity.HIGH,
            station="King's Cross",
            time_of_day=TimeOfDay.MORNING_PEAK,
            affected_trains=["IC101", "RE205"],
            delay_before=15,
            description="Platform 3 double-booked during rush hour",
            platform="3",
            recommended_resolution=RecommendedResolution(
                strategy=ResolutionStrategy.PLATFORM_CHANGE,
                confidence=0.85,
                estimated_delay_reduction=10,
                description="Redirect IC101 to Platform 5"
            ),
            final_outcome=FinalOutcome(
                outcome=ResolutionOutcome.SUCCESS,
                actual_delay=5,
                resolution_time_minutes=8,
                notes="Resolved successfully"
            )
        )
    
    def test_upsert_conflict_returns_result(self, mock_service, sample_conflict):
        """Test that upsert_conflict returns UpsertResult."""
        service, mock_client = mock_service
        embedding = [0.1] * 384
        
        result = service.upsert_conflict(sample_conflict, embedding)
        
        assert isinstance(result, UpsertResult)
        assert result.id == "test-conflict-123"
        assert result.collection == "conflict_memory"
        assert result.success is True
    
    def test_upsert_conflict_calls_client(self, mock_service, sample_conflict):
        """Test that upsert_conflict calls Qdrant client."""
        service, mock_client = mock_service
        embedding = [0.1] * 384
        
        service.upsert_conflict(sample_conflict, embedding)
        
        mock_client.upsert.assert_called_once()
        call_args = mock_client.upsert.call_args
        assert call_args[1]['collection_name'] == "conflict_memory"
    
    def test_upsert_conflict_with_custom_id(self, mock_service, sample_conflict):
        """Test upsert with custom ID."""
        service, mock_client = mock_service
        embedding = [0.1] * 384
        
        result = service.upsert_conflict(
            sample_conflict, 
            embedding,
            conflict_id="custom-id-456"
        )
        
        assert result.id == "custom-id-456"


class TestBatchUpsert:
    """Tests for batch upsert operations."""
    
    @pytest.fixture
    def mock_service(self):
        """Create service with mocked client."""
        with patch(QDRANT_CLIENT_PATH) as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_collections.return_value = MagicMock(collections=[])
            mock_client_class.return_value = mock_client
            
            service = QdrantService()
            yield service, mock_client
    
    def test_batch_upsert_empty_list(self, mock_service):
        """Test batch upsert with empty list."""
        service, mock_client = mock_service
        
        result = service.upsert_conflicts_batch([], [])
        
        assert result == []
        mock_client.upsert.assert_not_called()
    
    def test_batch_upsert_length_mismatch(self, mock_service):
        """Test batch upsert raises error on length mismatch."""
        service, mock_client = mock_service
        
        from app.models.conflict import (
            GeneratedConflict,
            RecommendedResolution,
            FinalOutcome
        )
        
        conflict = GeneratedConflict(
            id="test-1",
            conflict_type=ConflictType.PLATFORM_CONFLICT,
            severity=ConflictSeverity.MEDIUM,
            station="Test",
            time_of_day=TimeOfDay.MIDDAY,
            affected_trains=["T1"],
            description="Test conflict for batch test",
            recommended_resolution=RecommendedResolution(
                strategy=ResolutionStrategy.PLATFORM_CHANGE,
                confidence=0.8,
                description="Test resolution"
            ),
            final_outcome=FinalOutcome(outcome=ResolutionOutcome.SUCCESS)
        )
        
        with pytest.raises(ValueError, match="mismatch"):
            service.upsert_conflicts_batch(
                [conflict],
                [[0.1] * 384, [0.2] * 384]  # Too many embeddings
            )


class TestSearchSimilarConflicts:
    """Tests for similarity search."""
    
    @pytest.fixture
    def mock_service(self):
        """Create service with mocked client and search results."""
        with patch(QDRANT_CLIENT_PATH) as mock_client_class:
            mock_client = MagicMock()
            mock_client.get_collections.return_value = MagicMock(collections=[])
            
            # Mock search result
            mock_hit = MagicMock()
            mock_hit.id = "result-1"
            mock_hit.score = 0.95
            mock_hit.payload = {
                "conflict_type": "platform_conflict",
                "severity": "high",
                "station": "King's Cross",
                "time_of_day": "morning_peak",
                "affected_trains": ["IC101"],
                "delay_before": 10,
                "description": "Test conflict",
                "resolution_strategy": "platform_change",
                "resolution_outcome": "success",
                "resolution_confidence": 0.85,
                "actual_delay_after": 5,
            }
            
            mock_client.search.return_value = [mock_hit]
            mock_client_class.return_value = mock_client
            
            service = QdrantService()
            yield service, mock_client
    
    def test_search_returns_typed_result(self, mock_service):
        """Test that search returns SearchResult."""
        service, mock_client = mock_service
        query_embedding = [0.1] * 384
        
        result = service.search_similar_conflicts(query_embedding)
        
        assert isinstance(result, SearchResult)
        assert result.total_matches == 1
        assert result.search_time_ms is not None
    
    def test_search_matches_are_typed(self, mock_service):
        """Test that search matches are SimilarConflict objects."""
        service, mock_client = mock_service
        query_embedding = [0.1] * 384
        
        result = service.search_similar_conflicts(query_embedding)
        
        assert len(result.matches) == 1
        match = result.matches[0]
        
        assert isinstance(match, SimilarConflict)
        assert match.id == "result-1"
        assert match.score == 0.95
        assert match.conflict_type == "platform_conflict"
        assert match.station == "King's Cross"
        assert match.resolution_strategy == "platform_change"
    
    def test_search_with_limit(self, mock_service):
        """Test search respects limit parameter."""
        service, mock_client = mock_service
        query_embedding = [0.1] * 384
        
        service.search_similar_conflicts(query_embedding, limit=5)
        
        call_args = mock_client.search.call_args
        assert call_args[1]['limit'] == 5
    
    def test_search_with_score_threshold(self, mock_service):
        """Test search respects score_threshold parameter."""
        service, mock_client = mock_service
        query_embedding = [0.1] * 384
        
        service.search_similar_conflicts(query_embedding, score_threshold=0.8)
        
        call_args = mock_client.search.call_args
        assert call_args[1]['score_threshold'] == 0.8


class TestPreConflictState:
    """Tests for pre-conflict state operations."""
    
    def test_pre_conflict_state_model(self):
        """Test PreConflictState model creation."""
        state = PreConflictState(
            station="King's Cross",
            time_of_day="morning_peak",
            platform_occupancy={"1": "IC101", "2": None, "3": "RE205"},
            approaching_trains=["S15", "IC102"],
            departing_trains=["RE206"],
            current_delays={"IC101": 5},
            conflict_occurred=True,
            conflict_type="platform_conflict"
        )
        
        assert state.station == "King's Cross"
        assert state.platform_occupancy["1"] == "IC101"
        assert state.conflict_occurred is True
        assert state.id is not None  # Auto-generated
    
    @patch(QDRANT_CLIENT_PATH)
    def test_upsert_pre_conflict_state(self, mock_client_class):
        """Test upserting a pre-conflict state."""
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        mock_client_class.return_value = mock_client
        
        service = QdrantService()
        
        state = PreConflictState(
            station="King's Cross",
            time_of_day="morning_peak",
        )
        embedding = [0.1] * 384
        
        result = service.upsert_pre_conflict_state(state, embedding)
        
        assert isinstance(result, UpsertResult)
        assert result.collection == "pre_conflict_memory"
        assert result.success is True
        
        # Verify upsert was called
        mock_client.upsert.assert_called_once()
        call_args = mock_client.upsert.call_args
        assert call_args[1]['collection_name'] == "pre_conflict_memory"


class TestFactoryFunction:
    """Tests for the factory function."""
    
    def setup_method(self):
        """Clear singleton before each test."""
        clear_qdrant_service_cache()
    
    def teardown_method(self):
        """Clear singleton after each test."""
        clear_qdrant_service_cache()
    
    def test_returns_qdrant_service(self):
        """Test factory returns QdrantService instance."""
        service = get_qdrant_service()
        
        assert isinstance(service, QdrantService)
    
    def test_returns_same_instance(self):
        """Test factory returns same singleton instance."""
        service1 = get_qdrant_service()
        service2 = get_qdrant_service()
        
        assert service1 is service2
    
    def test_clear_cache_creates_new_instance(self):
        """Test clearing cache allows new instance creation."""
        service1 = get_qdrant_service()
        clear_qdrant_service_cache()
        service2 = get_qdrant_service()
        
        assert service1 is not service2


class TestDeleteConflict:
    """Tests for conflict deletion."""
    
    @patch(QDRANT_CLIENT_PATH)
    def test_delete_conflict(self, mock_client_class):
        """Test deleting a conflict."""
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        mock_client_class.return_value = mock_client
        
        service = QdrantService()
        result = service.delete_conflict("conflict-to-delete")
        
        assert result is True
        mock_client.delete.assert_called_once()


class TestGetConflictById:
    """Tests for getting conflict by ID."""
    
    @patch(QDRANT_CLIENT_PATH)
    def test_get_existing_conflict(self, mock_client_class):
        """Test getting an existing conflict."""
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        
        # Mock retrieve result
        mock_point = MagicMock()
        mock_point.id = "existing-conflict"
        mock_point.payload = {
            "conflict_type": "platform_conflict",
            "severity": "high",
            "station": "Test Station",
            "time_of_day": "morning_peak",
            "description": "Test",
        }
        mock_client.retrieve.return_value = [mock_point]
        mock_client_class.return_value = mock_client
        
        service = QdrantService()
        result = service.get_conflict_by_id("existing-conflict")
        
        assert result is not None
        assert isinstance(result, SimilarConflict)
        assert result.id == "existing-conflict"
    
    @patch(QDRANT_CLIENT_PATH)
    def test_get_nonexistent_conflict(self, mock_client_class):
        """Test getting a non-existent conflict returns None."""
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        mock_client.retrieve.return_value = []
        mock_client_class.return_value = mock_client
        
        service = QdrantService()
        result = service.get_conflict_by_id("nonexistent")
        
        assert result is None


class TestCollectionStats:
    """Tests for collection statistics."""
    
    @patch(QDRANT_CLIENT_PATH)
    def test_get_collection_stats(self, mock_client_class):
        """Test getting collection statistics."""
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])
        
        # Mock collection info
        mock_info = MagicMock()
        mock_info.vectors_count = 100
        mock_info.points_count = 100
        mock_info.status = MagicMock(value="green")
        mock_client.get_collection.return_value = mock_info
        mock_client_class.return_value = mock_client
        
        service = QdrantService()
        stats = service.get_collection_stats()
        
        assert "conflict_memory" in stats
        assert "pre_conflict_memory" in stats
        assert stats["conflict_memory"]["vectors_count"] == 100
