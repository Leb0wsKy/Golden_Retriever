"""
Schedule-based conflict generator using real transit data.

This generator creates conflicts based on real schedule data from
the Transitland API, making conflicts much more realistic.

Conflict Detection Logic:
- Platform conflicts: Two trains scheduled for same platform within 3 min
- Headway violations: Consecutive trains closer than minimum headway
- Capacity overload: Too many trains in station during a time window
"""

import logging
import random
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from dataclasses import dataclass

from app.core.constants import (
    ConflictType,
    ConflictSeverity,
    TimeOfDay,
)
from app.models.conflict import (
    GeneratedConflict,
)
from app.services.transitland_client import (
    TransitlandClient,
    ScheduleWindow,
    get_transitland_client,
)
from app.services.conflict_generator import ConflictGenerator, GeneratorConfig


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class ScheduleConflictConfig:
    """Configuration for schedule-based conflict detection."""
    
    # Platform conflict thresholds
    min_platform_turnaround_minutes: int = 3  # Min time between trains on same platform
    platform_conflict_window_minutes: int = 5  # Window to check for conflicts
    
    # Headway thresholds
    min_headway_seconds: int = 180  # 3 minutes minimum headway
    headway_warning_seconds: int = 240  # 4 minutes = warning level
    
    # Capacity thresholds
    capacity_window_minutes: int = 15  # Time window for capacity calculation
    max_movements_per_window: int = 12  # Max trains in window before overload
    
    # Delay injection for realism
    delay_probability: float = 0.3  # 30% of trains have delays
    max_delay_minutes: int = 20  # Maximum random delay


# =============================================================================
# Helper Functions
# =============================================================================

def _time_diff_minutes(time1: str, time2: str) -> float:
    """Calculate difference in minutes between two time strings."""
    def parse_minutes(t: str) -> float:
        parts = t.split(":")
        return int(parts[0]) * 60 + int(parts[1]) + (int(parts[2]) / 60 if len(parts) > 2 else 0)
    
    return parse_minutes(time2) - parse_minutes(time1)


def _add_minutes_to_time(time_str: str, minutes: int) -> str:
    """Add minutes to a time string."""
    parts = time_str.split(":")
    total_minutes = int(parts[0]) * 60 + int(parts[1]) + minutes
    hours = total_minutes // 60
    mins = total_minutes % 60
    return f"{hours:02d}:{mins:02d}:00"


def _hour_to_time_of_day(hour: int) -> TimeOfDay:
    """Convert hour to TimeOfDay enum."""
    if 4 <= hour < 7:
        return TimeOfDay.EARLY_MORNING
    elif 7 <= hour < 10:
        return TimeOfDay.MORNING_PEAK
    elif 10 <= hour < 16:
        return TimeOfDay.MIDDAY
    elif 16 <= hour < 19:
        return TimeOfDay.EVENING_PEAK
    elif 19 <= hour < 23:
        return TimeOfDay.EVENING
    else:
        return TimeOfDay.NIGHT


def _calculate_platform_severity(gap_minutes: float, config: ScheduleConflictConfig) -> ConflictSeverity:
    """Calculate severity based on platform gap."""
    if gap_minutes < 0:
        return ConflictSeverity.CRITICAL  # Overlap
    elif gap_minutes < 1:
        return ConflictSeverity.HIGH
    elif gap_minutes < 2:
        return ConflictSeverity.MEDIUM
    else:
        return ConflictSeverity.LOW


def _calculate_headway_severity(headway_seconds: int, config: ScheduleConflictConfig) -> ConflictSeverity:
    """Calculate severity based on headway violation."""
    if headway_seconds < 60:
        return ConflictSeverity.CRITICAL
    elif headway_seconds < 120:
        return ConflictSeverity.HIGH
    elif headway_seconds < 150:
        return ConflictSeverity.MEDIUM
    else:
        return ConflictSeverity.LOW


def _calculate_capacity_severity(count: int, limit: int) -> ConflictSeverity:
    """Calculate severity based on capacity exceedance."""
    ratio = count / limit
    if ratio > 1.5:
        return ConflictSeverity.CRITICAL
    elif ratio > 1.3:
        return ConflictSeverity.HIGH
    elif ratio > 1.15:
        return ConflictSeverity.MEDIUM
    else:
        return ConflictSeverity.LOW


# =============================================================================
# Conflict Detection Functions
# =============================================================================

def detect_platform_conflicts(
    schedule: ScheduleWindow,
    config: ScheduleConflictConfig,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    """
    Detect platform conflicts from schedule data.
    
    A platform conflict occurs when two trains are scheduled to use
    the same platform within the minimum turnaround time.
    
    Args:
        schedule: Station schedule window
        config: Detection configuration
        rng: Random number generator for delay injection
    
    Returns:
        List of detected platform conflict scenarios
    """
    conflicts = []
    
    for platform, movements in schedule.platform_usage.items():
        # Sort by arrival/departure time
        sorted_movements = sorted(
            movements,
            key=lambda m: m.get("arrival_time") or m.get("departure_time") or "99:99:99"
        )
        
        for i in range(1, len(sorted_movements)):
            prev = sorted_movements[i - 1]
            curr = sorted_movements[i]
            
            # Calculate time gap
            prev_dep = prev.get("departure_time", prev.get("arrival_time", ""))
            curr_arr = curr.get("arrival_time", curr.get("departure_time", ""))
            
            if not prev_dep or not curr_arr:
                continue
            
            gap_minutes = _time_diff_minutes(prev_dep, curr_arr)
            
            # Inject random delay to simulate real-world conditions
            if rng.random() < config.delay_probability:
                delay = rng.randint(1, config.max_delay_minutes)
                gap_minutes -= delay  # Delay reduces the gap
            
            # Check for conflict
            if gap_minutes < config.min_platform_turnaround_minutes:
                severity = _calculate_platform_severity(gap_minutes, config)
                
                conflicts.append({
                    "type": ConflictType.PLATFORM_CONFLICT,
                    "platform": platform,
                    "train_1": {
                        "id": prev.get("train_number") or prev.get("trip_id", ""),
                        "route": prev.get("route_name", ""),
                        "departure": prev_dep,
                        "headsign": prev.get("headsign", ""),
                    },
                    "train_2": {
                        "id": curr.get("train_number") or curr.get("trip_id", ""),
                        "route": curr.get("route_name", ""),
                        "arrival": curr_arr,
                        "headsign": curr.get("headsign", ""),
                    },
                    "gap_minutes": gap_minutes,
                    "severity": severity,
                    "station": schedule.station_name,
                })
    
    return conflicts


def detect_headway_violations(
    schedule: ScheduleWindow,
    config: ScheduleConflictConfig,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    """
    Detect headway violations between consecutive trains.
    
    A headway violation occurs when trains following each other
    on the same route are closer than the minimum safe headway.
    """
    conflicts = []
    
    # Group departures by route
    routes: Dict[str, List[Dict[str, Any]]] = {}
    for departure in schedule.departures:
        route = departure.get("route_name", "unknown")
        if route not in routes:
            routes[route] = []
        routes[route].append(departure)
    
    for route_name, route_departures in routes.items():
        # Sort by departure time
        sorted_deps = sorted(
            route_departures,
            key=lambda d: d.get("departure_time", "99:99:99")
        )
        
        for i in range(1, len(sorted_deps)):
            prev = sorted_deps[i - 1]
            curr = sorted_deps[i]
            
            prev_time = prev.get("departure_time", "")
            curr_time = curr.get("departure_time", "")
            
            if not prev_time or not curr_time:
                continue
            
            headway_seconds = int(_time_diff_minutes(prev_time, curr_time) * 60)
            
            # Inject delay
            if rng.random() < config.delay_probability:
                delay_seconds = rng.randint(30, config.max_delay_minutes * 60)
                headway_seconds -= delay_seconds
            
            if headway_seconds < config.min_headway_seconds:
                severity = _calculate_headway_severity(headway_seconds, config)
                
                conflicts.append({
                    "type": ConflictType.HEADWAY_CONFLICT,
                    "route": route_name,
                    "leading_train": {
                        "id": prev.get("train_number") or prev.get("trip_id", ""),
                        "departure": prev_time,
                    },
                    "following_train": {
                        "id": curr.get("train_number") or curr.get("trip_id", ""),
                        "departure": curr_time,
                    },
                    "headway_seconds": max(0, headway_seconds),
                    "required_headway_seconds": config.min_headway_seconds,
                    "severity": severity,
                    "station": schedule.station_name,
                })
    
    return conflicts


def detect_capacity_overloads(
    schedule: ScheduleWindow,
    config: ScheduleConflictConfig,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    """
    Detect capacity overload situations.
    
    Capacity overload occurs when too many trains are scheduled
    to use a station within a given time window.
    """
    conflicts = []
    detected_windows = set()  # Track detected windows to avoid duplicates
    
    # Combine all movements and sort by time
    all_movements = []
    for arr in schedule.arrivals:
        movement_copy = dict(arr)
        movement_copy["movement_type"] = "arrival"
        all_movements.append(movement_copy)
    for dep in schedule.departures:
        movement_copy = dict(dep)
        movement_copy["movement_type"] = "departure"
        all_movements.append(movement_copy)
    
    all_movements.sort(
        key=lambda m: m.get("arrival_time") or m.get("departure_time") or "99:99:99"
    )
    
    # Sliding window analysis
    window_size = config.capacity_window_minutes
    
    for i, movement in enumerate(all_movements):
        movement_time = movement.get("arrival_time") or movement.get("departure_time")
        if not movement_time:
            continue
        
        # Skip if we've already detected a conflict in this time window
        window_key = movement_time[:5]  # HH:MM
        if window_key in detected_windows:
            continue
        
        # Count movements in window
        window_end_time = _add_minutes_to_time(movement_time, window_size)
        
        movements_in_window = []
        for j in range(i, len(all_movements)):
            other_time = all_movements[j].get("arrival_time") or all_movements[j].get("departure_time")
            if other_time and other_time <= window_end_time:
                movements_in_window.append(all_movements[j])
            elif other_time and other_time > window_end_time:
                break
        
        # Check for overload
        if len(movements_in_window) > config.max_movements_per_window:
            # Determine time of day
            hour = int(movement_time.split(":")[0])
            time_of_day = _hour_to_time_of_day(hour)
            
            # Higher threshold during peak (already busy)
            adjusted_threshold = config.max_movements_per_window
            if time_of_day in [TimeOfDay.MORNING_PEAK, TimeOfDay.EVENING_PEAK]:
                adjusted_threshold = int(adjusted_threshold * 1.2)
            
            if len(movements_in_window) > adjusted_threshold:
                severity = _calculate_capacity_severity(
                    len(movements_in_window), adjusted_threshold
                )
                
                affected_trains = [
                    m.get("train_number") or m.get("trip_id", "")
                    for m in movements_in_window
                ]
                
                conflicts.append({
                    "type": ConflictType.CAPACITY_OVERLOAD,
                    "window_start": movement_time,
                    "window_minutes": window_size,
                    "movements_count": len(movements_in_window),
                    "capacity_limit": adjusted_threshold,
                    "affected_trains": affected_trains[:6],  # Limit for readability
                    "severity": severity,
                    "station": schedule.station_name,
                    "time_of_day": time_of_day,
                })
                
                # Mark this window as detected
                detected_windows.add(window_key)
    
    return conflicts


# =============================================================================
# Schedule-Based Conflict Generator
# =============================================================================

class ScheduleBasedConflictGenerator:
    """
    Generates conflicts based on real schedule data.
    
    This generator fetches real schedules from Transitland and
    detects realistic conflict scenarios based on actual timetables.
    
    Example:
        >>> generator = ScheduleBasedConflictGenerator()
        >>> conflicts = await generator.generate_from_schedule(
        ...     station="London Euston",
        ...     date=date.today(),
        ...     count=10
        ... )
    """
    
    def __init__(
        self,
        seed: Optional[int] = None,
        config: Optional[ScheduleConflictConfig] = None,
        generator_config: Optional[GeneratorConfig] = None,
    ):
        """
        Initialize the schedule-based generator.
        
        Args:
            seed: Random seed for reproducibility
            config: Conflict detection configuration
            generator_config: Configuration for resolution/outcome generation
        """
        self.seed = seed
        self._rng = random.Random(seed)
        self.config = config or ScheduleConflictConfig()
        
        # Use original generator for resolution/outcome generation
        self._base_generator = ConflictGenerator(seed=seed, config=generator_config)
        
        # Transitland client
        self._client: Optional[TransitlandClient] = None
    
    def _get_client(self) -> TransitlandClient:
        """Get or create Transitland client."""
        if self._client is None:
            self._client = get_transitland_client()
        return self._client
    
    async def generate_from_schedule(
        self,
        station: str,
        schedule_date: Optional[date] = None,
        start_hour: int = 6,
        end_hour: int = 22,
        count: int = 10,
        conflict_types: Optional[List[ConflictType]] = None,
    ) -> List[GeneratedConflict]:
        """
        Generate conflicts from real schedule data.
        
        Args:
            station: Station name to analyze
            schedule_date: Date to fetch schedule for (default: today)
            start_hour: Start of analysis window
            end_hour: End of analysis window
            count: Maximum number of conflicts to generate
            conflict_types: Filter to specific conflict types
        
        Returns:
            List of generated conflicts based on real schedule patterns
        """
        if schedule_date is None:
            schedule_date = date.today()
        
        # Fetch schedule
        client = self._get_client()
        schedule = await client.get_station_schedule(
            station_name=station,
            schedule_date=schedule_date,
            start_hour=start_hour,
            end_hour=end_hour,
        )
        
        # Detect conflicts
        all_detected = []
        platform_conflicts = []
        headway_conflicts = []
        capacity_conflicts = []
        
        if conflict_types is None or ConflictType.PLATFORM_CONFLICT in conflict_types:
            platform_conflicts = detect_platform_conflicts(
                schedule, self.config, self._rng
            )
            all_detected.extend(platform_conflicts)
        
        if conflict_types is None or ConflictType.HEADWAY_CONFLICT in conflict_types:
            headway_conflicts = detect_headway_violations(
                schedule, self.config, self._rng
            )
            all_detected.extend(headway_conflicts)
        
        if conflict_types is None or ConflictType.CAPACITY_OVERLOAD in conflict_types:
            capacity_conflicts = detect_capacity_overloads(
                schedule, self.config, self._rng
            )
            all_detected.extend(capacity_conflicts)
        
        # Shuffle and limit
        self._rng.shuffle(all_detected)
        selected = all_detected[:count]
        
        # Convert to GeneratedConflict objects
        generated = []
        for detected in selected:
            conflict = self._convert_to_generated_conflict(detected, schedule_date)
            generated.append(conflict)
        
        logger.info(
            f"Generated {len(generated)} schedule-based conflicts for {station} "
            f"({len(platform_conflicts)} platform, "
            f"{len(headway_conflicts)} headway, "
            f"{len(capacity_conflicts)} capacity detected)"
        )
        
        return generated
    
    def _convert_to_generated_conflict(
        self,
        detected: Dict[str, Any],
        schedule_date: date,
    ) -> GeneratedConflict:
        """Convert a detected conflict to a GeneratedConflict object."""
        conflict_type = detected["type"]
        severity = detected["severity"]
        station = detected["station"]
        
        # Determine time of day from conflict timing
        if conflict_type == ConflictType.PLATFORM_CONFLICT:
            time_str = detected["train_2"]["arrival"]
            hour = int(time_str.split(":")[0])
            time_of_day = _hour_to_time_of_day(hour)
            affected_trains = [
                detected["train_1"]["id"],
                detected["train_2"]["id"],
            ]
            platform = detected["platform"]
            description = self._generate_platform_description(detected)
            delay_before = self._estimate_delay(severity, conflict_type)
            track_section = None
            
        elif conflict_type == ConflictType.HEADWAY_CONFLICT:
            time_str = detected["following_train"]["departure"]
            hour = int(time_str.split(":")[0])
            time_of_day = _hour_to_time_of_day(hour)
            affected_trains = [
                detected["leading_train"]["id"],
                detected["following_train"]["id"],
            ]
            platform = None
            track_section = detected.get("route", "Main Line")
            description = self._generate_headway_description(detected)
            delay_before = self._estimate_delay(severity, conflict_type)
            
        elif conflict_type == ConflictType.CAPACITY_OVERLOAD:
            time_of_day = detected.get("time_of_day", TimeOfDay.MIDDAY)
            affected_trains = detected.get("affected_trains", [])
            platform = None
            track_section = None
            description = self._generate_capacity_description(detected)
            delay_before = self._estimate_delay(severity, conflict_type)
            
        else:
            # Fallback
            time_of_day = TimeOfDay.MIDDAY
            affected_trains = []
            platform = None
            track_section = None
            description = "Schedule-based conflict detected"
            delay_before = 10
        
        # Generate resolution and outcome using base generator logic
        recommended_resolution = self._base_generator._generate_resolution(
            conflict_type, severity, delay_before
        )
        final_outcome = self._base_generator._generate_outcome(
            severity, recommended_resolution, delay_before
        )
        
        # Create conflict timestamp
        conflict_time = datetime.combine(
            schedule_date,
            datetime.min.time().replace(
                hour=self._rng.randint(6, 21),
                minute=self._rng.randint(0, 59)
            )
        )
        
        return GeneratedConflict(
            id=self._base_generator._generate_id(),
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
            detected_at=conflict_time - timedelta(minutes=self._rng.randint(5, 15)),
            metadata={
                "source": "schedule_based",
                "schedule_date": schedule_date.isoformat(),
                "detection_data": detected,
            },
            recommended_resolution=recommended_resolution,
            final_outcome=final_outcome,
        )
    
    def _generate_platform_description(self, detected: Dict[str, Any]) -> str:
        """Generate description for platform conflict."""
        t1 = detected["train_1"]
        t2 = detected["train_2"]
        platform = detected["platform"]
        gap = detected["gap_minutes"]
        
        if gap < 0:
            return (
                f"Platform {platform} overlap conflict: {t1['id']} ({t1['route']}) "
                f"scheduled to depart at {t1['departure']} while {t2['id']} ({t2['route']}) "
                f"arrives at {t2['arrival']}. Trains overlapping by {abs(gap):.1f} minutes."
            )
        else:
            return (
                f"Platform {platform} turnaround violation: Only {gap:.1f} minutes between "
                f"{t1['id']} departure ({t1['departure']}) and {t2['id']} arrival ({t2['arrival']}). "
                f"Minimum required: {self.config.min_platform_turnaround_minutes} minutes."
            )
    
    def _generate_headway_description(self, detected: Dict[str, Any]) -> str:
        """Generate description for headway conflict."""
        leading = detected["leading_train"]
        following = detected["following_train"]
        headway = detected["headway_seconds"]
        required = detected["required_headway_seconds"]
        route = detected["route"]
        
        return (
            f"Headway violation on {route}: {following['id']} following {leading['id']} "
            f"with only {headway}s gap (minimum required: {required}s). "
            f"Departures at {leading['departure']} and {following['departure']}."
        )
    
    def _generate_capacity_description(self, detected: Dict[str, Any]) -> str:
        """Generate description for capacity conflict."""
        count = detected["movements_count"]
        limit = detected["capacity_limit"]
        window = detected["window_minutes"]
        trains = detected["affected_trains"]
        
        trains_str = ", ".join(str(t) for t in trains[:4])
        suffix = "..." if len(trains) > 4 else ""
        
        return (
            f"Capacity overload: {count} train movements scheduled within {window}-minute window "
            f"(capacity: {limit}). Affected services include: {trains_str}{suffix}."
        )
    
    def _estimate_delay(
        self,
        severity: ConflictSeverity,
        conflict_type: ConflictType
    ) -> int:
        """Estimate delay based on severity and conflict type."""
        base_delays = {
            ConflictSeverity.LOW: (3, 8),
            ConflictSeverity.MEDIUM: (5, 15),
            ConflictSeverity.HIGH: (10, 25),
            ConflictSeverity.CRITICAL: (20, 45),
        }
        
        min_delay, max_delay = base_delays.get(severity, (5, 15))
        
        # Adjust by conflict type
        if conflict_type == ConflictType.TRACK_BLOCKAGE:
            min_delay = int(min_delay * 1.5)
            max_delay = int(max_delay * 1.5)
        
        return self._rng.randint(min_delay, max_delay)
    
    async def generate_multi_station(
        self,
        stations: Optional[List[str]] = None,
        schedule_date: Optional[date] = None,
        count_per_station: int = 5,
    ) -> List[GeneratedConflict]:
        """
        Generate conflicts from multiple stations.
        
        Args:
            stations: List of station names (default: major UK stations)
            schedule_date: Date to analyze
            count_per_station: Conflicts to generate per station
        
        Returns:
            Combined list of conflicts from all stations
        """
        if stations is None:
            stations = [
                "London Euston",
                "London Kings Cross",
                "Birmingham New Street",
                "Manchester Piccadilly",
                "Edinburgh Waverley",
            ]
        
        all_conflicts = []
        for station in stations:
            try:
                conflicts = await self.generate_from_schedule(
                    station=station,
                    schedule_date=schedule_date,
                    count=count_per_station,
                )
                all_conflicts.extend(conflicts)
            except Exception as e:
                logger.warning(f"Failed to generate conflicts for {station}: {e}")
        
        return all_conflicts


# =============================================================================
# Hybrid Generator (Combines Both Approaches)
# =============================================================================

class HybridConflictGenerator:
    """
    Hybrid generator that combines schedule-based and synthetic conflicts.
    
    Uses schedule data when available, falls back to synthetic generation
    when API is unavailable or for specific use cases.
    """
    
    def __init__(
        self,
        seed: Optional[int] = None,
        schedule_ratio: float = 0.7,  # 70% schedule-based
    ):
        """
        Initialize hybrid generator.
        
        Args:
            seed: Random seed
            schedule_ratio: Ratio of schedule-based vs synthetic conflicts
        """
        self.seed = seed
        self.schedule_ratio = schedule_ratio
        self._rng = random.Random(seed)
        
        self._schedule_generator = ScheduleBasedConflictGenerator(seed=seed)
        self._synthetic_generator = ConflictGenerator(seed=seed)
    
    async def generate(
        self,
        count: int = 10,
        stations: Optional[List[str]] = None,
        schedule_date: Optional[date] = None,
    ) -> List[GeneratedConflict]:
        """
        Generate a mix of schedule-based and synthetic conflicts.
        """
        schedule_count = int(count * self.schedule_ratio)
        synthetic_count = count - schedule_count
        
        conflicts = []
        
        # Try schedule-based generation
        if schedule_count > 0:
            try:
                schedule_conflicts = await self._schedule_generator.generate_multi_station(
                    stations=stations,
                    schedule_date=schedule_date,
                    count_per_station=max(1, schedule_count // 5),
                )
                conflicts.extend(schedule_conflicts[:schedule_count])
            except Exception as e:
                logger.warning(f"Schedule generation failed, using synthetic: {e}")
                synthetic_count += schedule_count
        
        # Fill remainder with synthetic
        if synthetic_count > 0:
            synthetic_conflicts = self._synthetic_generator.generate(count=synthetic_count)
            conflicts.extend(synthetic_conflicts)
        
        # Shuffle to mix
        self._rng.shuffle(conflicts)
        
        return conflicts[:count]


# =============================================================================
# Factory Functions
# =============================================================================

_schedule_generator_instance: Optional[ScheduleBasedConflictGenerator] = None
_hybrid_generator_instance: Optional[HybridConflictGenerator] = None


def get_schedule_conflict_generator(
    seed: Optional[int] = None
) -> ScheduleBasedConflictGenerator:
    """Get or create schedule-based generator singleton."""
    global _schedule_generator_instance
    if _schedule_generator_instance is None:
        _schedule_generator_instance = ScheduleBasedConflictGenerator(seed=seed)
    return _schedule_generator_instance


def get_hybrid_generator(
    seed: Optional[int] = None,
    schedule_ratio: float = 0.7,
) -> HybridConflictGenerator:
    """Get or create hybrid generator singleton."""
    global _hybrid_generator_instance
    if _hybrid_generator_instance is None:
        _hybrid_generator_instance = HybridConflictGenerator(
            seed=seed,
            schedule_ratio=schedule_ratio,
        )
    return _hybrid_generator_instance


def clear_generator_caches() -> None:
    """Clear all generator singletons."""
    global _schedule_generator_instance, _hybrid_generator_instance
    _schedule_generator_instance = None
    _hybrid_generator_instance = None
