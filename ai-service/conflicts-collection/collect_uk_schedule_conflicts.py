"""
Schedule Conflict Dataset Collection Script

Collects schedule data from Transitland for 16 UK stations and
builds a labeled conflict dataset for training and analysis.

Usage:
    python collect_uk_schedule_conflicts.py

Output:
    - ai-service/dataset/raw/schedule_stop_pairs.jsonl
    - ai-service/dataset/processed/schedule_conflicts.csv
    - ai-service/dataset/processed/schedule_conflicts.label_distribution.json
"""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Add dataset to path
SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_DIR = SCRIPT_DIR / "dataset"
sys.path.insert(0, str(DATASET_DIR))

# UK Station Codes from Digital Twin
UK_STATIONS = {
    "London Euston": "s-gcpvj-londoneuston",
    "London Kings Cross": "s-gcpvj-londonkingscross",
    "London St Pancras": "s-gcpvj-londonstpancras",
    "London Paddington": "s-gcpv-londonpaddington",
    "London Waterloo": "s-gcpu-londonwaterloo",
    "London Victoria": "s-gcpu-londonvictoria",
    "London Liverpool Street": "s-gcpw-londonliverpoolstreet",
    "Birmingham New Street": "s-gcqd-birminghamnewstreet",
    "Manchester Piccadilly": "s-gcw2-manchesterpiccadilly",
    "Edinburgh Waverley": "s-gcp6-edinburghwaverley",
    "Glasgow Central": "s-gckx-glasgowcentral",
    "Leeds": "s-gcse-leeds",
    "Liverpool Lime Street": "s-gcmv-liverpoollimestreet",
    "Bristol Temple Meads": "s-gbz-bristoltemplemeads",
    "Newcastle": "s-gcp7-newcastlecentral",
    "York": "s-gcx6-york",
}


def check_environment():
    """Verify environment setup."""
    print("🔍 Checking environment...")
    
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv("TRANSITLAND_API_KEY")
    if not api_key or api_key == "your_transitland_api_key_here":
        print("❌ ERROR: TRANSITLAND_API_KEY not configured")
        print("   Set it in .env file or export as environment variable")
        return False
    
    print(f"✅ TRANSITLAND_API_KEY found ({api_key[:10]}...)")
    
    # Check dataset directory
    if not DATASET_DIR.exists():
        print(f"❌ ERROR: Dataset directory not found: {DATASET_DIR}")
        return False
    
    print(f"✅ Dataset directory found: {DATASET_DIR}")
    
    # Check required scripts
    collect_script = DATASET_DIR / "collect_schedule_stop_pairs.py"
    build_script = DATASET_DIR / "build_schedule_conflicts.py"
    
    if not collect_script.exists():
        print(f"❌ ERROR: Collection script not found: {collect_script}")
        return False
    
    if not build_script.exists():
        print(f"❌ ERROR: Build script not found: {build_script}")
        return False
    
    print("✅ Required scripts found")
    
    return True


def collect_schedule_data():
    """Collect schedule data from Transitland for all UK stations."""
    print("\n" + "="*60)
    print("📡 STEP 1: Collecting Schedule Data from Transitland")
    print("="*60)
    
    station_ids = ",".join(UK_STATIONS.values())
    
    print(f"\n📍 Stations to collect ({len(UK_STATIONS)}):")
    for name, code in UK_STATIONS.items():
        print(f"   • {name:<30} → {code}")
    
    print(f"\n🚀 Starting collection...")
    print(f"   Station IDs: {station_ids[:50]}...")
    print(f"   Follow pagination: Yes")
    print(f"   Max pages per station: 10")
    
    collect_script = DATASET_DIR / "collect_schedule_stop_pairs.py"
    
    cmd = [
        sys.executable,
        str(collect_script),
        "--stop-ids", station_ids,
        "--follow-next",
        "--max-pages", "10"
    ]
    
    print(f"\n💻 Command: {' '.join(cmd)}")
    print("\n⏳ This may take 5-10 minutes...")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        if result.returncode != 0:
            print(f"\n❌ Collection failed!")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            return False
        
        print(f"\n✅ Collection complete!")
        print(result.stdout)
        
        # Check output file
        raw_file = DATASET_DIR / "raw" / "schedule_stop_pairs.jsonl"
        if raw_file.exists():
            line_count = sum(1 for _ in open(raw_file, encoding='utf-8'))
            file_size = raw_file.stat().st_size / 1024 / 1024  # MB
            print(f"\n📊 Output: {raw_file}")
            print(f"   Lines: {line_count:,}")
            print(f"   Size: {file_size:.2f} MB")
        else:
            print(f"\n⚠️ Warning: Output file not found: {raw_file}")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("\n❌ Collection timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"\n❌ Collection error: {e}")
        return False


def build_conflict_dataset():
    """Build labeled conflict dataset from raw schedule data."""
    print("\n" + "="*60)
    print("🔨 STEP 2: Building Schedule Conflict Dataset")
    print("="*60)
    
    build_script = DATASET_DIR / "build_schedule_conflicts.py"
    
    print(f"\n🚀 Processing schedule data...")
    print(f"   Input: raw/schedule_stop_pairs.jsonl")
    print(f"   Output: processed/schedule_conflicts.csv")
    
    cmd = [
        sys.executable,
        str(build_script)
    ]
    
    print(f"\n💻 Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode != 0:
            print(f"\n❌ Build failed!")
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")
            return False
        
        print(f"\n✅ Build complete!")
        print(result.stdout)
        
        # Check output files
        csv_file = DATASET_DIR / "processed" / "schedule_conflicts.csv"
        dist_file = DATASET_DIR / "processed" / "schedule_conflicts.label_distribution.json"
        
        if csv_file.exists():
            line_count = sum(1 for _ in open(csv_file, encoding='utf-8')) - 1  # -1 for header
            file_size = csv_file.stat().st_size / 1024  # KB
            print(f"\n📊 Dataset: {csv_file}")
            print(f"   Rows: {line_count:,}")
            print(f"   Size: {file_size:.2f} KB")
        
        if dist_file.exists():
            import json
            with open(dist_file) as f:
                distribution = json.load(f)
            
            print(f"\n📈 Label Distribution:")
            total = sum(distribution.values())
            for label, count in sorted(distribution.items(), key=lambda x: -x[1]):
                pct = (count / total * 100) if total > 0 else 0
                print(f"   • {label:<40} {count:>6,} ({pct:>5.1f}%)")
            print(f"   {'─' * 60}")
            print(f"   {'TOTAL':<40} {total:>6,} (100.0%)")
        
        return True
        
    except subprocess.TimeoutExpired:
        print("\n❌ Build timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"\n❌ Build error: {e}")
        return False


def analyze_conflicts():
    """Analyze the conflict dataset and map to Digital Twin types."""
    print("\n" + "="*60)
    print("📊 STEP 3: Analyzing Conflict Types")
    print("="*60)
    
    csv_file = DATASET_DIR / "processed" / "schedule_conflicts.csv"
    
    if not csv_file.exists():
        print(f"❌ Dataset not found: {csv_file}")
        return False
    
    try:
        import pandas as pd
        
        df = pd.read_csv(csv_file)
        
        print(f"\n📋 Dataset Overview:")
        print(f"   Total records: {len(df):,}")
        print(f"   Columns: {len(df.columns)}")
        
        if 'conflict_label' in df.columns:
            conflicts_only = df[df['is_conflict'] == True]
            print(f"   Conflicts: {len(conflicts_only):,} ({len(conflicts_only)/len(df)*100:.1f}%)")
            print(f"   Normal: {len(df[df['is_conflict'] == False]):,} ({len(df[df['is_conflict'] == False])/len(df)*100:.1f}%)")
        
        # Mapping to Digital Twin conflict types
        schedule_to_digital_twin = {
            "platform_conflict": "platform_conflict",  # Direct match
            "headway_conflict": "headway_conflict",  # Direct match
            "delay_propagation_conflict": "service_disruption",
            "capacity_congestion_conflict": "capacity_overload",
            "service_gap_conflict": "service_disruption",
            "schedule_inconsistency_conflict": "service_disruption",
            "transfer_timing_conflict": "service_disruption",
            "normal": "normal"
        }
        
        print(f"\n🔗 Mapping to Digital Twin Conflict Types:")
        print(f"   Schedule Type → Digital Twin Type")
        print(f"   {'─' * 60}")
        
        if 'conflict_label' in df.columns:
            for schedule_type in df['conflict_label'].unique():
                dt_type = schedule_to_digital_twin.get(schedule_type, "unknown")
                count = len(df[df['conflict_label'] == schedule_type])
                print(f"   {schedule_type:<35} → {dt_type:<25} ({count:,})")
        
        # Digital Twin coverage analysis
        digital_twin_types = {
            "platform_conflict",
            "headway_conflict", 
            "track_blockage",
            "capacity_overload",
            "signal_failure",
            "crew_shortage",
            "rolling_stock_failure",
            "weather_disruption",
            "passenger_incident",
            "infrastructure_work",
            "power_supply_issue",
            "station_overcrowding",
            "service_disruption"
        }
        
        covered_types = set(schedule_to_digital_twin.values())
        coverage_pct = len(covered_types) / len(digital_twin_types) * 100
        
        print(f"\n✅ Digital Twin Coverage:")
        print(f"   Covered types: {len(covered_types)}/{len(digital_twin_types)} ({coverage_pct:.0f}%)")
        print(f"   Covered: {', '.join(sorted(covered_types))}")
        
        uncovered = digital_twin_types - covered_types
        if uncovered:
            print(f"   Not in schedule data: {', '.join(sorted(uncovered))}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Analysis error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main execution flow."""
    print("\n" + "="*70)
    print("  🚆 UK SCHEDULE CONFLICT DATASET COLLECTION")
    print("="*70)
    
    # Step 0: Check environment
    if not check_environment():
        print("\n❌ Environment check failed. Aborting.")
        return 1
    
    # Step 1: Collect schedule data
    if not collect_schedule_data():
        print("\n❌ Schedule data collection failed. Aborting.")
        return 1
    
    # Step 2: Build conflict dataset
    if not build_conflict_dataset():
        print("\n❌ Dataset build failed. Aborting.")
        return 1
    
    # Step 3: Analyze conflicts
    if not analyze_conflicts():
        print("\n❌ Conflict analysis failed. Aborting.")
        return 1
    
    print("\n" + "="*70)
    print("  ✅ SCHEDULE CONFLICT DATASET COMPLETE")
    print("="*70)
    
    print("\n📁 Output Files:")
    print(f"   • {DATASET_DIR}/raw/schedule_stop_pairs.jsonl")
    print(f"   • {DATASET_DIR}/processed/schedule_conflicts.csv")
    print(f"   • {DATASET_DIR}/processed/schedule_conflicts.label_distribution.json")
    
    print("\n🚀 Next Steps:")
    print("   1. Review label distribution in schedule_conflicts.label_distribution.json")
    print("   2. Run: python import_schedule_conflicts.py  (to import into Digital Twin)")
    print("   3. Check conflict_memory collection in Qdrant Cloud")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
