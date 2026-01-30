"""
Generate Synthetic Schedule Conflicts

Creates realistic schedule conflict scenarios for UK stations.
Since Transitland doesn't have UK rail data, we generate synthetic
conflicts based on real-world patterns.

Output:
    - dataset/processed/schedule_conflicts.csv
    - dataset/processed/schedule_conflicts.label_distribution.json
"""

import json
import random
import pandas as pd
from pathlib import Path
from datetime import datetime, time, timedelta
from typing import List, Dict

# Paths
DATASET_DIR = Path(__file__).parent / "dataset"
PROCESSED_DIR = DATASET_DIR / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# UK Stations
STATIONS = [
    "London Euston", "London Kings Cross", "London St Pancras",
    "London Paddington", "London Waterloo", "London Victoria",
    "Birmingham New Street", "Manchester Piccadilly",
    "Edinburgh Waverley", "Glasgow Central", "Leeds", "York"
]

# Routes (realistic UK routes)
ROUTES = [
    ("London Euston", "Birmingham New Street", "West Coast Main Line"),
    ("London Euston", "Manchester Piccadilly", "West Coast Main Line"),
    ("London Kings Cross", "Edinburgh Waverley", "East Coast Main Line"),
    ("London Kings Cross", "Leeds", "East Coast Main Line"),
    ("London Kings Cross", "York", "East Coast Main Line"),
    ("London St Pancras", "Birmingham New Street", "Midland Main Line"),
    ("London Paddington", "Bristol", "Great Western Main Line"),
    ("London Waterloo", "Southampton", "South Western Main Line"),
    ("Manchester Piccadilly", "Glasgow Central", "West Coast Main Line"),
]

# Platforms per station
PLATFORMS = {
    "London Euston": [f"Platform {i}" for i in range(1, 19)],
    "London Kings Cross": [f"Platform {i}" for i in range(1, 12)],
    "London St Pancras": [f"Platform {i}" for i in range(1, 14)],
    "London Paddington": [f"Platform {i}" for i in range(1, 15)],
    "Birmingham New Street": [f"Platform {i}" for i in range(1, 13)],
    "Manchester Piccadilly": [f"Platform {i}" for i in range(1, 15)],
}

# Default platforms
DEFAULT_PLATFORMS = [f"Platform {i}" for i in range(1, 9)]

# Conflict types and their typical scenarios
CONFLICT_SCENARIOS = {
    "platform_conflict": {
        "description": "Two trains scheduled for same platform at overlapping times",
        "severity_range": (15, 45),  # minutes delay
        "typical_gap": (0, 5),  # minutes overlap/gap
        "weight": 0.25
    },
    "headway_conflict": {
        "description": "Insufficient time between consecutive trains",
        "severity_range": (5, 20),
        "typical_gap": (1, 3),  # minutes (should be 3-5)
        "weight": 0.20
    },
    "delay_propagation_conflict": {
        "description": "Incoming delay affects downstream schedule",
        "severity_range": (10, 60),
        "typical_gap": (0, 15),
        "weight": 0.15
    },
    "capacity_congestion_conflict": {
        "description": "Too many trains competing for limited platforms",
        "severity_range": (20, 90),
        "typical_gap": (0, 10),
        "weight": 0.15
    },
    "service_gap_conflict": {
        "description": "Excessive gap in service on a route",
        "severity_range": (30, 120),
        "typical_gap": (60, 180),
        "weight": 0.10
    },
    "schedule_inconsistency_conflict": {
        "description": "Schedule doesn't match published timetable",
        "severity_range": (5, 30),
        "typical_gap": (0, 20),
        "weight": 0.10
    },
    "transfer_timing_conflict": {
        "description": "Insufficient connection time between services",
        "severity_range": (5, 25),
        "typical_gap": (2, 8),  # minutes (should be 10-15)
        "weight": 0.05
    }
}


def generate_time(hour_range=(6, 22)):
    """Generate random time within hour range."""
    hour = random.randint(*hour_range)
    minute = random.choice([0, 15, 30, 45])
    return time(hour, minute)


def generate_trip_id(station: str, route: str, time_val: time) -> str:
    """Generate trip ID."""
    station_code = station.replace(" ", "")[:4].upper()
    route_code = route.replace(" ", "")[:4].upper()
    time_str = time_val.strftime("%H%M")
    return f"{station_code}_{route_code}_{time_str}_{random.randint(1000, 9999)}"


def generate_conflicts(num_per_type: int = 100) -> List[Dict]:
    """Generate synthetic schedule conflicts."""
    conflicts = []
    
    for conflict_type, config in CONFLICT_SCENARIOS.items():
        count = int(num_per_type * config["weight"] / 0.15)  # Adjust based on weight
        
        for _ in range(count):
            # Pick random station
            station = random.choice(STATIONS)
            platforms = PLATFORMS.get(station, DEFAULT_PLATFORMS)
            platform = random.choice(platforms)
            
            # Pick route
            origin, dest, route_name = random.choice(ROUTES)
            
            # Generate times
            scheduled_time = generate_time()
            delay_min = random.randint(*config["severity_range"])
            actual_time = (datetime.combine(datetime.today(), scheduled_time) + 
                          timedelta(minutes=delay_min)).time()
            
            # Generate trip ID
            trip_id = generate_trip_id(station, route_name, scheduled_time)
            
            # Build conflict record
            conflict = {
                "conflict_label": conflict_type,
                "is_conflict": True,
                "station": station,
                "stop_name": station,
                "platform": platform,
                "trip_id": trip_id,
                "route_id": route_name.replace(" ", "_").lower(),
                "route_name": route_name,
                "trip_headsign": dest,
                "scheduled_arrival": scheduled_time.strftime("%H:%M:%S"),
                "scheduled_departure": (datetime.combine(datetime.today(), scheduled_time) + 
                                       timedelta(minutes=2)).time().strftime("%H:%M:%S"),
                "actual_arrival": actual_time.strftime("%H:%M:%S") if delay_min > 0 else None,
                "delay_minutes": delay_min,
                "conflict_flags": config["description"],
                "severity": "severe" if delay_min > 30 else "moderate" if delay_min > 15 else "minor",
                "time_of_day": _get_time_of_day(scheduled_time),
                "service_date": "2026-01-28",
                "source": "synthetic"
            }
            
            conflicts.append(conflict)
    
    # Add some normal (non-conflict) records for balance
    for _ in range(num_per_type // 2):
        station = random.choice(STATIONS)
        platforms = PLATFORMS.get(station, DEFAULT_PLATFORMS)
        origin, dest, route_name = random.choice(ROUTES)
        scheduled_time = generate_time()
        trip_id = generate_trip_id(station, route_name, scheduled_time)
        
        normal = {
            "conflict_label": "normal",
            "is_conflict": False,
            "station": station,
            "stop_name": station,
            "platform": random.choice(platforms),
            "trip_id": trip_id,
            "route_id": route_name.replace(" ", "_").lower(),
            "route_name": route_name,
            "trip_headsign": dest,
            "scheduled_arrival": scheduled_time.strftime("%H:%M:%S"),
            "scheduled_departure": (datetime.combine(datetime.today(), scheduled_time) + 
                                   timedelta(minutes=2)).time().strftime("%H:%M:%S"),
            "actual_arrival": None,
            "delay_minutes": 0,
            "conflict_flags": None,
            "severity": "none",
            "time_of_day": _get_time_of_day(scheduled_time),
            "service_date": "2026-01-28",
            "source": "synthetic"
        }
        conflicts.append(normal)
    
    return conflicts


def _get_time_of_day(t: time) -> str:
    """Map time to time of day category."""
    hour = t.hour
    if 6 <= hour < 9:
        return "morning_peak"
    elif 17 <= hour < 20:
        return "evening_peak"
    elif 9 <= hour < 17:
        return "off_peak"
    else:
        return "night"


def main():
    print("\n" + "="*70)
    print("  🏭 GENERATE SYNTHETIC SCHEDULE CONFLICTS")
    print("="*70)
    
    print("\n⚙️ Generating conflicts...")
    conflicts = generate_conflicts(num_per_type=150)
    
    print(f"✅ Generated {len(conflicts):,} records")
    
    # Convert to DataFrame
    df = pd.DataFrame(conflicts)
    
    # Shuffle
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Save CSV
    csv_file = PROCESSED_DIR / "schedule_conflicts.csv"
    df.to_csv(csv_file, index=False)
    print(f"📝 Saved: {csv_file}")
    
    # Generate label distribution
    label_counts = df["conflict_label"].value_counts().to_dict()
    distribution = {
        "total_records": len(df),
        "conflict_records": len(df[df["is_conflict"] == True]),
        "normal_records": len(df[df["is_conflict"] == False]),
        "label_distribution": label_counts,
        "conflict_types": list(CONFLICT_SCENARIOS.keys()),
        "generation_timestamp": datetime.now().isoformat()
    }
    
    dist_file = PROCESSED_DIR / "schedule_conflicts.label_distribution.json"
    with open(dist_file, 'w') as f:
        json.dump(distribution, f, indent=2)
    print(f"📊 Distribution: {dist_file}")
    
    # Print summary
    print("\n" + "="*70)
    print("📊 DATASET SUMMARY")
    print("="*70)
    print(f"Total Records: {distribution['total_records']:,}")
    print(f"Conflicts: {distribution['conflict_records']:,}")
    print(f"Normal: {distribution['normal_records']:,}")
    print(f"\nConflict Type Distribution:")
    for label, count in sorted(label_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(df)) * 100
        print(f"  {label:40s}: {count:4d} ({pct:5.1f}%)")
    
    print(f"\n✅ Synthetic dataset generation complete!")
    return 0


if __name__ == "__main__":
    exit(main())
