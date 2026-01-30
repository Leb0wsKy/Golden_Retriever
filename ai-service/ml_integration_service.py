"""
Integration Service: Connect ML Predictions to Digital Twin
Periodically analyzes network state and generates pre-conflict alerts
"""

import requests
import time
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service URLs
BACKEND_URL = "http://localhost:5000"
DIGITAL_TWIN_URL = "http://localhost:5002"
ML_API_URL = "http://localhost:5003"


def fetch_active_trains():
    """Fetch current active trains from backend"""
    try:
        response = requests.get(f"{BACKEND_URL}/api/trains/active")
        if response.status_code == 200:
            return response.json().get('trains', [])
        return []
    except Exception as e:
        print(f"Error fetching trains: {e}")
        return []


def group_trains_by_network(trains):
    """Group trains by network_id"""
    networks = {}
    for train in trains:
        network_id = train.get('network_id', train.get('operator', 'unknown'))
        if network_id not in networks:
            networks[network_id] = []
        networks[network_id].append(train)
    return networks


def predict_network_conflict(network_id, trains):
    """Call ML API to predict network conflict"""
    try:
        payload = {
            'network_id': network_id,
            'trains': trains
        }
        
        response = requests.post(
            f"{ML_API_URL}/api/ml/analyze-network",
            json=payload,
            timeout=5
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"ML API error for {network_id}: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error calling ML API for {network_id}: {e}")
        return None


def create_pre_conflict_alert(network_id, prediction, train_count):
    """Create pre-conflict alert in Digital Twin using ML prediction endpoint"""
    try:
        if not prediction['prediction']['is_conflict']:
            return False
        
        pred = prediction['prediction']
        alert = prediction['alert']
        metrics = prediction.get('network_metrics', {})
        
        # Prepare data for Digital Twin ML endpoint
        alert_data = {
            'network_id': network_id,
            'train_count': train_count,
            'conflict_probability': pred['probability'],
            'confidence': pred['confidence'],
            'risk_level': pred['risk_level'],
            'severity': alert['severity'],
            'contributing_factors': alert['contributing_factors'],
            'recommended_action': alert['recommended_action'],
            'alert_message': alert['alert_message'],
            'avg_speed': metrics.get('avg_speed'),
            'avg_delay': metrics.get('avg_delay'),
            'anomaly_ratio': metrics.get('anomaly_ratio'),
            'delayed_ratio': metrics.get('delayed_ratio'),
            'source': 'ml_prediction',
            'timestamp': datetime.now().isoformat()
        }
        
        # Send to Digital Twin ML predictions endpoint
        response = requests.post(
            f"{DIGITAL_TWIN_URL}/api/ml/predictions",
            json=alert_data,
            timeout=5
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            logger.info(f"✓ ML prediction stored in Qdrant for {network_id} (ID: {result.get('prediction_id')})")
            return True
        else:
            logger.error(f"✗ Failed to store ML prediction for {network_id}: {response.status_code}")
            logger.error(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating ML prediction alert for {network_id}: {e}")
        return False


def monitor_networks():
    """Main monitoring loop"""
    print("\n" + "="*60)
    print("ML PREDICTION INTEGRATION SERVICE")
    print("="*60)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nMonitoring networks for conflict prediction...")
    print("Press Ctrl+C to stop\n")
    
    iteration = 0
    
    try:
        while True:
            iteration += 1
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iteration {iteration}")
            print("-" * 40)
            
            # Fetch active trains
            trains = fetch_active_trains()
            if not trains:
                print("No active trains found")
                time.sleep(30)
                continue
            
            print(f"Found {len(trains)} active trains")
            
            # Group by network
            networks = group_trains_by_network(trains)
            print(f"Analyzing {len(networks)} networks")
            
            alerts_created = 0
            
            # Analyze each network
            for network_id, network_trains in networks.items():
                print(f"\n  Network: {network_id} ({len(network_trains)} trains)")
                
                # Predict conflict
                prediction = predict_network_conflict(network_id, network_trains)
                
                if prediction and prediction.get('success'):
                    pred_data = prediction['prediction']
                    print(f"    Probability: {pred_data['probability']:.2%}")
                    print(f"    Risk Level: {pred_data['risk_level']}")
                    
                    # Create alert if conflict predicted
                    if pred_data['is_conflict']:
                        print(f"    ⚠️  CONFLICT PREDICTED!")
                        if create_pre_conflict_alert(network_id, prediction, len(network_trains)):
                            alerts_created += 1
                else:
                    print(f"    Failed to get prediction")
            
            print(f"\n✓ Created {alerts_created} pre-conflict alerts")
            print(f"Next check in 30 seconds...")
            
            # Wait before next iteration
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user")
    except Exception as e:
        print(f"\n\nError in monitoring loop: {e}")


if __name__ == "__main__":
    # Check ML API availability
    try:
        response = requests.get(f"{ML_API_URL}/api/ml/health", timeout=2)
        if response.status_code == 200:
            print("✓ ML API is available")
        else:
            print("✗ ML API not responding correctly")
            exit(1)
    except Exception as e:
        print(f"✗ Cannot connect to ML API at {ML_API_URL}")
        print(f"   Error: {e}")
        print("\n   Please start the ML API first:")
        print("   python ml_prediction_api.py")
        exit(1)
    
    monitor_networks()
