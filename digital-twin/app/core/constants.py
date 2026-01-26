"""
Application constants and enumerations.

Defines constant values and enums used throughout the application
for conflict types, resolution strategies, and other domain concepts.
"""

from enum import Enum


class ConflictType(str, Enum):
    """Types of rail conflicts that can occur."""
    
    PLATFORM_CONFLICT = "platform_conflict"     # Platform allocation conflict
    HEADWAY_CONFLICT = "headway_conflict"       # Minimum headway violation
    TRACK_BLOCKAGE = "track_blockage"           # Track occupation/blockage
    CAPACITY_OVERLOAD = "capacity_overload"     # Station/line capacity exceeded


class ConflictSeverity(str, Enum):
    """Severity levels for conflicts."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TimeOfDay(str, Enum):
    """Time periods for conflict occurrence."""
    
    EARLY_MORNING = "early_morning"     # 04:00 - 07:00
    MORNING_PEAK = "morning_peak"       # 07:00 - 10:00
    MIDDAY = "midday"                   # 10:00 - 16:00
    EVENING_PEAK = "evening_peak"       # 16:00 - 19:00
    EVENING = "evening"                 # 19:00 - 23:00
    NIGHT = "night"                     # 23:00 - 04:00


class ResolutionStrategy(str, Enum):
    """Available resolution strategies."""
    
    REROUTE = "reroute"                 # Change train route
    REORDER = "reorder"                 # Change train order/priority
    DELAY = "delay"                     # Add delay to one or more trains
    PLATFORM_CHANGE = "platform_change" # Assign different platform
    SPEED_ADJUSTMENT = "speed_adjustment"  # Adjust train speed
    CANCELLATION = "cancellation"       # Cancel a service (last resort)
    HOLD = "hold"                       # Hold train at station


class ResolutionOutcome(str, Enum):
    """Possible outcomes of a resolution attempt."""
    
    SUCCESS = "success"                 # Resolution fully successful
    PARTIAL_SUCCESS = "partial_success" # Resolution partially worked
    FAILED = "failed"                   # Resolution did not work
    ESCALATED = "escalated"             # Required manual intervention


class SimulationStatus(str, Enum):
    """Status of a simulation run."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


# Default values
DEFAULT_SIMILARITY_THRESHOLD = 0.75
DEFAULT_TOP_K_RESULTS = 10
MAX_SIMULATION_ITERATIONS = 1000

# Conflict generation defaults
MIN_AFFECTED_TRAINS = 1
MAX_AFFECTED_TRAINS = 6
MIN_DELAY_MINUTES = 0
MAX_DELAY_MINUTES = 120
