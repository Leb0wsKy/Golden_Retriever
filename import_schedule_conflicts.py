"""
Import Schedule Conflicts into Digital Twin

Imports the schedule_conflicts.csv dataset into the Digital Twin's
conflict_memory collection via the API.

Usage:
    python import_schedule_conflicts.py [--limit 100] [--dry-run]

Options:
    --limit N       Only import first N conflicts (for testing)
    --dry-run       Show what would be imported without actually importing
    --url URL       Digital Twin URL (default: http://localhost:8000)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import requests
from datetime import datetime
from tqdm import tqdm

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR / "ai-service" / "dataset"
CSV_FILE = DATASET_DIR / "processed" / "schedule_conflicts.csv"

# Mapping from schedule conflict types to Digital Twin types
CONFLICT_TYPE_MAPPING = {
    "platform_conflict": "platform_conflict",
    "headway_conflict": "headway_conflict",
    "delay_propagation_conflict": "service_disruption",
    "capacity_congestion_conflict": "capacity_overload",
    "service_gap_conflict": "service_disruption",
    "schedule_inconsistency_conflict": "service_disruption",
    "transfer_timing_conflict": "service_disruption",
    "normal": "service_disruption",  # Default for non-conflict records
}

# Severity mapping (based on conflict characteristics)
def map_severity(row: pd.Series) -> str:
    """Map conflict characteristics to severity level."""
    # Check if severity column exists and map it
    if 'severity' in row and pd.notna(row['severity']):
        severity_map = {
            'severe': 'high',
            'moderate': 'medium',
            'minor': 'low',
            'none': 'low'
        }
        return severity_map.get(row['severity'], 'medium')
    
    # Fallback based on conflict type
    conflict_type = row.get('conflict_label', 'normal')
    
    # High severity
    if conflict_type in ['platform_conflict', 'capacity_congestion_conflict']:
        return 'high'
    
    # Medium severity
    if conflict_type in ['headway_conflict', 'delay_propagation_conflict']:
        return 'medium'
    
    # Low severity
    return 'low'


# Time of day mapping
def map_time_of_day(row: pd.Series) -> str:
    """Extract time of day from schedule data."""
    # Check if time_of_day column exists
    if 'time_of_day' in row and pd.notna(row['time_of_day']):
        time_map = {
            'morning_peak': 'morning_peak',
            'evening_peak': 'evening_peak',
            'off_peak': 'midday',
            'night': 'night',
            'early_morning': 'early_morning'
        }
        return time_map.get(row['time_of_day'], 'midday')
    
    # Try to parse arrival or departure time
    for col in ['arrival_time', 'departure_time', 'scheduled_arrival', 'scheduled_departure']:
        if col in row and pd.notna(row[col]):
            try:
                time_str = str(row[col])
                hour = int(time_str.split(':')[0]) if ':' in time_str else 12
                
                if 4 <= hour < 7:
                    return 'early_morning'
                elif 7 <= hour < 10:
                    return 'morning_peak'
                elif 10 <= hour < 16:
                    return 'midday'
                elif 16 <= hour < 19:
                    return 'evening_peak'
                elif 19 <= hour < 23:
                    return 'evening'
                else:
                    return 'night'
            except:
                pass
    
    return 'midday'  # Default


def create_conflict_payload(row: pd.Series, index: int) -> Dict[str, Any]:
    """Convert CSV row to Digital Twin conflict payload."""
    conflict_type = CONFLICT_TYPE_MAPPING.get(
        row.get('conflict_label', 'normal'),
        'service_disruption'
    )
    
    # Extract station name
    station = row.get('stop_name', row.get('origin_stop_name', 'Unknown Station'))
    
    # Build description
    description_parts = []
    if pd.notna(row.get('conflict_flags')):
        flags = str(row['conflict_flags']).split(',')
        description_parts.extend(flags)
    
    if not description_parts:
        description_parts.append(f"{row.get('conflict_label', 'Unknown')} detected at {station}")
    
    description = " | ".join(description_parts[:3])  # Limit to 3 parts
    
    # Ensure description meets minimum length
    if len(description) < 10:
        description = f"Schedule conflict: {description} at {station}"
    
    # Extract affected trains
    affected_trains = []
    for col in ['trip_id', 'route_id', 'trip_headsign']:
        if col in row and pd.notna(row[col]):
            affected_trains.append(str(row[col]))
    
    if not affected_trains:
        affected_trains = [f"train_{index}"]
    
    # Build metadata
    metadata = {
        "source": "schedule_conflicts_dataset",
        "dataset_row": index,
        "conflict_label": row.get('conflict_label', 'normal'),
    }
    
    # Add optional fields from dataset
    for col in ['route_id', 'trip_id', 'stop_id', 'scheduled_arrival', 'scheduled_departure']:
        if col in row and pd.notna(row[col]):
            metadata[col] = str(row[col])
    
    payload = {
        "conflict_type": conflict_type,
        "severity": map_severity(row),
        "station": station,
        "time_of_day": map_time_of_day(row),
        "affected_trains": affected_trains[:5],  # Limit to 5
        "delay_before": int(row.get('delay_minutes', 0)) if pd.notna(row.get('delay_minutes')) else 0,
        "description": description,
        "metadata": metadata
    }
    
    return payload


def import_conflicts(csv_path: Path, digital_twin_url: str, limit: int = None, dry_run: bool = False):
    """Import conflicts from CSV into Digital Twin."""
    
    print(f"\n📂 Loading dataset: {csv_path}")
    
    if not csv_path.exists():
        print(f"❌ Dataset not found: {csv_path}")
        return False
    
    df = pd.read_csv(csv_path)
    print(f"✅ Loaded {len(df):,} records")
    
    # Filter to conflicts only
    if 'is_conflict' in df.columns:
        df = df[df['is_conflict'] == True]
        print(f"📊 Filtered to {len(df):,} conflicts")
    
    if limit:
        df = df.head(limit)
        print(f"🔢 Limited to first {limit} conflicts")
    
    if len(df) == 0:
        print("⚠️ No conflicts to import")
        return True
    
    # Show sample
    print(f"\n📋 Sample conflict:")
    sample = create_conflict_payload(df.iloc[0], 0)
    print(json.dumps(sample, indent=2))
    
    if dry_run:
        print(f"\n🔍 DRY RUN - Would import {len(df)} conflicts to {digital_twin_url}")
        return True
    
    # Import conflicts
    print(f"\n🚀 Importing {len(df):,} conflicts to {digital_twin_url}/api/v1/conflicts/")
    
    imported = 0
    failed = 0
    errors = []
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Importing"):
        try:
            payload = create_conflict_payload(row, idx)
            
            response = requests.post(
                f"{digital_twin_url}/api/v1/conflicts/",
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                imported += 1
            else:
                failed += 1
                error_msg = f"Row {idx}: HTTP {response.status_code} - {response.text[:100]}"
                errors.append(error_msg)
                if failed <= 5:  # Show first 5 errors
                    print(f"\n⚠️ {error_msg}")
        
        except Exception as e:
            failed += 1
            error_msg = f"Row {idx}: {str(e)[:100]}"
            errors.append(error_msg)
            if failed <= 5:
                print(f"\n❌ {error_msg}")
    
    # Summary
    print(f"\n" + "="*60)
    print(f"📊 Import Summary")
    print("="*60)
    print(f"✅ Imported: {imported:,}")
    print(f"❌ Failed: {failed:,}")
    print(f"📈 Success Rate: {(imported/(imported+failed)*100):.1f}%")
    
    if errors and failed > 5:
        print(f"\n⚠️ Showing first 5 errors, {failed-5} more errors occurred")
    
    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Import schedule conflicts into Digital Twin")
    parser.add_argument("--url", default="http://localhost:8000", help="Digital Twin URL")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of conflicts to import")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported without importing")
    parser.add_argument("--csv", default=str(CSV_FILE), help="Path to schedule_conflicts.csv")
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("  📥 IMPORT SCHEDULE CONFLICTS INTO DIGITAL TWIN")
    print("="*70)
    
    print(f"\n⚙️ Configuration:")
    print(f"   Digital Twin URL: {args.url}")
    print(f"   CSV File: {args.csv}")
    print(f"   Limit: {args.limit if args.limit else 'None (all conflicts)'}")
    print(f"   Dry Run: {args.dry_run}")
    
    # Test Digital Twin connectivity
    print(f"\n🔍 Testing Digital Twin connection...")
    try:
        response = requests.get(f"{args.url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Digital Twin is healthy")
        else:
            print(f"⚠️ Digital Twin returned HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to Digital Twin: {e}")
        print(f"   Make sure Digital Twin is running on {args.url}")
        return 1
    
    # Import conflicts
    success = import_conflicts(
        Path(args.csv),
        args.url,
        limit=args.limit,
        dry_run=args.dry_run
    )
    
    if success:
        print(f"\n✅ Import complete!")
        
        if not args.dry_run:
            print(f"\n🎯 Next Steps:")
            print(f"   1. Query conflicts: GET {args.url}/api/v1/conflicts/")
            print(f"   2. Check Qdrant: {args.url}/api/v1/conflicts/stats")
            print(f"   3. Test recommendations with imported conflicts")
    else:
        print(f"\n❌ Import had failures. Check errors above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
