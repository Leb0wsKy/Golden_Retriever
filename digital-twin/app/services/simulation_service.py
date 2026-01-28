"""
Rule-Based Digital Twin Simulator for Rail Conflict Resolution.

This module implements a deterministic, rule-based simulation engine that predicts
the outcomes of applying different resolution strategies to rail conflicts.

Design Philosophy:
-----------------
1. **Rule-Based**: Uses explicit domain rules rather than ML models, making
   behavior transparent and debuggable. Each rule is documented with comments.

2. **Deterministic**: Given the same inputs and random seed, produces identical
   outputs. Essential for reproducibility and testing.

3. **Pluggable Architecture**: Designed to be easily replaced with a more
   sophisticated simulator (e.g., microscopic rail simulation) without
   changing the API contract.

4. **Scoring System**: Computes a composite score for ranking resolution
   candidates, considering delay reduction, recovery time, and side effects.

Key Metrics:
-----------
- delay_after: Predicted delay in minutes after applying the resolution
- delay_reduction: How many minutes of delay the resolution eliminates
- recovery_time: Time in minutes until normal operations resume
- score: Composite score (0-100) for ranking resolutions

Usage:
------
    >>> simulator = DigitalTwinSimulator(seed=42)
    >>> result = simulator.simulate(conflict, resolution)
    >>> print(f"Score: {result.score}, Delay reduction: {result.delay_reduction}min")

Future Replacement:
------------------
To replace with a real simulator:
1. Create a new class implementing the same interface (simulate method)
2. Return SimulationOutcome with the same fields
3. Update the factory function to return the new implementation
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Union, TYPE_CHECKING
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import random
import logging

from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.constants import (
    ConflictType,
    ConflictSeverity,
    TimeOfDay,
    ResolutionStrategy,
    SimulationStatus,
    MAX_SIMULATION_ITERATIONS
)
from app.core.exceptions import SimulationError, SimulationTimeoutError

if TYPE_CHECKING:
    from app.models.conflict import GeneratedConflict, ConflictBase

logger = logging.getLogger(__name__)


# =============================================================================
# Simulation Models
# =============================================================================

class SimulationOutcome(BaseModel):
    """
    Outcome of simulating a resolution strategy.
    
    This is the main output of the digital twin simulator, containing
    all predicted metrics and a composite score for ranking.
    
    Attributes:
        strategy: The resolution strategy that was simulated.
        success: Whether the resolution is predicted to succeed.
        delay_after: Predicted delay in minutes after resolution.
        delay_reduction: Minutes of delay eliminated by this resolution.
        recovery_time: Minutes until normal operations resume.
        score: Composite score (0-100) for ranking. Higher is better.
        confidence: Confidence in the prediction (0-1).
        side_effects: Dictionary of predicted side effects.
        explanation: Human-readable explanation of the simulation.
    """
    strategy: ResolutionStrategy = Field(..., description="Resolution strategy simulated")
    success: bool = Field(..., description="Whether resolution is predicted to succeed")
    
    # Core metrics
    delay_after: int = Field(..., ge=0, description="Predicted delay after resolution (minutes)")
    delay_reduction: int = Field(..., ge=0, description="Delay reduction achieved (minutes)")
    recovery_time: int = Field(..., ge=0, description="Time to normal operations (minutes)")
    
    # Scoring
    score: float = Field(..., ge=0, le=100, description="Composite ranking score (0-100)")
    confidence: float = Field(default=0.8, ge=0, le=1, description="Prediction confidence")
    
    # Additional details
    side_effects: Dict[str, Any] = Field(default_factory=dict, description="Predicted side effects")
    explanation: str = Field(default="", description="Human-readable explanation")
    
    # Simulation metadata
    simulation_time_ms: Optional[float] = Field(default=None, description="Simulation duration")
    status: SimulationStatus = Field(default=SimulationStatus.COMPLETED)


class ResolutionCandidate(BaseModel):
    """
    A candidate resolution to simulate.
    
    Attributes:
        strategy: The resolution strategy to apply.
        parameters: Strategy-specific parameters.
        priority: Priority level for this candidate.
    """
    strategy: ResolutionStrategy = Field(..., description="Resolution strategy")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    priority: int = Field(default=0, ge=0, description="Priority level")


class SimulationInput(BaseModel):
    """
    Input for the digital twin simulator.
    
    Encapsulates all information needed to run a simulation.
    
    Attributes:
        conflict_type: Type of the conflict.
        severity: Severity level.
        station: Station where conflict occurs.
        time_of_day: Time period of the conflict.
        affected_trains: Number of affected trains.
        delay_before: Current delay in minutes.
        platform: Platform number if applicable.
        track_section: Track section if applicable.
        metadata: Additional context.
    """
    conflict_type: ConflictType = Field(..., description="Type of conflict")
    severity: ConflictSeverity = Field(default=ConflictSeverity.MEDIUM)
    station: str = Field(default="Unknown")
    time_of_day: TimeOfDay = Field(default=TimeOfDay.MIDDAY)
    affected_trains: int = Field(default=2, ge=1, description="Number of affected trains")
    delay_before: int = Field(default=0, ge=0, description="Current delay in minutes")
    platform: Optional[str] = Field(default=None)
    track_section: Optional[str] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Rule Constants
# =============================================================================

# -----------------------------------------------------------------------------
# Base effectiveness of each strategy for each conflict type (0-1 scale).
# These values are derived from domain expertise and historical patterns.
# Higher values indicate better expected outcomes for the strategy-conflict pair.
# -----------------------------------------------------------------------------
STRATEGY_EFFECTIVENESS = {
    ConflictType.PLATFORM_CONFLICT: {
        # Platform change is the natural solution for platform conflicts
        ResolutionStrategy.PLATFORM_CHANGE: 0.90,
        # Reordering can help by changing which train uses the platform first
        ResolutionStrategy.REORDER: 0.75,
        # Delays can work but cascade effects are common
        ResolutionStrategy.DELAY: 0.60,
        # Rerouting is overkill for platform conflicts
        ResolutionStrategy.REROUTE: 0.40,
        # Speed adjustment has limited impact on platform allocation
        ResolutionStrategy.SPEED_ADJUSTMENT: 0.30,
        # Hold can help staging trains
        ResolutionStrategy.HOLD: 0.55,
        # Cancellation always works but has high cost
        ResolutionStrategy.CANCELLATION: 0.95,
    },
    ConflictType.HEADWAY_CONFLICT: {
        # Speed adjustment is ideal for headway management
        ResolutionStrategy.SPEED_ADJUSTMENT: 0.85,
        # Holding trains increases spacing effectively
        ResolutionStrategy.HOLD: 0.80,
        # Reordering can resolve priority-based headway issues
        ResolutionStrategy.REORDER: 0.70,
        # Delays work but can cause cascades
        ResolutionStrategy.DELAY: 0.65,
        # Rerouting is effective but expensive
        ResolutionStrategy.REROUTE: 0.60,
        # Platform change has minimal effect on headway
        ResolutionStrategy.PLATFORM_CHANGE: 0.30,
        ResolutionStrategy.CANCELLATION: 0.95,
    },
    ConflictType.TRACK_BLOCKAGE: {
        # Rerouting is the primary solution for blocked tracks
        ResolutionStrategy.REROUTE: 0.85,
        # Delays wait out the blockage
        ResolutionStrategy.DELAY: 0.60,
        # Reordering helps optimize the queue
        ResolutionStrategy.REORDER: 0.55,
        # Holding prevents trains from entering blocked section
        ResolutionStrategy.HOLD: 0.50,
        # Speed adjustment has limited impact on blockages
        ResolutionStrategy.SPEED_ADJUSTMENT: 0.35,
        # Platform change only helps if blockage is near station
        ResolutionStrategy.PLATFORM_CHANGE: 0.25,
        ResolutionStrategy.CANCELLATION: 0.95,
    },
    ConflictType.CAPACITY_OVERLOAD: {
        # Delays spread out the load over time
        ResolutionStrategy.DELAY: 0.75,
        # Rerouting diverts traffic to less congested routes
        ResolutionStrategy.REROUTE: 0.70,
        # Reordering optimizes throughput
        ResolutionStrategy.REORDER: 0.65,
        # Cancellation removes load from the system
        ResolutionStrategy.CANCELLATION: 0.90,
        # Speed adjustment can help regulate flow
        ResolutionStrategy.SPEED_ADJUSTMENT: 0.55,
        # Holding can help but may worsen congestion
        ResolutionStrategy.HOLD: 0.45,
        # Platform change has limited effect on capacity
        ResolutionStrategy.PLATFORM_CHANGE: 0.30,
    },
    # New conflict types with optimized strategies
    ConflictType.SIGNAL_FAILURE: {
        # Reroute around failed signal
        ResolutionStrategy.REROUTE: 0.80,
        # Hold trains until repair
        ResolutionStrategy.HOLD: 0.70,
        # Delay while fixing
        ResolutionStrategy.DELAY: 0.65,
        # Speed reduction for manual operation
        ResolutionStrategy.SPEED_ADJUSTMENT: 0.60,
        # Reorder to minimize impact
        ResolutionStrategy.REORDER: 0.50,
        # Cancellation if severe
        ResolutionStrategy.CANCELLATION: 0.85,
        ResolutionStrategy.PLATFORM_CHANGE: 0.25,
    },
    ConflictType.CREW_SHORTAGE: {
        # Cancel service without crew
        ResolutionStrategy.CANCELLATION: 0.90,
        # Delay until crew available
        ResolutionStrategy.DELAY: 0.75,
        # Reorder to use available crews efficiently
        ResolutionStrategy.REORDER: 0.70,
        # Reroute to crew availability
        ResolutionStrategy.REROUTE: 0.50,
        # Other strategies less effective
        ResolutionStrategy.HOLD: 0.40,
        ResolutionStrategy.SPEED_ADJUSTMENT: 0.20,
        ResolutionStrategy.PLATFORM_CHANGE: 0.15,
    },
    ConflictType.ROLLING_STOCK_FAILURE: {
        # Cancellation if no spare stock
        ResolutionStrategy.CANCELLATION: 0.85,
        # Delay for repairs or replacement
        ResolutionStrategy.DELAY: 0.70,
        # Reroute to depot/maintenance
        ResolutionStrategy.REROUTE: 0.65,
        # Reorder to minimize disruption
        ResolutionStrategy.REORDER: 0.55,
        # Hold at safe location
        ResolutionStrategy.HOLD: 0.50,
        # Speed reduction if partial failure
        ResolutionStrategy.SPEED_ADJUSTMENT: 0.45,
        ResolutionStrategy.PLATFORM_CHANGE: 0.20,
    },
    ConflictType.WEATHER_DISRUPTION: {
        # Speed reduction for safety
        ResolutionStrategy.SPEED_ADJUSTMENT: 0.85,
        # Delay until conditions improve
        ResolutionStrategy.DELAY: 0.75,
        # Reroute around affected area
        ResolutionStrategy.REROUTE: 0.70,
        # Hold services if severe
        ResolutionStrategy.HOLD: 0.65,
        # Cancel if dangerous
        ResolutionStrategy.CANCELLATION: 0.80,
        # Reorder based on route exposure
        ResolutionStrategy.REORDER: 0.55,
        ResolutionStrategy.PLATFORM_CHANGE: 0.30,
    },
    ConflictType.TIMETABLE_CONFLICT: {
        # Reorder services to fix schedule
        ResolutionStrategy.REORDER: 0.85,
        # Delay to create gaps
        ResolutionStrategy.DELAY: 0.75,
        # Platform change for better flow
        ResolutionStrategy.PLATFORM_CHANGE: 0.70,
        # Speed adjustment to catch up
        ResolutionStrategy.SPEED_ADJUSTMENT: 0.65,
        # Reroute if conflicts persist
        ResolutionStrategy.REROUTE: 0.55,
        # Hold to reset timing
        ResolutionStrategy.HOLD: 0.50,
        # Cancellation as last resort
        ResolutionStrategy.CANCELLATION: 0.75,
    },
    ConflictType.PASSENGER_INCIDENT: {
        # Hold while incident resolved
        ResolutionStrategy.HOLD: 0.80,
        # Delay for passenger safety
        ResolutionStrategy.DELAY: 0.75,
        # Platform change if needed
        ResolutionStrategy.PLATFORM_CHANGE: 0.65,
        # Reorder if multiple trains affected
        ResolutionStrategy.REORDER: 0.55,
        # Cancel if severe incident
        ResolutionStrategy.CANCELLATION: 0.70,
        # Speed reduction on approach
        ResolutionStrategy.SPEED_ADJUSTMENT: 0.45,
        # Reroute rarely helps
        ResolutionStrategy.REROUTE: 0.30,
    },
    ConflictType.INFRASTRUCTURE_WORK: {
        # Reroute around work zone
        ResolutionStrategy.REROUTE: 0.85,
        # Delay until work window closes
        ResolutionStrategy.DELAY: 0.70,
        # Speed reduction through work zone
        ResolutionStrategy.SPEED_ADJUSTMENT: 0.65,
        # Reorder for efficiency
        ResolutionStrategy.REORDER: 0.60,
        # Platform change if station work
        ResolutionStrategy.PLATFORM_CHANGE: 0.55,
        # Cancel if blocking
        ResolutionStrategy.CANCELLATION: 0.75,
        # Hold until clear
        ResolutionStrategy.HOLD: 0.50,
    },
    ConflictType.POWER_OUTAGE: {
        # Delay until power restored
        ResolutionStrategy.DELAY: 0.80,
        # Reroute to powered sections
        ResolutionStrategy.REROUTE: 0.75,
        # Cancel electric services
        ResolutionStrategy.CANCELLATION: 0.85,
        # Hold at safe location
        ResolutionStrategy.HOLD: 0.70,
        # Reorder based on power availability
        ResolutionStrategy.REORDER: 0.60,
        # Speed reduction rarely helps
        ResolutionStrategy.SPEED_ADJUSTMENT: 0.30,
        ResolutionStrategy.PLATFORM_CHANGE: 0.25,
    },
    ConflictType.LEVEL_CROSSING_INCIDENT: {
        # Hold trains approaching crossing
        ResolutionStrategy.HOLD: 0.85,
        # Delay until cleared
        ResolutionStrategy.DELAY: 0.75,
        # Speed reduction on approach
        ResolutionStrategy.SPEED_ADJUSTMENT: 0.70,
        # Reroute if alternative exists
        ResolutionStrategy.REROUTE: 0.60,
        # Reorder based on distance
        ResolutionStrategy.REORDER: 0.50,
        # Cancel if severe
        ResolutionStrategy.CANCELLATION: 0.65,
        # Platform change not applicable
        ResolutionStrategy.PLATFORM_CHANGE: 0.15,
    },
}

# -----------------------------------------------------------------------------
# Severity multipliers affect how much delay is added/removed.
# Higher severity = harder to resolve, more residual delay.
# -----------------------------------------------------------------------------
SEVERITY_MULTIPLIERS = {
    ConflictSeverity.LOW: 0.5,       # Easy to resolve, minimal residual delay
    ConflictSeverity.MEDIUM: 1.0,    # Baseline difficulty
    ConflictSeverity.HIGH: 1.5,      # Harder to resolve, more residual delay
    ConflictSeverity.CRITICAL: 2.0,  # Very difficult, significant residual delay
}

# -----------------------------------------------------------------------------
# Time-of-day impacts simulation outcomes.
# Peak hours have more network pressure, making resolution harder.
# -----------------------------------------------------------------------------
TIME_OF_DAY_FACTORS = {
    TimeOfDay.EARLY_MORNING: 0.8,    # Low traffic, easy recovery
    TimeOfDay.MORNING_PEAK: 1.4,     # High traffic, cascade risk
    TimeOfDay.MIDDAY: 1.0,           # Moderate traffic, baseline
    TimeOfDay.EVENING_PEAK: 1.5,     # Highest traffic, hardest recovery
    TimeOfDay.EVENING: 1.1,          # Moderate-high traffic
    TimeOfDay.NIGHT: 0.6,            # Very low traffic, easy recovery
}

# -----------------------------------------------------------------------------
# Base recovery times (minutes) for each strategy.
# Time from resolution decision to normal operations.
# -----------------------------------------------------------------------------
BASE_RECOVERY_TIMES = {
    ResolutionStrategy.PLATFORM_CHANGE: 8,    # Quick platform reassignment
    ResolutionStrategy.REORDER: 12,           # Need to communicate new priorities
    ResolutionStrategy.DELAY: 15,             # Delay propagation takes time
    ResolutionStrategy.REROUTE: 20,           # Route changes need coordination
    ResolutionStrategy.SPEED_ADJUSTMENT: 10,  # Quick to implement
    ResolutionStrategy.HOLD: 10,              # Simple to execute
    ResolutionStrategy.CANCELLATION: 25,      # Passenger handling takes time
}


# =============================================================================
# Digital Twin Simulator
# =============================================================================

class DigitalTwinSimulator:
    """
    Rule-based digital twin simulator for rail conflict resolution.
    
    This simulator uses domain rules to predict the outcome of applying
    resolution strategies to rail conflicts. It is designed to be:
    
    1. **Deterministic**: Same inputs + seed = same outputs
    2. **Transparent**: All rules are documented with inline comments
    3. **Replaceable**: Easy to swap with a real simulator
    
    The simulator computes three key metrics:
    - delay_after: Remaining delay after resolution
    - delay_reduction: How much delay was eliminated
    - recovery_time: Time until normal operations
    
    These are combined into a composite score for ranking resolutions.
    
    Example:
        >>> simulator = DigitalTwinSimulator(seed=42)
        >>> 
        >>> # Create simulation input from conflict
        >>> sim_input = SimulationInput(
        ...     conflict_type=ConflictType.PLATFORM_CONFLICT,
        ...     severity=ConflictSeverity.HIGH,
        ...     delay_before=15,
        ...     affected_trains=3
        ... )
        >>> 
        >>> # Simulate a resolution
        >>> candidate = ResolutionCandidate(strategy=ResolutionStrategy.PLATFORM_CHANGE)
        >>> result = simulator.simulate(sim_input, candidate)
        >>> 
        >>> print(f"Score: {result.score:.1f}")
        >>> print(f"Delay reduction: {result.delay_reduction} min")
    
    Attributes:
        seed: Random seed for deterministic simulation.
        _rng: Random number generator instance.
    """
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the digital twin simulator.
        
        Args:
            seed: Random seed for reproducibility. If None, uses system randomness.
        """
        self.seed = seed
        self._rng = random.Random(seed)
        logger.info(f"DigitalTwinSimulator initialized with seed={seed}")
    
    def reset_seed(self, seed: Optional[int] = None) -> None:
        """
        Reset the random number generator with a new seed.
        
        Useful for ensuring reproducibility within a simulation session.
        
        Args:
            seed: New seed value. If None, uses the original seed.
        """
        self.seed = seed if seed is not None else self.seed
        self._rng = random.Random(self.seed)
    
    def simulate(
        self,
        conflict: Union[SimulationInput, "GeneratedConflict", "ConflictBase", Dict[str, Any]],
        resolution: Union[ResolutionCandidate, ResolutionStrategy],
    ) -> SimulationOutcome:
        """
        Simulate applying a resolution to a conflict.
        
        This is the main entry point for the simulator. It accepts various
        input formats for flexibility and returns a typed SimulationOutcome.
        
        Args:
            conflict: The conflict to resolve. Can be:
                - SimulationInput: Explicit simulation input
                - GeneratedConflict/ConflictBase: Pydantic conflict model
                - Dict: Raw conflict data
            resolution: The resolution to simulate. Can be:
                - ResolutionCandidate: Full candidate with parameters
                - ResolutionStrategy: Just the strategy (default params)
        
        Returns:
            SimulationOutcome with predicted metrics and score.
        
        Raises:
            SimulationError: If simulation fails.
        """
        import time
        start_time = time.time()
        
        try:
            # Normalize inputs to internal format
            sim_input = self._normalize_conflict_input(conflict)
            candidate = self._normalize_resolution_input(resolution)
            
            # Run the rule-based simulation
            outcome = self._run_simulation(sim_input, candidate)
            
            # Record simulation time
            outcome.simulation_time_ms = round((time.time() - start_time) * 1000, 2)
            
            return outcome
            
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            raise SimulationError(
                f"Failed to simulate {resolution}",
                {"error": str(e)}
            )
    
    def simulate_all(
        self,
        conflict: Union[SimulationInput, "GeneratedConflict", "ConflictBase", Dict[str, Any]],
        strategies: Optional[List[ResolutionStrategy]] = None,
    ) -> List[SimulationOutcome]:
        """
        Simulate all applicable strategies and return ranked results.
        
        Args:
            conflict: The conflict to resolve.
            strategies: Optional list of strategies to try. If None, uses
                       applicable strategies based on conflict type.
        
        Returns:
            List of SimulationOutcome sorted by score (descending).
        """
        sim_input = self._normalize_conflict_input(conflict)
        
        # Get applicable strategies if not specified
        if strategies is None:
            strategies = self._get_applicable_strategies(sim_input.conflict_type)
        
        # Run simulation for each strategy
        outcomes = []
        for strategy in strategies:
            candidate = ResolutionCandidate(strategy=strategy)
            outcome = self.simulate(sim_input, candidate)
            outcomes.append(outcome)
        
        # Sort by score (descending) - higher score = better resolution
        outcomes.sort(key=lambda x: x.score, reverse=True)
        
        return outcomes
    
    def simulate_from_pydantic(
        self,
        conflict: "GeneratedConflict",
        strategy: ResolutionStrategy,
    ) -> SimulationOutcome:
        """
        Convenience method for simulating a GeneratedConflict.
        
        Args:
            conflict: A GeneratedConflict Pydantic model.
            strategy: Resolution strategy to simulate.
        
        Returns:
            SimulationOutcome with predictions.
        """
        return self.simulate(conflict, strategy)
    
    # =========================================================================
    # Core Simulation Logic
    # =========================================================================
    
    def _run_simulation(
        self,
        sim_input: SimulationInput,
        candidate: ResolutionCandidate,
    ) -> SimulationOutcome:
        """
        Execute the rule-based simulation.
        
        This method implements the core simulation logic using domain rules.
        Each step is documented with comments explaining the reasoning.
        
        Args:
            sim_input: Normalized simulation input.
            candidate: Resolution candidate to simulate.
        
        Returns:
            SimulationOutcome with all computed metrics.
        """
        strategy = candidate.strategy
        
        # =====================================================================
        # STEP 1: Calculate Base Effectiveness
        # The effectiveness determines how well this strategy addresses this
        # conflict type. It's the foundation for all other calculations.
        # =====================================================================
        
        # Look up the base effectiveness for this strategy-conflict combination
        conflict_effectiveness = STRATEGY_EFFECTIVENESS.get(
            sim_input.conflict_type,
            {s: 0.5 for s in ResolutionStrategy}  # Default to 0.5 if unknown
        )
        base_effectiveness = conflict_effectiveness.get(strategy, 0.5)
        
        # =====================================================================
        # STEP 2: Apply Severity Modifier
        # Higher severity conflicts are harder to resolve effectively.
        # The modifier reduces effectiveness for severe conflicts.
        # =====================================================================
        
        severity_mult = SEVERITY_MULTIPLIERS.get(sim_input.severity, 1.0)
        
        # Severity reduces effectiveness (inverse relationship)
        # For low severity (0.5 mult): effectiveness increases slightly
        # For critical severity (2.0 mult): effectiveness decreases
        severity_adjusted_effectiveness = base_effectiveness * (1.0 / severity_mult ** 0.3)
        # Cap at 0.95 - no strategy is perfect
        severity_adjusted_effectiveness = min(0.95, severity_adjusted_effectiveness)
        
        # =====================================================================
        # STEP 3: Apply Time-of-Day Factor
        # Peak hours have more network pressure, making resolution harder.
        # The factor affects recovery time and cascade risk.
        # =====================================================================
        
        time_factor = TIME_OF_DAY_FACTORS.get(sim_input.time_of_day, 1.0)
        
        # =====================================================================
        # STEP 4: Add Controlled Randomness
        # Small random variations simulate real-world unpredictability while
        # remaining deterministic (same seed = same result).
        # Variation range: ±10% of effectiveness
        # =====================================================================
        
        random_factor = 1.0 + self._rng.uniform(-0.1, 0.1)
        final_effectiveness = severity_adjusted_effectiveness * random_factor
        final_effectiveness = max(0.1, min(0.95, final_effectiveness))  # Clamp to [0.1, 0.95]
        
        # =====================================================================
        # STEP 5: Calculate Delay After Resolution
        # The remaining delay depends on:
        # - Initial delay (delay_before)
        # - Strategy effectiveness
        # - Number of affected trains (more trains = harder to coordinate)
        # =====================================================================
        
        # Base delay reduction is effectiveness * initial delay
        max_reduction = sim_input.delay_before * final_effectiveness
        
        # Multi-train penalty: each additional train reduces effectiveness by 5%
        # Rationale: coordinating multiple trains is exponentially harder
        train_penalty = 1.0 - (0.05 * max(0, sim_input.affected_trains - 1))
        train_penalty = max(0.5, train_penalty)  # Minimum 50% effectiveness
        
        actual_reduction = max_reduction * train_penalty
        
        # Calculate remaining delay (cannot go below 0)
        delay_after = max(0, int(sim_input.delay_before - actual_reduction))
        delay_reduction = sim_input.delay_before - delay_after
        
        # =====================================================================
        # STEP 6: Calculate Recovery Time
        # Time from resolution decision to normal operations.
        # Affected by:
        # - Base recovery time for the strategy
        # - Time of day (peak hours = longer recovery)
        # - Number of affected trains
        # =====================================================================
        
        base_recovery = BASE_RECOVERY_TIMES.get(strategy, 15)
        
        # Time factor increases recovery during peak hours
        time_adjusted_recovery = base_recovery * time_factor
        
        # Each train adds ~2 minutes to coordination time
        train_adjusted_recovery = time_adjusted_recovery + (2 * sim_input.affected_trains)
        
        # Add small random variation (±15%)
        random_recovery = train_adjusted_recovery * (1.0 + self._rng.uniform(-0.15, 0.15))
        recovery_time = max(5, int(random_recovery))  # Minimum 5 minutes
        
        # =====================================================================
        # STEP 7: Determine Success Probability
        # Resolution is considered successful if effectiveness > threshold.
        # Threshold varies by severity (higher severity = harder to succeed).
        # =====================================================================
        
        # Success threshold increases with severity
        success_threshold = 0.4 + (0.1 * (severity_mult - 0.5))
        success = final_effectiveness > success_threshold
        
        # Random failure chance (5%) to simulate unexpected issues
        if self._rng.random() < 0.05:
            success = False
        
        # =====================================================================
        # STEP 8: Calculate Side Effects
        # Each strategy has different side effects on the network.
        # These are documented and factored into the final score.
        # =====================================================================
        
        side_effects = self._calculate_side_effects(
            sim_input, candidate, final_effectiveness
        )
        
        # =====================================================================
        # STEP 9: Calculate Composite Score
        # The score combines all metrics into a single ranking value.
        # Score components:
        # - Delay reduction (40% weight): Primary objective
        # - Recovery speed (30% weight): Faster is better
        # - Side effect penalty (20% weight): Fewer side effects preferred
        # - Success bonus (10% weight): Successful resolutions score higher
        # =====================================================================
        
        score = self._calculate_score(
            delay_before=sim_input.delay_before,
            delay_after=delay_after,
            delay_reduction=delay_reduction,
            recovery_time=recovery_time,
            success=success,
            side_effects=side_effects
        )
        
        # =====================================================================
        # STEP 10: Calculate Confidence
        # Confidence in prediction based on how well we understand this scenario.
        # Lower confidence for:
        # - Unusual conflict types
        # - Extreme severity levels
        # - Many affected trains
        # =====================================================================
        
        confidence = self._calculate_confidence(sim_input, final_effectiveness)
        
        # =====================================================================
        # STEP 11: Generate Explanation
        # Human-readable explanation of the simulation results.
        # =====================================================================
        
        explanation = self._generate_explanation(
            sim_input, candidate, delay_reduction, recovery_time, success, side_effects
        )
        
        return SimulationOutcome(
            strategy=strategy,
            success=success,
            delay_after=delay_after,
            delay_reduction=delay_reduction,
            recovery_time=recovery_time,
            score=score,
            confidence=confidence,
            side_effects=side_effects,
            explanation=explanation,
            status=SimulationStatus.COMPLETED
        )
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _normalize_conflict_input(
        self,
        conflict: Union[SimulationInput, "GeneratedConflict", "ConflictBase", Dict[str, Any]]
    ) -> SimulationInput:
        """
        Convert various input formats to SimulationInput.
        
        Provides flexibility in accepting different conflict representations
        while normalizing to a consistent internal format.
        """
        if isinstance(conflict, SimulationInput):
            return conflict
        
        # Handle Pydantic models
        if hasattr(conflict, 'model_dump'):
            data = conflict.model_dump()
        elif hasattr(conflict, 'dict'):
            data = conflict.dict()
        else:
            data = dict(conflict)
        
        # Extract and convert fields
        conflict_type = data.get('conflict_type')
        if isinstance(conflict_type, str):
            try:
                conflict_type = ConflictType(conflict_type)
            except ValueError:
                conflict_type = ConflictType.TRACK_BLOCKAGE
        
        severity = data.get('severity', ConflictSeverity.MEDIUM)
        if isinstance(severity, str):
            try:
                severity = ConflictSeverity(severity)
            except ValueError:
                severity = ConflictSeverity.MEDIUM
        
        time_of_day = data.get('time_of_day', TimeOfDay.MIDDAY)
        if isinstance(time_of_day, str):
            try:
                time_of_day = TimeOfDay(time_of_day)
            except ValueError:
                time_of_day = TimeOfDay.MIDDAY
        
        # Count affected trains
        affected_trains = data.get('affected_trains', [])
        if isinstance(affected_trains, list):
            num_trains = len(affected_trains)
        else:
            num_trains = int(affected_trains) if affected_trains else 2
        
        return SimulationInput(
            conflict_type=conflict_type,
            severity=severity,
            station=data.get('station', 'Unknown'),
            time_of_day=time_of_day,
            affected_trains=max(1, num_trains),
            delay_before=data.get('delay_before', 0),
            platform=data.get('platform'),
            track_section=data.get('track_section'),
            metadata=data.get('metadata', {})
        )
    
    def _normalize_resolution_input(
        self,
        resolution: Union[ResolutionCandidate, ResolutionStrategy]
    ) -> ResolutionCandidate:
        """Convert resolution input to ResolutionCandidate."""
        if isinstance(resolution, ResolutionCandidate):
            return resolution
        
        # Assume it's a ResolutionStrategy enum
        return ResolutionCandidate(strategy=resolution)
    
    def _get_applicable_strategies(
        self,
        conflict_type: ConflictType
    ) -> List[ResolutionStrategy]:
        """
        Get strategies applicable to a conflict type.
        
        Returns strategies ordered by expected effectiveness (best first).
        """
        # Get effectiveness map for this conflict type
        effectiveness = STRATEGY_EFFECTIVENESS.get(conflict_type, {})
        
        # Sort by effectiveness (descending) and return
        sorted_strategies = sorted(
            effectiveness.keys(),
            key=lambda s: effectiveness.get(s, 0),
            reverse=True
        )
        
        return sorted_strategies
    
    def _calculate_side_effects(
        self,
        sim_input: SimulationInput,
        candidate: ResolutionCandidate,
        effectiveness: float
    ) -> Dict[str, Any]:
        """
        Calculate predicted side effects of the resolution.
        
        Each strategy has characteristic side effects that affect other
        parts of the network. These are estimated based on rules.
        """
        strategy = candidate.strategy
        side_effects = {}
        
        # =====================================================================
        # Cascade Effect: How much delay spreads to other trains
        # Higher during peak hours, lower when resolution is more effective
        # =====================================================================
        
        time_factor = TIME_OF_DAY_FACTORS.get(sim_input.time_of_day, 1.0)
        
        # Strategies with high cascade potential
        if strategy == ResolutionStrategy.DELAY:
            # Delays often cascade through the network
            cascade_base = 0.3 + (0.2 * time_factor)  # 30-50% cascade
        elif strategy == ResolutionStrategy.CANCELLATION:
            # Cancellations have moderate cascade (passengers need rebooking)
            cascade_base = 0.25
        elif strategy == ResolutionStrategy.REROUTE:
            # Rerouting can affect other trains on the new route
            cascade_base = 0.2
        else:
            # Other strategies have lower cascade effects
            cascade_base = 0.1
        
        # Higher effectiveness reduces cascade
        cascade_effect = cascade_base * (1.0 - effectiveness * 0.5)
        side_effects['cascade_probability'] = round(min(0.8, cascade_effect), 2)
        
        # =====================================================================
        # Passenger Impact: Number of passengers affected
        # Estimates based on time of day and strategy
        # =====================================================================
        
        # Base passengers per train varies by time of day
        passengers_per_train = {
            TimeOfDay.EARLY_MORNING: 50,
            TimeOfDay.MORNING_PEAK: 300,
            TimeOfDay.MIDDAY: 150,
            TimeOfDay.EVENING_PEAK: 350,
            TimeOfDay.EVENING: 200,
            TimeOfDay.NIGHT: 30,
        }.get(sim_input.time_of_day, 150)
        
        if strategy == ResolutionStrategy.CANCELLATION:
            # All passengers on cancelled service affected
            passenger_impact = passengers_per_train
        elif strategy == ResolutionStrategy.PLATFORM_CHANGE:
            # Some passengers may miss announcements
            passenger_impact = int(passengers_per_train * 0.1)
        elif strategy == ResolutionStrategy.DELAY:
            # All passengers delayed
            passenger_impact = passengers_per_train * sim_input.affected_trains
        else:
            # Minimal direct passenger impact
            passenger_impact = int(passengers_per_train * 0.05)
        
        side_effects['passenger_impact'] = passenger_impact
        
        # =====================================================================
        # Resource Requirements: Staff and equipment needed
        # =====================================================================
        
        if strategy == ResolutionStrategy.REROUTE:
            side_effects['requires_signaller'] = True
            side_effects['coordination_complexity'] = 'high'
        elif strategy == ResolutionStrategy.PLATFORM_CHANGE:
            side_effects['requires_announcements'] = True
            side_effects['coordination_complexity'] = 'medium'
        elif strategy == ResolutionStrategy.CANCELLATION:
            side_effects['requires_customer_service'] = True
            side_effects['coordination_complexity'] = 'high'
        else:
            side_effects['coordination_complexity'] = 'low'
        
        return side_effects
    
    def _calculate_score(
        self,
        delay_before: int,
        delay_after: int,
        delay_reduction: int,
        recovery_time: int,
        success: bool,
        side_effects: Dict[str, Any]
    ) -> float:
        """
        Calculate composite score for ranking resolutions.
        
        Score is on a 0-100 scale where higher is better.
        
        Components:
        - Delay reduction component (40%): More reduction = higher score
        - Recovery speed component (30%): Faster recovery = higher score
        - Side effect penalty (20%): More side effects = lower score
        - Success bonus (10%): Successful prediction = bonus points
        """
        # =====================================================================
        # Component 1: Delay Reduction (40 points max)
        # Normalized by initial delay. 100% reduction = 40 points.
        # =====================================================================
        
        if delay_before > 0:
            reduction_ratio = delay_reduction / delay_before
        else:
            reduction_ratio = 1.0  # No delay to reduce = perfect score
        
        delay_score = 40 * reduction_ratio
        
        # =====================================================================
        # Component 2: Recovery Speed (30 points max)
        # Fast recovery (< 10 min) gets full points.
        # Slow recovery (> 60 min) gets minimal points.
        # Uses logarithmic scale for smooth degradation.
        # =====================================================================
        
        if recovery_time <= 10:
            recovery_score = 30  # Full points for fast recovery
        elif recovery_time >= 60:
            recovery_score = 5   # Minimal points for slow recovery
        else:
            # Logarithmic decay between 10 and 60 minutes
            # recovery_score = 30 - 25 * log10(recovery_time/10) / log10(6)
            import math
            recovery_score = 30 - 25 * (math.log10(recovery_time / 10) / math.log10(6))
            recovery_score = max(5, recovery_score)
        
        # =====================================================================
        # Component 3: Side Effect Penalty (20 points max, starts at 20)
        # Deduct points based on severity of side effects.
        # =====================================================================
        
        side_effect_penalty = 0
        
        # Cascade probability penalty (max 8 points)
        cascade = side_effects.get('cascade_probability', 0)
        side_effect_penalty += cascade * 8
        
        # Passenger impact penalty (max 7 points)
        passengers = side_effects.get('passenger_impact', 0)
        if passengers > 500:
            side_effect_penalty += 7
        elif passengers > 200:
            side_effect_penalty += 5
        elif passengers > 50:
            side_effect_penalty += 2
        
        # Coordination complexity penalty (max 5 points)
        complexity = side_effects.get('coordination_complexity', 'low')
        complexity_penalties = {'low': 0, 'medium': 2, 'high': 5}
        side_effect_penalty += complexity_penalties.get(complexity, 0)
        
        side_effect_score = 20 - min(20, side_effect_penalty)
        
        # =====================================================================
        # Component 4: Success Bonus (10 points)
        # Successful resolutions get full bonus.
        # =====================================================================
        
        success_score = 10 if success else 0
        
        # =====================================================================
        # Combine Components
        # =====================================================================
        
        total_score = delay_score + recovery_score + side_effect_score + success_score
        
        # Ensure score is in [0, 100] range
        return round(max(0, min(100, total_score)), 1)
    
    def _calculate_confidence(
        self,
        sim_input: SimulationInput,
        effectiveness: float
    ) -> float:
        """
        Calculate confidence in the prediction.
        
        Lower confidence for unusual or extreme scenarios.
        """
        confidence = 0.85  # Base confidence
        
        # Reduce confidence for critical severity (less predictable)
        if sim_input.severity == ConflictSeverity.CRITICAL:
            confidence -= 0.15
        elif sim_input.severity == ConflictSeverity.HIGH:
            confidence -= 0.08
        
        # Reduce confidence for many affected trains (complex coordination)
        if sim_input.affected_trains > 4:
            confidence -= 0.10
        elif sim_input.affected_trains > 2:
            confidence -= 0.05
        
        # Increase confidence for high effectiveness (well-understood scenarios)
        if effectiveness > 0.8:
            confidence += 0.05
        
        return round(max(0.5, min(0.95, confidence)), 2)
    
    def _generate_explanation(
        self,
        sim_input: SimulationInput,
        candidate: ResolutionCandidate,
        delay_reduction: int,
        recovery_time: int,
        success: bool,
        side_effects: Dict[str, Any]
    ) -> str:
        """Generate human-readable explanation of simulation results."""
        strategy_name = candidate.strategy.value.replace('_', ' ')
        outcome_word = "succeed" if success else "have limited effect"
        
        explanation_parts = [
            f"Applying {strategy_name} is predicted to {outcome_word}.",
            f"Expected delay reduction: {delay_reduction} minutes.",
            f"Recovery to normal operations: ~{recovery_time} minutes.",
        ]
        
        # Add relevant side effect notes
        if side_effects.get('cascade_probability', 0) > 0.3:
            explanation_parts.append(
                f"Moderate cascade risk ({side_effects['cascade_probability']:.0%})."
            )
        
        passengers = side_effects.get('passenger_impact', 0)
        if passengers > 100:
            explanation_parts.append(f"Approximately {passengers} passengers affected.")
        
        complexity = side_effects.get('coordination_complexity', 'low')
        if complexity == 'high':
            explanation_parts.append("Requires significant coordination effort.")
        
        return " ".join(explanation_parts)


# =============================================================================
# Legacy SimulationResult (for backwards compatibility)
# =============================================================================

class SimulationResult:
    """
    Legacy container for simulation results.
    
    Maintained for backwards compatibility with existing code.
    New code should use SimulationOutcome instead.
    """
    
    def __init__(
        self,
        strategy: ResolutionStrategy,
        success: bool,
        metrics: Dict[str, Any],
        status: SimulationStatus = SimulationStatus.COMPLETED
    ):
        self.strategy = strategy
        self.success = success
        self.metrics = metrics
        self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "strategy": self.strategy.value,
            "success": self.success,
            "metrics": self.metrics,
            "status": self.status.value
        }
    
    @classmethod
    def from_outcome(cls, outcome: SimulationOutcome) -> "SimulationResult":
        """Create SimulationResult from SimulationOutcome."""
        return cls(
            strategy=outcome.strategy,
            success=outcome.success,
            metrics={
                "delay_after": outcome.delay_after,
                "delay_reduction": outcome.delay_reduction,
                "recovery_time": outcome.recovery_time,
                "score": outcome.score,
                "confidence": outcome.confidence,
                **outcome.side_effects
            },
            status=outcome.status
        )


# =============================================================================
# Legacy SimulationService (for backwards compatibility)
# =============================================================================

class SimulationService:
    """
    Legacy simulation service interface.
    
    Wraps DigitalTwinSimulator for backwards compatibility.
    New code should use DigitalTwinSimulator directly.
    """
    
    def __init__(self, timeout: int = None, seed: Optional[int] = None):
        self.timeout = timeout or settings.SIMULATION_TIMEOUT
        self._simulator = DigitalTwinSimulator(seed=seed)
    
    def simulate(
        self,
        conflict: Dict[str, Any],
        strategy: ResolutionStrategy,
        parameters: Dict[str, Any] = None
    ) -> SimulationResult:
        """Run simulation for a conflict resolution strategy."""
        candidate = ResolutionCandidate(
            strategy=strategy,
            parameters=parameters or {}
        )
        outcome = self._simulator.simulate(conflict, candidate)
        return SimulationResult.from_outcome(outcome)
    
    def simulate_all(
        self,
        conflict: Dict[str, Any],
        strategies: List[ResolutionStrategy] = None
    ) -> List[SimulationResult]:
        """Simulate all applicable strategies for a conflict."""
        outcomes = self._simulator.simulate_all(conflict, strategies)
        return [SimulationResult.from_outcome(o) for o in outcomes]


# =============================================================================
# Factory Functions
# =============================================================================

_simulator_instance: Optional[DigitalTwinSimulator] = None


def get_digital_twin_simulator(seed: Optional[int] = None) -> DigitalTwinSimulator:
    """
    Get a singleton DigitalTwinSimulator instance.
    
    For use with FastAPI dependency injection.
    
    Args:
        seed: Random seed for reproducibility.
    
    Returns:
        DigitalTwinSimulator instance.
    """
    global _simulator_instance
    
    if _simulator_instance is None:
        _simulator_instance = DigitalTwinSimulator(seed=seed)
    elif seed is not None:
        # Reset seed if a new one is provided
        _simulator_instance.reset_seed(seed)
    
    return _simulator_instance


def clear_simulator_cache() -> None:
    """Clear the singleton instance (useful for testing)."""
    global _simulator_instance
    _simulator_instance = None
