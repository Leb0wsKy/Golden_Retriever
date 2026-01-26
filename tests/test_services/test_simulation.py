"""
Tests for the simulation service (legacy integration tests).

Note: The comprehensive unit tests are in tests/test_simulation_service.py.
These tests verify integration with other components like the conflict generator.
"""

import pytest
from app.services.simulation_service import SimulationService, SimulationResult
from app.core.constants import ResolutionStrategy, SimulationStatus
from app.models.conflict import GeneratedConflict


class TestSimulationService:
    """Test cases for SimulationService."""
    
    @pytest.fixture
    def simulation_service(self):
        """Create a simulation service instance."""
        return SimulationService(timeout=10, seed=42)
    
    def test_simulate_single_strategy(
        self,
        simulation_service: SimulationService,
        sample_conflict_dict: dict
    ):
        """Test simulating a single resolution strategy."""
        result = simulation_service.simulate(
            conflict=sample_conflict_dict,
            strategy=ResolutionStrategy.PLATFORM_CHANGE
        )
        
        assert isinstance(result, SimulationResult)
        assert result.strategy == ResolutionStrategy.PLATFORM_CHANGE
        assert result.status == SimulationStatus.COMPLETED
        # Updated to check for new metrics
        assert "delay_after" in result.metrics
        assert "delay_reduction" in result.metrics
        assert "recovery_time" in result.metrics
        assert "score" in result.metrics
    
    def test_simulate_all_strategies(
        self,
        simulation_service: SimulationService,
        sample_conflict_dict: dict
    ):
        """Test simulating all applicable strategies."""
        results = simulation_service.simulate_all(conflict=sample_conflict_dict)
        
        assert len(results) > 0
        assert all(isinstance(r, SimulationResult) for r in results)
    
    def test_simulation_result_to_dict(
        self,
        simulation_service: SimulationService,
        sample_conflict_dict: dict
    ):
        """Test SimulationResult serialization."""
        result = simulation_service.simulate(
            conflict=sample_conflict_dict,
            strategy=ResolutionStrategy.DELAY
        )
        
        result_dict = result.to_dict()
        
        assert "strategy" in result_dict
        assert "success" in result_dict
        assert "metrics" in result_dict
        assert "status" in result_dict
    
    def test_different_conflict_types(
        self,
        simulation_service: SimulationService,
        conflict_generator
    ):
        """Test simulation handles different conflict types."""
        conflicts = conflict_generator.generate(count=10)
        
        for conflict in conflicts:
            conflict_dict = conflict.model_dump()
            results = simulation_service.simulate_all(conflict=conflict_dict)
            assert len(results) > 0
