"""
Simple UK Schedule Collection

Collects departure schedules from 16 UK stations using Transitland API.
Uses the working /stops/{id}/departures endpoint.

Usage:
    python collect_uk_schedules_simple.py

Output:
    - dataset/raw/uk_schedules.jsonl (raw departures)
    - dataset/processed/uk_schedule_summary.json (stats)
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime, date, timedelta
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Paths
DATASET_DIR = Path(__file__).parent / "dataset"
RAW_DIR = DATASET_DIR / "raw"
PROCESSED_DIR = DATASET_DIR / "processed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# UK Stations
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

BASE_URL = "https://transit.land/api/v2/rest"


def fetch_departures(station_id: str, api_key: str, service_date: str = None) -> dict:
    """Fetch departures for a station."""
    if not service_date:
        service_date = date.today().isoformat()
    
    url = f"{BASE_URL}/stops/{station_id}/departures"
    params = {
        "date": service_date,
    }
    headers = {"apikey": api_key}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"  ❌ HTTP Error {e.response.status_code}: {e}")
        return {"stops": []}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {"stops": []}


def main():
    print("\n" + "="*70)
    print("  🚆 UK SCHEDULE COLLECTION (SIMPLIFIED)")
    print("="*70)
    
    # Check API key
    api_key = os.getenv("TRANSITLAND_API_KEY")
    if not api_key:
        print("❌ TRANSITLAND_API_KEY not found")
        return 1
    
    print(f"✅ API Key: {api_key[:10]}...")
    
    # Service date (today)
    service_date = date.today().isoformat()
    print(f"📅 Service Date: {service_date}")
    
    # Output file
    output_file = RAW_DIR / "uk_schedules.jsonl"
    print(f"📝 Output: {output_file}")
    
    # Collect departures
    print(f"\n🚀 Collecting departures from {len(UK_STATIONS)} stations...")
    
    all_stats = {
        "collection_date": datetime.now().isoformat(),
        "service_date": service_date,
        "stations_requested": len(UK_STATIONS),
        "stations_successful": 0,
        "total_departures": 0,
        "stations": {}
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for station_name, station_id in tqdm(UK_STATIONS.items(), desc="Stations"):
            print(f"\n📍 {station_name} ({station_id})")
            
            data = fetch_departures(station_id, api_key, service_date)
            
            # Check if we got data
            stops = data.get("stops", [])
            if not stops:
                print(f"  ⚠️ No data returned")
                all_stats["stations"][station_name] = {
                    "station_id": station_id,
                    "departures": 0,
                    "status": "no_data"
                }
                continue
            
            # Count departures
            departure_count = 0
            for stop in stops:
                departures = stop.get("departures", [])
                departure_count += len(departures)
                
                # Save each stop's data
                record = {
                    "station_name": station_name,
                    "station_id": station_id,
                    "service_date": service_date,
                    "collection_timestamp": datetime.now().isoformat(),
                    "stop": stop
                }
                f.write(json.dumps(record) + "\n")
            
            print(f"  ✅ {departure_count} departures")
            
            all_stats["stations"][station_name] = {
                "station_id": station_id,
                "departures": departure_count,
                "status": "success"
            }
            all_stats["total_departures"] += departure_count
            all_stats["stations_successful"] += 1
    
    # Save summary
    summary_file = PROCESSED_DIR / "uk_schedule_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(all_stats, f, indent=2)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 COLLECTION SUMMARY")
    print("="*70)
    print(f"✅ Successful: {all_stats['stations_successful']}/{all_stats['stations_requested']}")
    print(f"🚂 Total Departures: {all_stats['total_departures']:,}")
    print(f"📝 Output: {output_file}")
    print(f"📊 Summary: {summary_file}")
    
    if all_stats['total_departures'] == 0:
        print("\n⚠️ No departures collected. This might mean:")
        print("   1. The API endpoint has changed")
        print("   2. These station IDs are invalid")
        print("   3. No service on the selected date")
        return 1
    
    print("\n✅ Collection complete!")
    return 0


if __name__ == "__main__":
    exit(main())
