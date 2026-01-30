"""
Test ML Prediction API
Quick test to verify the model integration works
"""

import requests
import json

ML_API_URL = "http://localhost:5003"


def test_health():
    """Test health endpoint"""
    print("\n1. Testing Health Endpoint...")
    print("-" * 40)
    
    response = requests.get(f"{ML_API_URL}/api/ml/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_model_info():
    """Test model info endpoint"""
    print("\n2. Testing Model Info Endpoint...")
    print("-" * 40)
    
    response = requests.get(f"{ML_API_URL}/api/ml/model-info")
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if data.get('success'):
        print(f"Model Type: {data['model']['type']}")
        print(f"Features: {data['model']['feature_count']}")
        print(f"Test Accuracy: {data['model']['performance']['test_accuracy']:.2%}")
        print(f"Test F1: {data['model']['performance']['test_f1']:.4f}")


def test_single_prediction():
    """Test single network prediction"""
    print("\n3. Testing Single Prediction...")
    print("-" * 40)
    
    # Sample network with HIGH RISK characteristics
    high_risk_network = {
        "network_id": "FS",
        "train_count": 150,
        "avg_speed": 42.5,
        "std_speed": 18.2,
        "min_speed": 25.0,
        "speed_variance": 331.24,
        "slow_train_ratio": 0.45,
        "fast_train_ratio": 0.05,
        "avg_delay": 2.8,
        "max_delay": 9.0,
        "std_delay": 2.5,
        "delayed_train_count": 45,
        "delayed_ratio": 0.30,
        "severe_delay_count": 12,
        "delayed_status_count": 40,
        "status_delay_mismatch": 5,
        "anomaly_count": 52,
        "anomaly_ratio": 0.35,
        "avg_nearest_distance": 0.8,
        "min_nearest_distance": 0.2,
        "crowded_locations": 25,
        "avg_nearby_trains": 35.5,
        "high_density_slow_speed": 30,
        "delayed_with_high_proximity": 18,
        "speed_delay_correlation": -0.3,
        "location_spread": 0.15,
        "avg_speed_trend": 43.0,
        "avg_delay_trend": 2.5,
        "anomaly_ratio_trend": 0.32,
        "delayed_ratio_trend": 0.28
    }
    
    response = requests.post(
        f"{ML_API_URL}/api/ml/predict-network-conflict",
        json=high_risk_network
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if data.get('success'):
        pred = data['prediction']
        print(f"\n🚨 Prediction Results:")
        print(f"  Conflict Predicted: {pred['is_conflict']}")
        print(f"  Probability: {pred['probability']:.2%}")
        print(f"  Confidence: {pred['confidence']:.2%}")
        print(f"  Risk Level: {pred['risk_level']}")


def test_analyze_network():
    """Test network analysis with train data"""
    print("\n4. Testing Network Analysis...")
    print("-" * 40)
    
    # Sample trains data (simulating high-risk scenario)
    sample_trains = []
    for i in range(50):
        sample_trains.append({
            "train_id": f"train-{i+1000}",
            "speed": 45 + (i % 30),
            "delay": 2 if i % 3 == 0 else 0,
            "is_anomaly": i % 4 == 0,
            "has_conflict": True,
            "nearby_trains": 20 + (i % 15),
            "nearest_train_km": 0.5 + (i % 5) * 0.2,
            "status": "delayed" if i % 5 == 0 else "on-time"
        })
    
    payload = {
        "network_id": "FS",
        "trains": sample_trains
    }
    
    response = requests.post(
        f"{ML_API_URL}/api/ml/analyze-network",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    if data.get('success'):
        print(f"\nNetwork: {data['network_id']}")
        print(f"Trains: {data['train_count']}")
        
        pred = data['prediction']
        print(f"\n📊 Prediction:")
        print(f"  Conflict: {pred['is_conflict']}")
        print(f"  Probability: {pred['probability']:.2%}")
        print(f"  Risk Level: {pred['risk_level']}")
        
        alert = data['alert']
        print(f"\n⚠️  Alert Information:")
        print(f"  Should Alert: {alert['should_alert']}")
        print(f"  Severity: {alert['severity']}")
        print(f"  Action: {alert['recommended_action']}")
        
        if alert['contributing_factors']:
            print(f"\n  Contributing Factors:")
            for factor in alert['contributing_factors']:
                print(f"    • {factor}")


def main():
    print("="*60)
    print("ML PREDICTION API - INTEGRATION TEST")
    print("="*60)
    
    try:
        # Test all endpoints
        test_health()
        test_model_info()
        test_single_prediction()
        test_analyze_network()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to ML API")
        print("\nPlease start the ML API first:")
        print("  python ml_prediction_api.py")
        print("\nOr run:")
        print("  .\\start-ml-api.bat")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")


if __name__ == "__main__":
    main()
