"""
Populate Pre-Conflict Memory Collection

This script generates synthetic pre-conflict network states based on existing
conflicts in the conflict_memory collection. For each conflict, it creates
a plausible pre-conflict state (10-30 minutes before the conflict occurred)
and stores it in the pre_conflict_memory collection.

This enables the pre-conflict scanner to have historical patterns to match against.

Usage:
    python populate_pre_conflict_memory.py --count 50
"""

import asyncio
import logging
import argparse
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# Add digital-twin to Python path
sys.path.insert(0, str(Path(__file__).parent / "digital-twin"))

from app.services.qdrant_service import get_qdrant_service, PreConflictState
from app.services.embedding_service import get_embedding_service
from app.core.constants import ConflictType, ConflictSeverity, TimeOfDay

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PreConflictGenerator:
    """Generates synthetic pre-conflict states from conflict data."""
    
    def __init__(self):
        self.qdrant_service = get_qdrant_service()
        self.embedding_service = get_embedding_service()
    
    async def generate_pre_conflict_states(self, count: int = 50) -> List[tuple]:
        """
        Generate synthetic pre-conflict states.
        
        Args:
            count: Number of pre-conflict states to generate
        
        Returns:
            List of tuples (PreConflictState, embedding)
        """
        logger.info(f"🔍 Fetching existing conflicts from conflict_memory...")
        
        # Try to fetch existing conflicts
        try:
            # Search for any conflicts (using empty query to get all)
            conflicts = await self.qdrant_service.search_conflicts(
                query_embedding=self.embedding_service.embed("conflict"),
                limit=100
            )
            logger.info(f"Found {len(conflicts)} existing conflicts to base pre-conflict states on")
        except Exception as e:
            logger.warning(f"Could not fetch conflicts: {e}. Will generate from scratch.")
            conflicts = []
        
        pre_conflict_states = []
        
        for i in range(count):
            # If we have conflicts, use them as basis; otherwise generate fresh
            if conflicts and i < len(conflicts):
                conflict = conflicts[i]
                pre_state = self._generate_from_conflict(conflict)
            else:
                pre_state = self._generate_synthetic()
            
            pre_conflict_states.append(pre_state)
            
            if (i + 1) % 10 == 0:
                logger.info(f"Generated {i + 1}/{count} pre-conflict states...")
        
        logger.info(f"✅ Generated {len(pre_conflict_states)} pre-conflict states")
        return pre_conflict_states
    
    def _generate_from_conflict(self, conflict) -> PreConflictState:
        """Generate pre-conflict state based on an actual conflict."""
        
        # Extract conflict details
        conflict_type = getattr(conflict, 'conflict_type', ConflictType.PLATFORM_CONFLICT)
        severity = getattr(conflict, 'severity', ConflictSeverity.MEDIUM)
        station = getattr(conflict, 'station', 'London Waterloo')
        time_of_day = getattr(conflict, 'time_of_day', TimeOfDay.MORNING_PEAK)
        
        # Generate network state that would precede this conflict
        network_state = self._generate_pre_conflict_network_state(
            conflict_type, severity, time_of_day
        )
        
        # Time before conflict (10-30 minutes)
        minutes_before = random.randint(10, 30)
        
        # Create description
        description = (
            f"Pre-conflict state: {network_state['active_trains']} trains active, "
            f"{network_state['average_delay_minutes']:.1f} min avg delay, "
            f"{network_state['congestion_level']} congestion at {station}. "
            f"Network density {network_state['network_density']:.2f}. "
            f"This state preceded a {conflict_type.value} conflict."
        )
        
        # Generate embedding
        embedding = self.embedding_service.embed(description)
        
        pre_state = PreConflictState(
            id=f"pre-conf-{datetime.utcnow().timestamp()}-{random.randint(1000, 9999)}",
            timestamp=datetime.utcnow() - timedelta(minutes=minutes_before),
            station=station,
            time_of_day=time_of_day.value,
            conflict_occurred=True,  # This state led to a conflict
            conflict_type=conflict_type.value,
            conflict_id=getattr(conflict, 'id', None),
            metadata={
                'network_state': network_state,
                'conflict_occurred_later': True,
                'later_conflict_id': getattr(conflict, 'id', None),
                'later_conflict_type': conflict_type.value,
                'minutes_until_conflict': minutes_before,
                'description': description
            }
        )
        
        return (pre_state, embedding)
    
    def _generate_synthetic(self) -> PreConflictState:
        """Generate completely synthetic pre-conflict state."""
        
        # Random conflict characteristics
        conflict_types = list(ConflictType)
        severities = list(ConflictSeverity)
        times_of_day = list(TimeOfDay)
        stations = [
            'London Waterloo', 'London Victoria', 'London Bridge',
            'Birmingham New Street', 'Manchester Piccadilly', 'Leeds',
            'Glasgow Central', 'Edinburgh Waverley', 'Liverpool Lime Street'
        ]
        
        conflict_type = random.choice(conflict_types)
        severity = random.choice(severities)
        time_of_day = random.choice(times_of_day)
        station = random.choice(stations)
        
        # Generate network state
        network_state = self._generate_pre_conflict_network_state(
            conflict_type, severity, time_of_day
        )
        
        minutes_before = random.randint(10, 30)
        
        description = (
            f"Pre-conflict state: {network_state['active_trains']} trains active, "
            f"{network_state['average_delay_minutes']:.1f} min avg delay, "
            f"{network_state['congestion_level']} congestion at {station}. "
            f"Network density {network_state['network_density']:.2f}. "
            f"This pattern historically led to {conflict_type.value} conflicts."
        )
        
        embedding = self.embedding_service.embed(description)
        
        pre_state = PreConflictState(
            id=f"pre-conf-synthetic-{datetime.utcnow().timestamp()}-{random.randint(1000, 9999)}",
            timestamp=datetime.utcnow() - timedelta(days=random.randint(1, 90)),
            station=station,
            time_of_day=time_of_day.value,
            conflict_occurred=True,  # This state led to a conflict
            conflict_type=conflict_type.value,
            metadata={
                'network_state': network_state,
                'conflict_occurred_later': True,
                'later_conflict_type': conflict_type.value,
                'minutes_until_conflict': minutes_before,
                'description': description
            }
        )
        
        return (pre_state, embedding)
    
    def _generate_pre_conflict_network_state(
        self,
        conflict_type: ConflictType,
        severity: ConflictSeverity,
        time_of_day: TimeOfDay
    ) -> Dict[str, Any]:
        """
        Generate realistic pre-conflict network conditions.
        
        The state is calibrated to reflect conditions that typically
        precede the given conflict type and severity.
        """
        
        # Base values depend on time of day
        if time_of_day in [TimeOfDay.MORNING_PEAK, TimeOfDay.EVENING_PEAK]:
            base_trains = random.randint(15, 25)
            base_delay = random.uniform(3, 8)
            base_density = random.uniform(0.65, 0.85)
            congestion = random.choice(['moderate', 'high'])
        elif time_of_day in [TimeOfDay.MIDDAY, TimeOfDay.EARLY_MORNING, TimeOfDay.EVENING]:
            base_trains = random.randint(8, 15)
            base_delay = random.uniform(1, 4)
            base_density = random.uniform(0.35, 0.55)
            congestion = random.choice(['low', 'moderate'])
        else:  # NIGHT
            base_trains = random.randint(2, 6)
            base_delay = random.uniform(0.5, 2)
            base_density = random.uniform(0.1, 0.3)
            congestion = 'low'
        
        # Adjust based on conflict type (pre-conflict states show warning signs)
        if conflict_type == ConflictType.PLATFORM_CONFLICT:
            base_trains += random.randint(2, 5)  # More trains = platform pressure
            base_density += 0.1
        elif conflict_type == ConflictType.TRACK_BLOCKAGE:
            base_delay += random.uniform(1, 3)  # Delays building up
        elif conflict_type == ConflictType.TIMETABLE_CONFLICT:
            base_delay += random.uniform(2, 5)  # Clear delay signals
        
        # Severity amplifies the problems
        severity_multiplier = {
            ConflictSeverity.LOW: 0.8,
            ConflictSeverity.MEDIUM: 1.0,
            ConflictSeverity.HIGH: 1.3,
            ConflictSeverity.CRITICAL: 1.6
        }.get(severity, 1.0)
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'active_trains': int(base_trains * severity_multiplier),
            'average_delay_minutes': round(base_delay * severity_multiplier, 1),
            'congestion_level': congestion,
            'network_density': min(0.95, round(base_density * severity_multiplier, 2)),
            'infrastructure_status': random.choice(['normal', 'degraded']) if severity_multiplier > 1.2 else 'normal',
            'weather_impact': random.choice(['none', 'minor', 'moderate']) if random.random() > 0.7 else 'none',
            'passenger_volume': random.choice(['normal', 'high', 'very_high']) if base_trains > 15 else 'normal'
        }
    
    async def store_pre_conflict_states(self, states: List[tuple]) -> int:
        """
        Store pre-conflict states in Qdrant.
        
        Args:
            states: List of tuples (PreConflictState, embedding)
        
        Returns:
            Number of states successfully stored
        """
        logger.info(f"💾 Storing {len(states)} pre-conflict states in Qdrant...")
        
        stored_count = 0
        errors = []
        
        for i, (state, embedding) in enumerate(states):
            try:
                self.qdrant_service.upsert_pre_conflict_state(state, embedding)
                stored_count += 1
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Stored {i + 1}/{len(states)} states...")
                    
            except Exception as e:
                errors.append(f"Failed to store state {state.id}: {e}")
                if len(errors) <= 5:  # Only log first 5 errors
                    logger.error(errors[-1])
        
        if errors and len(errors) > 5:
            logger.warning(f"... and {len(errors) - 5} more errors")
        
        logger.info(f"✅ Successfully stored {stored_count}/{len(states)} pre-conflict states")
        return stored_count


async def main():
    """Main execution function."""
    
    parser = argparse.ArgumentParser(
        description='Populate pre-conflict memory with synthetic data'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=50,
        help='Number of pre-conflict states to generate (default: 50)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("  PRE-CONFLICT MEMORY POPULATION TOOL")
    print("=" * 70)
    print(f"\n🎯 Target: Generate {args.count} pre-conflict states")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nThis will:")
    print("  1. Fetch existing conflicts from conflict_memory (if any)")
    print("  2. Generate realistic pre-conflict network states")
    print("  3. Store them in pre_conflict_memory collection")
    print("  4. Enable the pre-conflict scanner to detect patterns")
    print("\n" + "=" * 70 + "\n")
    
    try:
        generator = PreConflictGenerator()
        
        # Generate states
        states = await generator.generate_pre_conflict_states(count=args.count)
        
        if not states:
            logger.error("❌ No states generated. Exiting.")
            return 1
        
        # Store in Qdrant
        stored = await generator.store_pre_conflict_states(states)
        
        print("\n" + "=" * 70)
        print("  SUMMARY")
        print("=" * 70)
        print(f"✅ Generated: {len(states)} pre-conflict states")
        print(f"✅ Stored: {stored} states in Qdrant")
        print(f"✅ Success Rate: {stored/len(states)*100:.1f}%")
        print("\n🎉 Pre-conflict memory is now populated!")
        print("🔮 The scanner will now detect emerging conflicts every 10 minutes.")
        print("\nTo check scanner status:")
        print("  curl http://localhost:8000/api/v1/preventive-alerts/health")
        print("\nTo view alerts:")
        print("  curl http://localhost:8000/api/v1/preventive-alerts/")
        print("=" * 70 + "\n")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
