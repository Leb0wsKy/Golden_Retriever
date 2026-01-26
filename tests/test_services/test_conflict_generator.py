"""
Tests for the conflict generator service.

Tests deterministic generation using random seeds and validates
all generated conflict attributes.
"""

import pytest
from datetime import datetime

from app.services.conflict_generator import ConflictGenerator, GeneratorConfig
from app.models.conflict import GeneratedConflict, RecommendedResolution, FinalOutcome
from app.core.constants import (
    ConflictType,
    ConflictSeverity,
    TimeOfDay,
    ResolutionStrategy,
    ResolutionOutcome,
)


class TestConflictGeneratorBasics:
    """Basic functionality tests for ConflictGenerator."""
    
    @pytest.fixture
    def generator(self) -> ConflictGenerator:
        """Create a seeded generator for reproducible tests."""
        return ConflictGenerator(seed=42)
    
    def test_generate_single_conflict(self, generator: ConflictGenerator):
        """Test generating a single conflict returns correct type."""
        conflicts = generator.generate(count=1)
        
        assert len(conflicts) == 1
        assert isinstance(conflicts[0], GeneratedConflict)
    
    def test_generate_multiple_conflicts(self, generator: ConflictGenerator):
        """Test generating multiple conflicts."""
        count = 10
        conflicts = generator.generate(count=count)
        
        assert len(conflicts) == count
        assert all(isinstance(c, GeneratedConflict) for c in conflicts)
    
    def test_conflict_has_required_fields(self, generator: ConflictGenerator):
        """Test that generated conflicts have all required fields."""
        conflict = generator.generate(count=1)[0]
        
        # Check required fields exist and have correct types
        assert isinstance(conflict.id, str)
        assert conflict.id.startswith("conflict-")
        assert isinstance(conflict.conflict_type, ConflictType)
        assert isinstance(conflict.severity, ConflictSeverity)
        assert isinstance(conflict.station, str)
        assert isinstance(conflict.time_of_day, TimeOfDay)
        assert isinstance(conflict.affected_trains, list)
        assert len(conflict.affected_trains) >= 1
        assert isinstance(conflict.delay_before, int)
        assert isinstance(conflict.description, str)
        assert len(conflict.description) >= 10
        assert isinstance(conflict.detected_at, datetime)
        assert isinstance(conflict.recommended_resolution, RecommendedResolution)
        assert isinstance(conflict.final_outcome, FinalOutcome)
    
    def test_unique_conflict_ids(self, generator: ConflictGenerator):
        """Test that all generated conflicts have unique IDs."""
        conflicts = generator.generate(count=100)
        ids = [c.id for c in conflicts]
        
        assert len(ids) == len(set(ids)), "Conflict IDs should be unique"


class TestDeterministicGeneration:
    """Tests for deterministic generation using random seeds."""
    
    def test_same_seed_produces_same_results(self):
        """Test that same seed produces identical conflicts."""
        gen1 = ConflictGenerator(seed=12345)
        gen2 = ConflictGenerator(seed=12345)
        
        conflicts1 = gen1.generate(count=5)
        conflicts2 = gen2.generate(count=5)
        
        for c1, c2 in zip(conflicts1, conflicts2):
            assert c1.conflict_type == c2.conflict_type
            assert c1.station == c2.station
            assert c1.severity == c2.severity
            assert c1.time_of_day == c2.time_of_day
            assert c1.affected_trains == c2.affected_trains
            assert c1.delay_before == c2.delay_before
            assert c1.recommended_resolution.strategy == c2.recommended_resolution.strategy
            assert c1.final_outcome.outcome == c2.final_outcome.outcome
    
    def test_different_seeds_produce_different_results(self):
        """Test that different seeds produce different conflicts."""
        gen1 = ConflictGenerator(seed=111)
        gen2 = ConflictGenerator(seed=222)
        
        conflicts1 = gen1.generate(count=10)
        conflicts2 = gen2.generate(count=10)
        
        # At least some conflicts should differ
        differences = sum(
            1 for c1, c2 in zip(conflicts1, conflicts2)
            if c1.conflict_type != c2.conflict_type or c1.station != c2.station
        )
        
        assert differences > 0, "Different seeds should produce different results"
    
    def test_reset_seed(self):
        """Test that resetting seed reproduces the same sequence."""
        generator = ConflictGenerator(seed=999)
        
        first_batch = generator.generate(count=3)
        
        generator.reset_seed(999)
        second_batch = generator.generate(count=3)
        
        for c1, c2 in zip(first_batch, second_batch):
            assert c1.conflict_type == c2.conflict_type
            assert c1.station == c2.station
            assert c1.delay_before == c2.delay_before
    
    def test_reproducible_across_calls(self):
        """Test that sequential calls with same seed are reproducible."""
        # First run
        gen1 = ConflictGenerator(seed=42)
        result1_a = gen1.generate(count=2)
        result1_b = gen1.generate(count=2)
        
        # Second run
        gen2 = ConflictGenerator(seed=42)
        result2_a = gen2.generate(count=2)
        result2_b = gen2.generate(count=2)
        
        # Results should match
        assert result1_a[0].station == result2_a[0].station
        assert result1_a[1].station == result2_a[1].station
        assert result1_b[0].station == result2_b[0].station
        assert result1_b[1].station == result2_b[1].station


class TestConflictTypes:
    """Tests for specific conflict type generation."""
    
    @pytest.fixture
    def generator(self) -> ConflictGenerator:
        return ConflictGenerator(seed=42)
    
    def test_generate_by_type_platform(self, generator: ConflictGenerator):
        """Test generating platform conflicts specifically."""
        conflicts = generator.generate_by_type(
            ConflictType.PLATFORM_CONFLICT,
            count=5
        )
        
        assert len(conflicts) == 5
        assert all(c.conflict_type == ConflictType.PLATFORM_CONFLICT for c in conflicts)
        assert all(c.platform is not None for c in conflicts)
    
    def test_generate_by_type_headway(self, generator: ConflictGenerator):
        """Test generating headway conflicts specifically."""
        conflicts = generator.generate_by_type(
            ConflictType.HEADWAY_CONFLICT,
            count=5
        )
        
        assert len(conflicts) == 5
        assert all(c.conflict_type == ConflictType.HEADWAY_CONFLICT for c in conflicts)
        assert all(c.track_section is not None for c in conflicts)
        assert all("headway" in c.description.lower() for c in conflicts)
    
    def test_generate_by_type_track_blockage(self, generator: ConflictGenerator):
        """Test generating track blockage conflicts specifically."""
        conflicts = generator.generate_by_type(
            ConflictType.TRACK_BLOCKAGE,
            count=5
        )
        
        assert len(conflicts) == 5
        assert all(c.conflict_type == ConflictType.TRACK_BLOCKAGE for c in conflicts)
        assert all(c.track_section is not None for c in conflicts)
        assert all("blockage_cause" in c.metadata for c in conflicts)
    
    def test_generate_by_type_capacity(self, generator: ConflictGenerator):
        """Test generating capacity overload conflicts specifically."""
        conflicts = generator.generate_by_type(
            ConflictType.CAPACITY_OVERLOAD,
            count=5
        )
        
        assert len(conflicts) == 5
        assert all(c.conflict_type == ConflictType.CAPACITY_OVERLOAD for c in conflicts)
        assert all("station_capacity" in c.metadata for c in conflicts)
    
    def test_all_conflict_types_generated(self, generator: ConflictGenerator):
        """Test that random generation covers all conflict types."""
        # Generate enough conflicts to likely get all types
        conflicts = generator.generate(count=100)
        types_seen = {c.conflict_type for c in conflicts}
        
        assert len(types_seen) == len(ConflictType), \
            f"Expected all {len(ConflictType)} types, got {types_seen}"


class TestConflictAttributes:
    """Tests for conflict attribute validation."""
    
    @pytest.fixture
    def generator(self) -> ConflictGenerator:
        return ConflictGenerator(seed=42)
    
    def test_severity_is_valid(self, generator: ConflictGenerator):
        """Test that all severities are valid enum values."""
        conflicts = generator.generate(count=50)
        
        for conflict in conflicts:
            assert conflict.severity in ConflictSeverity
    
    def test_time_of_day_is_valid(self, generator: ConflictGenerator):
        """Test that all time_of_day values are valid."""
        conflicts = generator.generate(count=50)
        
        for conflict in conflicts:
            assert conflict.time_of_day in TimeOfDay
    
    def test_affected_trains_not_empty(self, generator: ConflictGenerator):
        """Test that affected_trains always has at least one train."""
        conflicts = generator.generate(count=50)
        
        for conflict in conflicts:
            assert len(conflict.affected_trains) >= 1
            assert all(isinstance(t, str) for t in conflict.affected_trains)
    
    def test_delay_before_within_bounds(self, generator: ConflictGenerator):
        """Test that delay_before is within expected bounds."""
        conflicts = generator.generate(count=50)
        
        for conflict in conflicts:
            assert 0 <= conflict.delay_before <= 120
    
    def test_station_from_valid_list(self, generator: ConflictGenerator):
        """Test that stations come from the valid stations list."""
        conflicts = generator.generate(count=50)
        
        for conflict in conflicts:
            assert conflict.station in ConflictGenerator.STATIONS
    
    def test_train_ids_have_valid_format(self, generator: ConflictGenerator):
        """Test that train IDs have expected format (prefix + number)."""
        conflicts = generator.generate(count=20)
        valid_prefixes = [p[0] for p in ConflictGenerator.TRAIN_PREFIXES]
        # Sort by length descending so longer prefixes are matched first (e.g., "SE" before "S")
        valid_prefixes_sorted = sorted(valid_prefixes, key=len, reverse=True)
        
        for conflict in conflicts:
            for train_id in conflict.affected_trains:
                # Should start with a valid prefix
                has_valid_prefix = any(train_id.startswith(p) for p in valid_prefixes_sorted)
                assert has_valid_prefix, f"Invalid train ID format: {train_id}"
                
                # Should have numeric suffix - find the longest matching prefix
                matching_prefixes = [p for p in valid_prefixes_sorted if train_id.startswith(p)]
                prefix_len = len(matching_prefixes[0])  # First match is longest due to sorting
                number_part = train_id[prefix_len:]
                assert number_part.isdigit(), f"Train ID should end with numbers: {train_id}"


class TestResolutionGeneration:
    """Tests for recommended resolution generation."""
    
    @pytest.fixture
    def generator(self) -> ConflictGenerator:
        return ConflictGenerator(seed=42)
    
    def test_resolution_strategy_is_valid(self, generator: ConflictGenerator):
        """Test that resolution strategies are valid enum values."""
        conflicts = generator.generate(count=50)
        
        for conflict in conflicts:
            assert conflict.recommended_resolution.strategy in ResolutionStrategy
    
    def test_resolution_confidence_in_range(self, generator: ConflictGenerator):
        """Test that confidence scores are between 0 and 1."""
        conflicts = generator.generate(count=50)
        
        for conflict in conflicts:
            confidence = conflict.recommended_resolution.confidence
            assert 0.0 <= confidence <= 1.0
    
    def test_resolution_matches_conflict_type(self, generator: ConflictGenerator):
        """Test that resolution strategies are appropriate for conflict type."""
        for conflict_type in ConflictType:
            conflicts = generator.generate_by_type(conflict_type, count=10)
            valid_strategies = ConflictGenerator.CONFLICT_RESOLUTIONS[conflict_type]
            
            for conflict in conflicts:
                assert conflict.recommended_resolution.strategy in valid_strategies, \
                    f"Strategy {conflict.recommended_resolution.strategy} not valid for {conflict_type}"
    
    def test_resolution_has_description(self, generator: ConflictGenerator):
        """Test that resolutions have meaningful descriptions."""
        conflicts = generator.generate(count=20)
        
        for conflict in conflicts:
            desc = conflict.recommended_resolution.description
            assert isinstance(desc, str)
            assert len(desc) > 10


class TestOutcomeGeneration:
    """Tests for final outcome generation."""
    
    @pytest.fixture
    def generator(self) -> ConflictGenerator:
        return ConflictGenerator(seed=42)
    
    def test_outcome_is_valid(self, generator: ConflictGenerator):
        """Test that outcomes are valid enum values."""
        conflicts = generator.generate(count=50)
        
        for conflict in conflicts:
            assert conflict.final_outcome.outcome in ResolutionOutcome
    
    def test_outcome_actual_delay_non_negative(self, generator: ConflictGenerator):
        """Test that actual delay is never negative."""
        conflicts = generator.generate(count=50)
        
        for conflict in conflicts:
            assert conflict.final_outcome.actual_delay >= 0
    
    def test_outcome_resolution_time_positive(self, generator: ConflictGenerator):
        """Test that resolution time is positive."""
        conflicts = generator.generate(count=50)
        
        for conflict in conflicts:
            assert conflict.final_outcome.resolution_time_minutes >= 0
    
    def test_outcome_has_notes(self, generator: ConflictGenerator):
        """Test that outcomes have notes."""
        conflicts = generator.generate(count=20)
        
        for conflict in conflicts:
            assert conflict.final_outcome.notes is not None
            assert len(conflict.final_outcome.notes) > 0
    
    def test_success_rate_approximately_correct(self):
        """Test that success rate matches configuration."""
        config = GeneratorConfig(success_rate=0.8, partial_success_rate=0.1)
        generator = ConflictGenerator(seed=42, config=config)
        
        conflicts = generator.generate(count=1000)
        
        success_count = sum(
            1 for c in conflicts
            if c.final_outcome.outcome == ResolutionOutcome.SUCCESS
        )
        
        # Allow 10% tolerance
        expected_rate = 0.8
        actual_rate = success_count / len(conflicts)
        
        assert abs(actual_rate - expected_rate) < 0.1, \
            f"Success rate {actual_rate:.2f} too far from expected {expected_rate}"


class TestGeneratorConfiguration:
    """Tests for generator configuration."""
    
    def test_custom_config(self):
        """Test that custom configuration is applied."""
        config = GeneratorConfig(
            success_rate=0.5,
            partial_success_rate=0.3,
            min_confidence=0.7,
            max_confidence=0.9
        )
        generator = ConflictGenerator(seed=42, config=config)
        
        conflicts = generator.generate(count=100)
        
        # Check confidence scores are within configured range
        for conflict in conflicts:
            # Note: penalty can reduce confidence below min
            assert conflict.recommended_resolution.confidence <= 0.9
    
    def test_default_config(self):
        """Test that default configuration works correctly."""
        generator = ConflictGenerator(seed=42)
        
        assert generator.config.success_rate == 0.75
        assert generator.config.partial_success_rate == 0.15
        assert generator.config.min_confidence == 0.6
        assert generator.config.max_confidence == 0.95


class TestUtilityMethods:
    """Tests for utility methods."""
    
    @pytest.fixture
    def generator(self) -> ConflictGenerator:
        return ConflictGenerator(seed=42)
    
    def test_to_dict_list(self, generator: ConflictGenerator):
        """Test converting conflicts to dictionary list."""
        conflicts = generator.generate(count=5)
        dict_list = generator.to_dict_list(conflicts)
        
        assert len(dict_list) == 5
        assert all(isinstance(d, dict) for d in dict_list)
        assert all("conflict_type" in d for d in dict_list)
        assert all("station" in d for d in dict_list)
    
    def test_to_embedding_text(self, generator: ConflictGenerator):
        """Test generating embedding text representation."""
        conflict = generator.generate(count=1)[0]
        text = generator.to_embedding_text(conflict)
        
        assert isinstance(text, str)
        assert conflict.station in text
        assert conflict.conflict_type.value in text
        assert conflict.severity.value in text
        assert conflict.recommended_resolution.strategy.value in text
        assert conflict.final_outcome.outcome.value in text
    
    def test_to_embedding_text_includes_optional_fields(self, generator: ConflictGenerator):
        """Test that embedding text includes platform/track when present."""
        # Generate platform conflict (has platform)
        platform_conflict = generator.generate_by_type(ConflictType.PLATFORM_CONFLICT, count=1)[0]
        platform_text = generator.to_embedding_text(platform_conflict)
        assert "Platform:" in platform_text
        
        # Generate track blockage (has track_section)
        track_conflict = generator.generate_by_type(ConflictType.TRACK_BLOCKAGE, count=1)[0]
        track_text = generator.to_embedding_text(track_conflict)
        assert "Track:" in track_text
