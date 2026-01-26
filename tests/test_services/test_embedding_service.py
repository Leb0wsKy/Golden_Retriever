"""
Unit tests for the embedding service.

Tests cover:
- Model loading and caching
- Single and batch text embedding
- Conflict object to text conversion
- Conflict embedding generation
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from app.services.embedding_service import (
    EmbeddingService,
    get_embedding_service,
    clear_model_cache,
    _get_cached_model,
    _model_cache,
)
from app.core.constants import (
    ConflictType,
    ConflictSeverity,
    TimeOfDay,
    ResolutionStrategy,
    ResolutionOutcome,
)

# Patch target for SentenceTransformer (imported inside _get_cached_model)
SENTENCE_TRANSFORMER_PATH = 'sentence_transformers.SentenceTransformer'


class TestModelCaching:
    """Tests for model loading and caching behavior."""
    
    def setup_method(self):
        """Clear cache before each test."""
        clear_model_cache()
    
    def teardown_method(self):
        """Clear cache after each test."""
        clear_model_cache()
    
    @patch(SENTENCE_TRANSFORMER_PATH)
    def test_model_loaded_once_for_same_name(self, mock_transformer):
        """Test that the same model is only loaded once."""
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model
        
        # Create two services with same model name
        service1 = EmbeddingService(model_name="test-model")
        service2 = EmbeddingService(model_name="test-model")
        
        # Access model on both
        _ = service1.model
        _ = service2.model
        
        # Model should only be loaded once
        assert mock_transformer.call_count == 1
    
    @patch(SENTENCE_TRANSFORMER_PATH)
    def test_different_models_loaded_separately(self, mock_transformer):
        """Test that different model names load separate models."""
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model
        
        service1 = EmbeddingService(model_name="model-a")
        service2 = EmbeddingService(model_name="model-b")
        
        _ = service1.model
        _ = service2.model
        
        # Each model should be loaded separately
        assert mock_transformer.call_count == 2
    
    @patch(SENTENCE_TRANSFORMER_PATH)
    def test_clear_cache_allows_reload(self, mock_transformer):
        """Test that clearing cache allows model to be reloaded."""
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model
        
        service = EmbeddingService(model_name="test-model")
        _ = service.model
        
        clear_model_cache()
        
        # Need new service instance after cache clear
        service2 = EmbeddingService(model_name="test-model")
        _ = service2.model
        
        # Model should be loaded twice
        assert mock_transformer.call_count == 2
    
    @patch(SENTENCE_TRANSFORMER_PATH)
    def test_lazy_loading(self, mock_transformer):
        """Test that model is not loaded until first use."""
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model
        
        service = EmbeddingService(model_name="test-model")
        
        # Model not loaded yet
        assert mock_transformer.call_count == 0
        
        # Access model property
        _ = service.model
        
        # Now it's loaded
        assert mock_transformer.call_count == 1


class TestSingleEmbedding:
    """Tests for single text embedding."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a service with mocked model."""
        clear_model_cache()
        with patch(SENTENCE_TRANSFORMER_PATH) as mock:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([0.1, 0.2, 0.3] * 128)  # 384 dims
            mock.return_value = mock_model
            service = EmbeddingService(model_name="test-model")
            yield service
        clear_model_cache()
    
    def test_embed_returns_list(self, mock_service):
        """Test that embed() returns a list of floats."""
        result = mock_service.embed("test text")
        
        assert isinstance(result, list)
        assert all(isinstance(x, float) for x in result)
    
    def test_embed_correct_dimension(self, mock_service):
        """Test that embedding has correct dimension."""
        result = mock_service.embed("test text")
        
        assert len(result) == 384
    
    def test_embed_calls_model_encode(self, mock_service):
        """Test that embed() calls the model's encode method."""
        mock_service.embed("test text")
        
        mock_service.model.encode.assert_called_once()
        call_args = mock_service.model.encode.call_args
        assert call_args[0][0] == "test text"
        assert call_args[1]['normalize_embeddings'] is True


class TestBatchEmbedding:
    """Tests for batch text embedding."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a service with mocked model."""
        clear_model_cache()
        with patch(SENTENCE_TRANSFORMER_PATH) as mock:
            mock_model = MagicMock()
            # Return 3 embeddings for batch
            mock_model.encode.return_value = np.array([
                [0.1] * 384,
                [0.2] * 384,
                [0.3] * 384,
            ])
            mock.return_value = mock_model
            service = EmbeddingService(model_name="test-model")
            yield service
        clear_model_cache()
    
    def test_embed_batch_returns_list_of_lists(self, mock_service):
        """Test that embed_batch() returns a list of embedding lists."""
        texts = ["text 1", "text 2", "text 3"]
        result = mock_service.embed_batch(texts)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(emb, list) for emb in result)
    
    def test_embed_batch_empty_input(self, mock_service):
        """Test that embed_batch() handles empty input."""
        result = mock_service.embed_batch([])
        
        assert result == []
    
    def test_embed_batch_uses_batch_size(self, mock_service):
        """Test that embed_batch() passes batch_size to encode."""
        texts = ["text 1", "text 2"]
        mock_service.embed_batch(texts, batch_size=16)
        
        call_args = mock_service.model.encode.call_args
        assert call_args[1]['batch_size'] == 16


class TestConflictToText:
    """Tests for conflict object to text conversion."""
    
    @pytest.fixture
    def service(self):
        """Create a service without loading the actual model."""
        clear_model_cache()
        with patch(SENTENCE_TRANSFORMER_PATH):
            service = EmbeddingService(model_name="test-model")
            yield service
        clear_model_cache()
    
    def test_basic_conflict_dict(self, service):
        """Test conversion of basic conflict dictionary."""
        conflict = {
            "conflict_type": "platform_conflict",
            "severity": "high",
            "station": "King's Cross",
            "time_of_day": "morning_peak",
            "description": "Platform 3 double-booked",
            "affected_trains": ["IC101", "RE205"],
            "delay_before": 15,
        }
        
        text = service.conflict_to_text(conflict)
        
        assert "platform conflict" in text.lower()
        assert "high" in text.lower()
        assert "King's Cross" in text
        assert "morning peak" in text.lower()
        assert "Platform 3 double-booked" in text
        assert "IC101" in text
        assert "RE205" in text
        assert "15 minutes" in text
    
    def test_conflict_with_platform(self, service):
        """Test that platform info is included."""
        conflict = {
            "conflict_type": "platform_conflict",
            "severity": "medium",
            "station": "Paddington",
            "time_of_day": "off_peak",
            "description": "Conflict",
            "platform": "5",
        }
        
        text = service.conflict_to_text(conflict)
        
        assert "platform 5" in text.lower()
    
    def test_conflict_with_track_section(self, service):
        """Test that track section info is included."""
        conflict = {
            "conflict_type": "track_blockage",
            "severity": "critical",
            "station": "Euston",
            "time_of_day": "evening_peak",
            "description": "Track obstruction",
            "track_section": "Main Line North",
        }
        
        text = service.conflict_to_text(conflict)
        
        assert "Main Line North" in text
    
    def test_conflict_with_resolution(self, service):
        """Test that resolution info is included when present."""
        conflict = {
            "conflict_type": "headway_conflict",
            "severity": "medium",
            "station": "Waterloo",
            "time_of_day": "morning_peak",
            "description": "Insufficient spacing",
            "recommended_resolution": {
                "strategy": "speed_adjustment",
                "confidence": 0.85,
            },
        }
        
        text = service.conflict_to_text(conflict)
        
        assert "speed adjustment" in text.lower()
        assert "85%" in text
    
    def test_conflict_with_outcome(self, service):
        """Test that outcome info is included when present."""
        conflict = {
            "conflict_type": "capacity_overload",
            "severity": "high",
            "station": "Victoria",
            "time_of_day": "evening_peak",
            "description": "Station overcrowded",
            "final_outcome": {
                "outcome": "success",
                "actual_delay": 5,
            },
        }
        
        text = service.conflict_to_text(conflict)
        
        assert "success" in text.lower()
        assert "5 minute delay" in text
    
    def test_limits_train_list(self, service):
        """Test that long train lists are truncated."""
        conflict = {
            "conflict_type": "platform_conflict",
            "severity": "high",
            "station": "Central",
            "time_of_day": "morning_peak",
            "description": "Many trains affected",
            "affected_trains": [f"TR{i}" for i in range(10)],  # 10 trains
        }
        
        text = service.conflict_to_text(conflict)
        
        # Should show first 5 and indicate more
        assert "TR0" in text
        assert "TR4" in text
        assert "5 more" in text
    
    def test_handles_pydantic_model(self, service):
        """Test conversion of Pydantic model objects."""
        from app.models.conflict import ConflictBase
        
        conflict = ConflictBase(
            conflict_type=ConflictType.PLATFORM_CONFLICT,
            severity=ConflictSeverity.HIGH,
            station="King's Cross",
            time_of_day=TimeOfDay.MORNING_PEAK,
            affected_trains=["IC101"],
            description="Test conflict description",
        )
        
        text = service.conflict_to_text(conflict)
        
        assert "platform conflict" in text.lower()
        assert "King's Cross" in text


class TestConflictEmbedding:
    """Tests for conflict object embedding."""
    
    @pytest.fixture
    def mock_service(self):
        """Create a service with mocked model."""
        clear_model_cache()
        with patch(SENTENCE_TRANSFORMER_PATH) as mock:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([0.5] * 384)
            mock.return_value = mock_model
            service = EmbeddingService(model_name="test-model")
            yield service
        clear_model_cache()
    
    def test_embed_conflict_returns_list(self, mock_service):
        """Test that embed_conflict() returns a list of floats."""
        conflict = {
            "conflict_type": "platform_conflict",
            "severity": "high",
            "station": "Test Station",
            "time_of_day": "morning_peak",
            "description": "Test description",
        }
        
        result = mock_service.embed_conflict(conflict)
        
        assert isinstance(result, list)
        assert len(result) == 384
    
    def test_embed_conflicts_batch(self, mock_service):
        """Test that embed_conflicts() processes multiple conflicts."""
        mock_service.model.encode.return_value = np.array([
            [0.1] * 384,
            [0.2] * 384,
        ])
        
        conflicts = [
            {"conflict_type": "platform_conflict", "severity": "high", 
             "station": "A", "time_of_day": "morning_peak", "description": "Conflict A"},
            {"conflict_type": "headway_conflict", "severity": "medium",
             "station": "B", "time_of_day": "off_peak", "description": "Conflict B"},
        ]
        
        result = mock_service.embed_conflicts(conflicts)
        
        assert len(result) == 2
        assert all(len(emb) == 384 for emb in result)


class TestFactoryFunction:
    """Tests for the get_embedding_service factory function."""
    
    def setup_method(self):
        """Clear caches before each test."""
        clear_model_cache()
        get_embedding_service.cache_clear()
    
    def teardown_method(self):
        """Clear caches after each test."""
        clear_model_cache()
        get_embedding_service.cache_clear()
    
    @patch(SENTENCE_TRANSFORMER_PATH)
    def test_returns_embedding_service(self, mock_transformer):
        """Test that factory returns EmbeddingService instance."""
        mock_transformer.return_value = MagicMock()
        
        service = get_embedding_service()
        
        assert isinstance(service, EmbeddingService)
    
    @patch(SENTENCE_TRANSFORMER_PATH)
    def test_returns_same_instance(self, mock_transformer):
        """Test that factory returns the same cached instance."""
        mock_transformer.return_value = MagicMock()
        
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        
        assert service1 is service2


class TestDimensionProperty:
    """Tests for the dimension property."""
    
    def test_dimension_from_settings(self):
        """Test that dimension comes from settings."""
        clear_model_cache()
        with patch(SENTENCE_TRANSFORMER_PATH):
            service = EmbeddingService(model_name="test-model")
            
            # Should match settings.EMBEDDING_DIMENSION
            from app.core.config import settings
            assert service.dimension == settings.EMBEDDING_DIMENSION
        clear_model_cache()


class TestIntegration:
    """Integration tests with actual model (skipped by default)."""
    
    @pytest.mark.skip(reason="Requires model download, run manually")
    def test_real_embedding_generation(self):
        """Test actual embedding generation with real model."""
        clear_model_cache()
        
        service = EmbeddingService()  # Uses default model
        
        text = "Platform conflict at King's Cross station during morning peak"
        embedding = service.embed(text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
        
        clear_model_cache()
    
    @pytest.mark.skip(reason="Requires model download, run manually")
    def test_similar_texts_have_similar_embeddings(self):
        """Test that semantically similar texts produce similar embeddings."""
        clear_model_cache()
        
        service = EmbeddingService()
        
        text1 = "Platform conflict at King's Cross"
        text2 = "Platform dispute at King's Cross station"  # Similar
        text3 = "Track blockage on the northern line"  # Different
        
        emb1 = np.array(service.embed(text1))
        emb2 = np.array(service.embed(text2))
        emb3 = np.array(service.embed(text3))
        
        # Cosine similarity
        sim_12 = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        sim_13 = np.dot(emb1, emb3) / (np.linalg.norm(emb1) * np.linalg.norm(emb3))
        
        # Similar texts should have higher similarity
        assert sim_12 > sim_13
        
        clear_model_cache()
