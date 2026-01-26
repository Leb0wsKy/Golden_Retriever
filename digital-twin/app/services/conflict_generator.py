"""
Synthetic rail conflict generator service.

Generates realistic synthetic rail conflicts for testing,
training, and initial system population.
"""

import random
import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.core.constants import (
    ConflictType,
    ConflictSeverity,
    TimeOfDay,
    ResolutionStrategy,
    ResolutionOutcome,
    MIN_AFFECTED_TRAINS,
    MAX_AFFECTED_TRAINS,
    MIN_DELAY_MINUTES,
    MAX_DELAY_MINUTES,
)
from app.models.conflict import (
    GeneratedConflict,
    RecommendedResolution,
    FinalOutcome,
)


@dataclass
class GeneratorConfig:
    """Configuration for conflict generation behavior."""
    
    success_rate: float = 0.75          # Base success rate for resolutions
    partial_success_rate: float = 0.15  # Rate of partial successes
    min_confidence: float = 0.6         # Minimum confidence for recommendations
    max_confidence: float = 0.95        # Maximum confidence for recommendations


class ConflictGenerator:
    """
    Generator for synthetic rail conflict data.
    
    Creates realistic conflict scenarios with recommended resolutions
    and final outcomes for testing and training the recommendation system.
    
    Attributes:
        seed: Random seed for reproducibility.
        config: Generator configuration.
        _rng: Random number generator instance.
    
    Example:
        >>> generator = ConflictGenerator(seed=42)
        >>> conflicts = generator.generate(count=10)
        >>> for conflict in conflicts:
        ...     print(f"{conflict.conflict_type}: {conflict.station}")
    """
    
    # ===================
    # Sample Data Pools
    # ===================
    
    STATIONS = [
        "London Euston",
        "Birmingham New Street",
        "Manchester Piccadilly",
        "Edinburgh Waverley",
        "Glasgow Central",
        "Leeds City",
        "Liverpool Lime Street",
        "Bristol Temple Meads",
        "Newcastle Central",
        "York",
        "Sheffield",
        "Nottingham",
        "Cambridge",
        "Oxford",
        "Reading",
        "Southampton Central",
        "Cardiff Central",
        "Crewe",
        "Preston",
        "Doncaster",
    ]
    
    TRAIN_PREFIXES = [
        ("IC", "InterCity"),
        ("RE", "Regional Express"),
        ("S", "Suburban"),
        ("HS", "High Speed"),
        ("XC", "CrossCountry"),
        ("GW", "Great Western"),
        ("AV", "Avanti"),
        ("EM", "East Midlands"),
        ("LN", "LNER"),
        ("SE", "Southeastern"),
    ]
    
    PLATFORMS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "1A", "1B", "2A", "2B"]
    
    TRACK_SECTIONS = [
        "Main Line North Section A",
        "Main Line North Section B",
        "Main Line South Section A",
        "Main Line South Section B",
        "West Coast Main Line",
        "East Coast Main Line",
        "Midland Main Line",
        "Great Western Main Line",
        "Branch Line Alpha",
        "Branch Line Beta",
        "Platform Approach Track 1",
        "Platform Approach Track 2",
        "Freight Corridor East",
        "Freight Corridor West",
        "Express Bypass Loop",
        "Suburban Loop Line",
    ]
    
    # Resolution strategies applicable to each conflict type
    CONFLICT_RESOLUTIONS: Dict[ConflictType, List[ResolutionStrategy]] = {
        ConflictType.PLATFORM_CONFLICT: [
            ResolutionStrategy.PLATFORM_CHANGE,
            ResolutionStrategy.DELAY,
            ResolutionStrategy.REORDER,
            ResolutionStrategy.HOLD,
        ],
        ConflictType.HEADWAY_CONFLICT: [
            ResolutionStrategy.SPEED_ADJUSTMENT,
            ResolutionStrategy.DELAY,
            ResolutionStrategy.REORDER,
            ResolutionStrategy.HOLD,
        ],
        ConflictType.TRACK_BLOCKAGE: [
            ResolutionStrategy.REROUTE,
            ResolutionStrategy.DELAY,
            ResolutionStrategy.HOLD,
            ResolutionStrategy.CANCELLATION,
        ],
        ConflictType.CAPACITY_OVERLOAD: [
            ResolutionStrategy.DELAY,
            ResolutionStrategy.REORDER,
            ResolutionStrategy.REROUTE,
            ResolutionStrategy.CANCELLATION,
        ],
    }
    
    # Severity weights by conflict type (higher = more severe on average)
    SEVERITY_WEIGHTS: Dict[ConflictType, Dict[ConflictSeverity, float]] = {
        ConflictType.PLATFORM_CONFLICT: {
            ConflictSeverity.LOW: 0.3,
            ConflictSeverity.MEDIUM: 0.4,
            ConflictSeverity.HIGH: 0.25,
            ConflictSeverity.CRITICAL: 0.05,
        },
        ConflictType.HEADWAY_CONFLICT: {
            ConflictSeverity.LOW: 0.1,
            ConflictSeverity.MEDIUM: 0.3,
            ConflictSeverity.HIGH: 0.4,
            ConflictSeverity.CRITICAL: 0.2,
        },
        ConflictType.TRACK_BLOCKAGE: {
            ConflictSeverity.LOW: 0.05,
            ConflictSeverity.MEDIUM: 0.2,
            ConflictSeverity.HIGH: 0.4,
            ConflictSeverity.CRITICAL: 0.35,
        },
        ConflictType.CAPACITY_OVERLOAD: {
            ConflictSeverity.LOW: 0.2,
            ConflictSeverity.MEDIUM: 0.35,
            ConflictSeverity.HIGH: 0.3,
            ConflictSeverity.CRITICAL: 0.15,
        },
    }
    
    def __init__(self, seed: Optional[int] = None, config: Optional[GeneratorConfig] = None):
        """
        Initialize the conflict generator.
        
        Args:
            seed: Optional random seed for reproducibility.
            config: Optional generator configuration.
        """
        self.seed = seed
        self.config = config or GeneratorConfig()
        self._rng = random.Random(seed)
    
    def reset_seed(self, seed: int) -> None:
        """
        Reset the random generator with a new seed.
        
        Args:
            seed: New random seed.
        """
        self.seed = seed
        self._rng = random.Random(seed)
    
    def generate(self, count: int = 1) -> List[GeneratedConflict]:
        """
        Generate multiple synthetic conflicts with resolutions and outcomes.
        
        Args:
            count: Number of conflicts to generate.
            
        Returns:
            List of GeneratedConflict Pydantic models.
        
        Example:
            >>> generator = ConflictGenerator(seed=42)
            >>> conflicts = generator.generate(count=5)
            >>> len(conflicts)
            5
        """
        return [self._generate_single() for _ in range(count)]
    
    def generate_by_type(
        self,
        conflict_type: ConflictType,
        count: int = 1
    ) -> List[GeneratedConflict]:
        """
        Generate conflicts of a specific type.
        
        Args:
            conflict_type: Type of conflicts to generate.
            count: Number of conflicts to generate.
            
        Returns:
            List of GeneratedConflict models of the specified type.
        """
        return [self._generate_single(conflict_type=conflict_type) for _ in range(count)]
    
    def _generate_single(
        self,
        conflict_type: Optional[ConflictType] = None
    ) -> GeneratedConflict:
        """Generate a single synthetic conflict with resolution and outcome."""
        
        # Select conflict type
        if conflict_type is None:
            conflict_type = self._rng.choice(list(ConflictType))
        
        # Generate base attributes
        station = self._rng.choice(self.STATIONS)
        time_of_day = self._rng.choice(list(TimeOfDay))
        severity = self._weighted_choice(self.SEVERITY_WEIGHTS[conflict_type])
        affected_trains = self._generate_train_ids(conflict_type, severity)
        delay_before = self._generate_delay(severity)
        
        # Generate type-specific attributes
        platform = None
        track_section = None
        description = ""
        metadata: Dict[str, Any] = {}
        
        if conflict_type == ConflictType.PLATFORM_CONFLICT:
            platform = self._rng.choice(self.PLATFORMS)
            description, metadata = self._generate_platform_conflict_details(
                station, platform, affected_trains, time_of_day
            )
        elif conflict_type == ConflictType.HEADWAY_CONFLICT:
            track_section = self._rng.choice(self.TRACK_SECTIONS)
            description, metadata = self._generate_headway_conflict_details(
                track_section, affected_trains
            )
        elif conflict_type == ConflictType.TRACK_BLOCKAGE:
            track_section = self._rng.choice(self.TRACK_SECTIONS)
            description, metadata = self._generate_track_blockage_details(
                track_section, affected_trains
            )
        elif conflict_type == ConflictType.CAPACITY_OVERLOAD:
            description, metadata = self._generate_capacity_overload_details(
                station, affected_trains, time_of_day
            )
        
        # Generate resolution and outcome
        recommended_resolution = self._generate_resolution(
            conflict_type, severity, delay_before
        )
        final_outcome = self._generate_outcome(
            severity, recommended_resolution, delay_before
        )
        
        # Generate timestamps
        conflict_time = self._generate_conflict_time(time_of_day)
        detected_at = conflict_time - timedelta(minutes=self._rng.randint(5, 30))
        
        return GeneratedConflict(
            id=self._generate_id(),
            conflict_type=conflict_type,
            severity=severity,
            station=station,
            time_of_day=time_of_day,
            affected_trains=affected_trains,
            delay_before=delay_before,
            description=description,
            platform=platform,
            track_section=track_section,
            conflict_time=conflict_time,
            detected_at=detected_at,
            metadata=metadata,
            recommended_resolution=recommended_resolution,
            final_outcome=final_outcome,
        )
    
    def _generate_train_ids(
        self,
        conflict_type: ConflictType,
        severity: ConflictSeverity
    ) -> List[str]:
        """Generate realistic train IDs based on conflict type and severity."""
        
        # More severe conflicts typically involve more trains
        severity_train_counts = {
            ConflictSeverity.LOW: (MIN_AFFECTED_TRAINS, 2),
            ConflictSeverity.MEDIUM: (2, 3),
            ConflictSeverity.HIGH: (2, 4),
            ConflictSeverity.CRITICAL: (3, MAX_AFFECTED_TRAINS),
        }
        
        min_trains, max_trains = severity_train_counts[severity]
        count = self._rng.randint(min_trains, max_trains)
        
        trains = []
        used_numbers = set()
        
        for _ in range(count):
            prefix, _ = self._rng.choice(self.TRAIN_PREFIXES)
            # Ensure unique train numbers
            while True:
                number = self._rng.randint(100, 9999)
                if number not in used_numbers:
                    used_numbers.add(number)
                    break
            trains.append(f"{prefix}{number}")
        
        return trains
    
    def _generate_delay(self, severity: ConflictSeverity) -> int:
        """Generate delay in minutes based on severity."""
        
        delay_ranges = {
            ConflictSeverity.LOW: (MIN_DELAY_MINUTES, 10),
            ConflictSeverity.MEDIUM: (5, 25),
            ConflictSeverity.HIGH: (15, 45),
            ConflictSeverity.CRITICAL: (30, MAX_DELAY_MINUTES),
        }
        
        min_delay, max_delay = delay_ranges[severity]
        return self._rng.randint(min_delay, max_delay)
    
    def _generate_platform_conflict_details(
        self,
        station: str,
        platform: str,
        trains: List[str],
        time_of_day: TimeOfDay
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate details for a platform conflict."""
        
        conflict_reasons = [
            f"Platform {platform} at {station} double-booked",
            f"Late arrival of {trains[0]} blocking Platform {platform}",
            f"Platform {platform} occupied beyond scheduled time",
            f"Conflicting arrivals scheduled for Platform {platform}",
        ]
        
        if len(trains) >= 2:
            description = (
                f"{self._rng.choice(conflict_reasons)}. "
                f"{trains[0]} arrival conflicts with {trains[1]} {'departure' if self._rng.random() > 0.5 else 'arrival'}. "
                f"Occurring during {time_of_day.value.replace('_', ' ')} period."
            )
        else:
            description = (
                f"{self._rng.choice(conflict_reasons)}. "
                f"{trains[0]} unable to access assigned platform. "
                f"Occurring during {time_of_day.value.replace('_', ' ')} period."
            )
        
        metadata = {
            "platform_capacity": 1,
            "trains_waiting": len(trains),
            "available_alternatives": self._rng.randint(0, 3),
            "passenger_impact_estimate": self._rng.randint(50, 500),
        }
        
        return description, metadata
    
    def _generate_headway_conflict_details(
        self,
        track_section: str,
        trains: List[str]
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate details for a headway conflict."""
        
        required_headway = self._rng.randint(3, 6)
        actual_headway = self._rng.randint(1, required_headway - 1)
        
        if len(trains) >= 2:
            description = (
                f"Headway violation on {track_section}. "
                f"{trains[1]} following {trains[0]} with only {actual_headway} minute gap "
                f"(minimum required: {required_headway} minutes). "
                f"Safety system intervention required."
            )
        else:
            description = (
                f"Headway violation detected on {track_section}. "
                f"{trains[0]} approaching with insufficient spacing. "
                f"Minimum headway: {required_headway} minutes, actual: {actual_headway} minutes."
            )
        
        metadata = {
            "required_headway_minutes": required_headway,
            "actual_headway_minutes": actual_headway,
            "track_speed_limit_kmh": self._rng.choice([80, 100, 125, 140, 160, 200]),
            "signaling_system": self._rng.choice(["ETCS Level 2", "AWS/TPWS", "ERTMS"]),
        }
        
        return description, metadata
    
    def _generate_track_blockage_details(
        self,
        track_section: str,
        trains: List[str]
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate details for a track blockage conflict."""
        
        blockage_causes = [
            "signal failure",
            "points failure",
            "overhead line damage",
            "track defect detected",
            "engineering works overrun",
            "trespass incident",
            "vehicle obstruction",
            "adverse weather conditions",
        ]
        
        cause = self._rng.choice(blockage_causes)
        estimated_clearance = self._rng.randint(15, 120)
        
        description = (
            f"Track blockage on {track_section} due to {cause}. "
            f"{len(trains)} train(s) affected: {', '.join(trains[:3])}{'...' if len(trains) > 3 else ''}. "
            f"Estimated clearance time: {estimated_clearance} minutes."
        )
        
        metadata = {
            "blockage_cause": cause,
            "estimated_clearance_minutes": estimated_clearance,
            "alternative_routes_available": self._rng.randint(0, 2),
            "track_length_affected_km": round(self._rng.uniform(0.5, 10.0), 1),
            "bidirectional_track": self._rng.choice([True, False]),
        }
        
        return description, metadata
    
    def _generate_capacity_overload_details(
        self,
        station: str,
        trains: List[str],
        time_of_day: TimeOfDay
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate details for a capacity overload conflict."""
        
        station_capacity = self._rng.randint(8, 20)
        current_demand = station_capacity + self._rng.randint(2, 8)
        time_window = self._rng.choice([15, 30, 45, 60])
        
        description = (
            f"Capacity overload at {station}. "
            f"{current_demand} train movements scheduled within {time_window}-minute window "
            f"(station capacity: {station_capacity}). "
            f"Peak period: {time_of_day.value.replace('_', ' ')}. "
            f"Affected services include: {', '.join(trains[:4])}{'...' if len(trains) > 4 else ''}."
        )
        
        metadata = {
            "station_capacity": station_capacity,
            "scheduled_movements": current_demand,
            "time_window_minutes": time_window,
            "overflow_count": current_demand - station_capacity,
            "platform_utilization_percent": min(100, int((current_demand / station_capacity) * 100)),
        }
        
        return description, metadata
    
    def _generate_resolution(
        self,
        conflict_type: ConflictType,
        severity: ConflictSeverity,
        delay_before: int
    ) -> RecommendedResolution:
        """Generate a recommended resolution for the conflict."""
        
        # Get applicable strategies for this conflict type
        strategies = self.CONFLICT_RESOLUTIONS[conflict_type]
        strategy = self._rng.choice(strategies)
        
        # Higher severity = lower confidence (harder to resolve)
        confidence_penalty = {
            ConflictSeverity.LOW: 0.0,
            ConflictSeverity.MEDIUM: 0.05,
            ConflictSeverity.HIGH: 0.15,
            ConflictSeverity.CRITICAL: 0.25,
        }
        
        base_confidence = self._rng.uniform(
            self.config.min_confidence,
            self.config.max_confidence
        )
        confidence = max(0.5, base_confidence - confidence_penalty[severity])
        
        # Estimate delay reduction
        reduction_factor = self._rng.uniform(0.3, 0.8)
        estimated_reduction = int(delay_before * reduction_factor)
        
        # Generate description
        description = self._generate_resolution_description(
            strategy, conflict_type, estimated_reduction
        )
        
        return RecommendedResolution(
            strategy=strategy,
            confidence=round(confidence, 2),
            estimated_delay_reduction=estimated_reduction,
            description=description,
        )
    
    def _generate_resolution_description(
        self,
        strategy: ResolutionStrategy,
        conflict_type: ConflictType,
        estimated_reduction: int
    ) -> str:
        """Generate human-readable resolution description."""
        
        descriptions = {
            ResolutionStrategy.PLATFORM_CHANGE: (
                f"Redirect affected train to alternative platform. "
                f"Expected to reduce delay by {estimated_reduction} minutes."
            ),
            ResolutionStrategy.DELAY: (
                f"Hold lower-priority service to allow clearance. "
                f"Estimated delay reduction: {estimated_reduction} minutes."
            ),
            ResolutionStrategy.REORDER: (
                f"Adjust train sequence to optimize throughput. "
                f"Should reduce overall delay by {estimated_reduction} minutes."
            ),
            ResolutionStrategy.REROUTE: (
                f"Divert train via alternative route. "
                f"Expected time saving: {estimated_reduction} minutes."
            ),
            ResolutionStrategy.SPEED_ADJUSTMENT: (
                f"Modify train speeds to restore safe headway. "
                f"Projected delay reduction: {estimated_reduction} minutes."
            ),
            ResolutionStrategy.HOLD: (
                f"Hold train at previous station until path clears. "
                f"Estimated impact reduction: {estimated_reduction} minutes."
            ),
            ResolutionStrategy.CANCELLATION: (
                f"Cancel service to reduce network congestion. "
                f"Will free up {estimated_reduction} minutes of capacity."
            ),
        }
        
        return descriptions.get(strategy, f"Apply {strategy.value} strategy.")
    
    def _generate_outcome(
        self,
        severity: ConflictSeverity,
        resolution: RecommendedResolution,
        delay_before: int
    ) -> FinalOutcome:
        """Generate the final outcome based on resolution and severity."""
        
        # Determine outcome based on confidence and severity
        roll = self._rng.random()
        
        # Adjust thresholds based on severity
        severity_penalty = {
            ConflictSeverity.LOW: 0.0,
            ConflictSeverity.MEDIUM: 0.05,
            ConflictSeverity.HIGH: 0.1,
            ConflictSeverity.CRITICAL: 0.2,
        }
        
        adjusted_success_rate = self.config.success_rate - severity_penalty[severity]
        adjusted_partial_rate = self.config.partial_success_rate
        
        if roll < adjusted_success_rate:
            outcome = ResolutionOutcome.SUCCESS
            # Actual delay close to or better than estimate
            actual_delay = max(0, delay_before - resolution.estimated_delay_reduction - self._rng.randint(0, 5))
            notes = "Resolution executed successfully with minimal complications."
        elif roll < adjusted_success_rate + adjusted_partial_rate:
            outcome = ResolutionOutcome.PARTIAL_SUCCESS
            # Actual delay better than before but not as good as estimate
            reduction = int(resolution.estimated_delay_reduction * self._rng.uniform(0.3, 0.7))
            actual_delay = delay_before - reduction
            notes = "Resolution partially effective. Some residual delays remain."
        elif roll < 0.95:
            outcome = ResolutionOutcome.FAILED
            # Delay stays same or gets slightly worse
            actual_delay = delay_before + self._rng.randint(0, 10)
            notes = "Resolution strategy did not achieve desired effect."
        else:
            outcome = ResolutionOutcome.ESCALATED
            # Manual intervention required
            actual_delay = delay_before + self._rng.randint(5, 20)
            notes = "Required escalation to manual control center intervention."
        
        resolution_time = self._rng.randint(5, 30)
        
        return FinalOutcome(
            outcome=outcome,
            actual_delay=actual_delay,
            resolution_time_minutes=resolution_time,
            notes=notes,
        )
    
    def _generate_conflict_time(self, time_of_day: TimeOfDay) -> datetime:
        """Generate a conflict timestamp based on time of day."""
        
        # Map time of day to hour ranges
        hour_ranges = {
            TimeOfDay.EARLY_MORNING: (4, 7),
            TimeOfDay.MORNING_PEAK: (7, 10),
            TimeOfDay.MIDDAY: (10, 16),
            TimeOfDay.EVENING_PEAK: (16, 19),
            TimeOfDay.EVENING: (19, 23),
            TimeOfDay.NIGHT: (23, 4),  # Wraps around midnight
        }
        
        start_hour, end_hour = hour_ranges[time_of_day]
        
        # Handle night period (wraps around midnight)
        if time_of_day == TimeOfDay.NIGHT:
            hour = self._rng.choice([23, 0, 1, 2, 3])
        else:
            hour = self._rng.randint(start_hour, end_hour - 1)
        
        minute = self._rng.randint(0, 59)
        
        # Use current date
        base_date = datetime.utcnow().replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0
        )
        
        # Add random offset of 0-7 days in the future
        days_offset = self._rng.randint(0, 7)
        return base_date + timedelta(days=days_offset)
    
    def _generate_id(self) -> str:
        """Generate a unique conflict ID."""
        return f"conflict-{uuid.uuid4().hex[:12]}"
    
    def _weighted_choice(self, weights: Dict[Any, float]) -> Any:
        """Make a weighted random choice."""
        items = list(weights.keys())
        probabilities = list(weights.values())
        return self._rng.choices(items, weights=probabilities, k=1)[0]
    
    # ===================
    # Utility Methods
    # ===================
    
    def to_dict_list(self, conflicts: List[GeneratedConflict]) -> List[Dict[str, Any]]:
        """Convert a list of conflicts to dictionaries."""
        return [conflict.model_dump() for conflict in conflicts]
    
    def to_embedding_text(self, conflict: GeneratedConflict) -> str:
        """
        Generate text representation for embedding.
        
        Creates a structured text from conflict attributes
        suitable for generating vector embeddings.
        
        Args:
            conflict: GeneratedConflict to convert.
            
        Returns:
            Text representation for embedding.
        """
        parts = [
            f"Type: {conflict.conflict_type.value}",
            f"Station: {conflict.station}",
            f"Severity: {conflict.severity.value}",
            f"Time: {conflict.time_of_day.value}",
            f"Trains: {', '.join(conflict.affected_trains)}",
            f"Delay: {conflict.delay_before} minutes",
            f"Description: {conflict.description}",
        ]
        
        if conflict.platform:
            parts.append(f"Platform: {conflict.platform}")
        if conflict.track_section:
            parts.append(f"Track: {conflict.track_section}")
        
        parts.append(f"Resolution: {conflict.recommended_resolution.strategy.value}")
        parts.append(f"Outcome: {conflict.final_outcome.outcome.value}")
        
        return " | ".join(parts)


# =============================================================================
# Factory Functions
# =============================================================================

# Singleton instance
_generator_instance: Optional[ConflictGenerator] = None


def get_conflict_generator(seed: Optional[int] = None) -> ConflictGenerator:
    """
    Get or create the conflict generator singleton.
    
    Args:
        seed: Optional random seed (only used on first creation).
        
    Returns:
        ConflictGenerator instance.
    """
    global _generator_instance
    
    if _generator_instance is None:
        _generator_instance = ConflictGenerator(seed=seed)
    
    return _generator_instance


def clear_generator_cache() -> None:
    """Clear the generator singleton cache."""
    global _generator_instance
    _generator_instance = None
