"""
Test script: Create sample trains and trigger ML predictions
"""
import requests
import json
import time

BACKEND_URL = "http://localhost:5000"
ML_API_URL = "http://localhost:5003"

# Sample network with high conflict probability features
test_network_data = {
    "network_id": "test_network_001",
    "trains": [
        {
            "train_id": "T001",
            "line": "Central",
            "current_station": "Kings Cross",
            "delay_minutes": 15,  # High delay
            "speed_kmh": 45,
            "scheduled_arrival": "2026-01-30T22:00:00",
            "actual_arrival": "2026-01-30T22:15:00"
        },
        {
            "train_id": "T002",
            "line": "Northern",
            "current_station": "Kings Cross",
            "delay_minutes": 10,
            "speed_kmh": 40,
            "scheduled_arrival": "2026-01-30T22:05:00",
            "actual_arrival": "2026-01-30T22:15:00"
        },
        {
            "train_id": "T003",
            "line": "Piccadilly",
            "current_station": "Euston",
            "delay_minutes": 8,
            "speed_kmh": 35,
            "scheduled_arrival": "2026-01-30T22:02:00",
            "actual_arrival": "2026-01-30T22:10:00"
        },
        {
            "train_id": "T004",
            "line": "Victoria",
            "current_station": "Oxford Circus",
            "delay_minutes": 12,
            "speed_kmh": 30,
            "scheduled_arrival": "2026-01-30T22:08:00",
            "actual_arrival": "2026-01-30T22:20:00"
        }
    ]
}

print("=" * 60)
print("ML PREDICTION TEST")
print("=" * 60)
print()

# Step 1: Test ML API directly
print("1️⃣  Testing ML API directly...")
print(f"   POST {ML_API_URL}/api/ml/analyze-network")
try:
    response = requests.post(
        f"{ML_API_URL}/api/ml/analyze-network",
        json=test_network_data,
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Status: {response.status_code}")
        print(f"   📊 Prediction: {result.get('prediction')}")
        prob = result.get('probability', 0)
        if prob is not None:
            print(f"   🎯 Probability: {prob:.3f}")
        print(f"   ⚠️  Risk Level: {result.get('risk_level')}")
        if result.get('alert'):
            print(f"   🚨 Alert: {result['alert'].get('message')}")
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
print("-" * 60)
print()

# Step 2: Test Digital Twin storage
print("2️⃣  Testing Digital Twin ML prediction storage...")
print(f"   POST http://localhost:8000/api/v1/ml/predictions")

# Build prediction alert
prediction_alert = {
    "network_id": "test_network_001",
    "severity": "high",
    "risk_level": "HIGH",
    "conflict_probability": 0.75,  # Changed from 'probability' to 'conflict_probability'
    "confidence": 0.85,
    "train_count": 4,
    "contributing_factors": ["High delays", "Network congestion", "Multiple delayed trains"],
    "recommended_action": "Review schedule and consider adjusting routes",
    "alert_message": "High conflict risk detected: 4 trains with significant delays"
}

try:
    response = requests.post(
        "http://localhost:8000/api/v1/ml/predictions",
        json=prediction_alert,
        timeout=10
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Status: {response.status_code}")
        print(f"   📝 Stored: {result.get('success')}")
        print(f"   🆔 Prediction ID: {result.get('prediction_id')}")
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
print("-" * 60)
print()

# Step 3: Retrieve predictions
print("3️⃣  Retrieving ML predictions...")
print(f"   GET http://localhost:8000/api/v1/ml/predictions?limit=10")

time.sleep(1)  # Wait a bit for storage

try:
    response = requests.get(
        "http://localhost:8000/api/v1/ml/predictions?limit=10",
        timeout=10
    )
    
    if response.status_code == 200:
        predictions = response.json()
        print(f"   ✅ Status: {response.status_code}")
        print(f"   📦 Retrieved: {len(predictions)} predictions")
        
        if predictions:
            for i, pred in enumerate(predictions[:3], 1):  # Show first 3
                print(f"\n   Prediction {i}:")
                print(f"      Network: {pred.get('network_id')}")
                print(f"      Probability: {pred.get('probability'):.3f}")
                print(f"      Risk: {pred.get('risk_level')}")
                print(f"      Alert: {pred.get('alert_message')}")
        else:
            print("   ℹ️  No predictions stored yet")
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
print("-" * 60)
print()

# Step 4: Test via backend proxy
print("4️⃣  Testing via backend proxy...")
print(f"   GET {BACKEND_URL}/api/digital-twin/ml/predictions?limit=10")

try:
    response = requests.get(
        f"{BACKEND_URL}/api/digital-twin/ml/predictions?limit=10",
        timeout=10
    )
    
    if response.status_code == 200:
        predictions = response.json()
        print(f"   ✅ Status: {response.status_code}")
        print(f"   📦 Retrieved: {len(predictions)} predictions")
    else:
        print(f"   ❌ Status: {response.status_code}")
        print(f"   Error: {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

print()
print("=" * 60)
print("✅ TEST COMPLETE")
print("=" * 60)
