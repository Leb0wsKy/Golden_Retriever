"""
Network Conflict Prediction API
Flask endpoint to serve ML predictions for the Golden Retriever platform
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from conflict_prediction_model.predict import ConflictPredictor
import pandas as pd
import numpy as np
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Initialize predictor once at startup
print("Loading conflict prediction model...")
try:
    predictor = ConflictPredictor(model_dir='conflict_prediction_model')
    print("✓ Model loaded successfully!")
except Exception as e:
    print(f"✗ Failed to load model: {e}")
    predictor = None


@app.route('/api/ml/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': predictor is not None,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/ml/predict-network-conflict', methods=['POST'])
def predict_network_conflict():
    """
    Predict conflict probability for a network snapshot
    
    Expected input format:
    {
        "network_id": "FS",
        "train_count": 150,
        "avg_speed": 52.5,
        "std_speed": 15.2,
        "avg_delay": 1.8,
        "anomaly_count": 45,
        "anomaly_ratio": 0.30,
        ... (all required features)
    }
    """
    if not predictor:
        return jsonify({'error': 'Model not loaded'}), 500
    
    try:
        data = request.json
        
        # Make prediction
        result = predictor.predict_single(**data)
        
        # Add metadata
        response = {
            'success': True,
            'prediction': {
                'is_conflict': result['prediction'],
                'probability': result['conflict_probability'],
                'confidence': result['confidence'],
                'risk_level': result['risk_level']
            },
            'network_id': data.get('network_id', 'unknown'),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response)
    
    except KeyError as e:
        return jsonify({
            'success': False,
            'error': f'Missing required feature: {str(e)}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ml/predict-batch', methods=['POST'])
def predict_batch():
    """
    Predict conflicts for multiple network snapshots
    
    Expected input format:
    {
        "snapshots": [
            {network snapshot 1},
            {network snapshot 2},
            ...
        ]
    }
    """
    if not predictor:
        return jsonify({'error': 'Model not loaded'}), 500
    
    try:
        data = request.json
        snapshots = data.get('snapshots', [])
        
        if not snapshots:
            return jsonify({
                'success': False,
                'error': 'No snapshots provided'
            }), 400
        
        # Convert to DataFrame
        df = pd.DataFrame(snapshots)
        
        # Make predictions
        results = predictor.predict(df)
        
        # Format response
        predictions = []
        for i, result in enumerate(results):
            predictions.append({
                'network_id': snapshots[i].get('network_id', 'unknown'),
                'snapshot_index': i,
                'is_conflict': result['prediction'],
                'probability': result['conflict_probability'],
                'confidence': result['confidence'],
                'risk_level': result['risk_level']
            })
        
        return jsonify({
            'success': True,
            'count': len(predictions),
            'predictions': predictions,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/ml/analyze-network', methods=['POST'])
def analyze_network():
    """
    Analyze current network state from live train data
    Aggregates train-level data to network-level and predicts conflicts
    
    Expected input format:
    {
        "network_id": "FS",
        "trains": [
            {
                "train_id": "train-123",
                "speed": 55.0,
                "delay": 2.0,
                "is_anomaly": false,
                "has_conflict": true,
                "nearby_trains": 15,
                "nearest_train_km": 0.5,
                ...
            },
            ...
        ]
    }
    """
    if not predictor:
        return jsonify({'error': 'Model not loaded'}), 500
    
    try:
        data = request.json
        network_id = data.get('network_id')
        trains = data.get('trains', [])
        
        if not trains:
            return jsonify({
                'success': False,
                'error': 'No train data provided'
            }), 400
        
        # Aggregate to network level
        df = pd.DataFrame(trains)
        network_features = aggregate_train_data_to_network(df)
        network_features['network_id'] = network_id
        
        # Predict
        result = predictor.predict_single(**network_features)
        
        # Determine alert level
        alert_info = generate_alert_info(result, network_features)
        
        response = {
            'success': True,
            'network_id': network_id,
            'train_count': len(trains),
            'prediction': {
                'is_conflict': result['prediction'],
                'probability': result['conflict_probability'],
                'confidence': result['confidence'],
                'risk_level': result['risk_level']
            },
            'alert': alert_info,
            'network_metrics': network_features,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def aggregate_train_data_to_network(train_df):
    """Aggregate train-level data to network-level features"""
    train_count = len(train_df)
    
    # Speed metrics
    avg_speed = train_df['speed'].mean() if 'speed' in train_df else 0
    std_speed = train_df['speed'].std() if 'speed' in train_df else 0
    min_speed = train_df['speed'].min() if 'speed' in train_df else 0
    speed_variance = train_df['speed'].var() if 'speed' in train_df else 0
    slow_train_ratio = (train_df['speed'] < 40).sum() / train_count if 'speed' in train_df else 0
    fast_train_ratio = (train_df['speed'] > 70).sum() / train_count if 'speed' in train_df else 0
    
    # Delay metrics
    avg_delay = train_df['delay'].mean() if 'delay' in train_df else 0
    max_delay = train_df['delay'].max() if 'delay' in train_df else 0
    std_delay = train_df['delay'].std() if 'delay' in train_df else 0
    delayed_train_count = (train_df['delay'] > 0).sum() if 'delay' in train_df else 0
    delayed_ratio = delayed_train_count / train_count
    severe_delay_count = (train_df['delay'] > 5).sum() if 'delay' in train_df else 0
    
    # Status metrics
    delayed_status_count = (train_df['status'] == 'delayed').sum() if 'status' in train_df else 0
    status_delay_mismatch = abs(delayed_status_count - delayed_train_count)
    
    # Anomaly metrics
    anomaly_count = train_df['is_anomaly'].sum() if 'is_anomaly' in train_df else 0
    anomaly_ratio = anomaly_count / train_count
    
    # Proximity metrics
    avg_nearest_distance = train_df['nearest_train_km'].mean() if 'nearest_train_km' in train_df else 0
    min_nearest_distance = train_df['nearest_train_km'].min() if 'nearest_train_km' in train_df else 0
    crowded_locations = (train_df['nearby_trains'] > 20).sum() if 'nearby_trains' in train_df else 0
    avg_nearby_trains = train_df['nearby_trains'].mean() if 'nearby_trains' in train_df else 0
    
    # Interaction features
    high_density_slow_speed = 0
    delayed_with_high_proximity = 0
    if 'nearby_trains' in train_df and 'speed' in train_df:
        high_density_slow_speed = ((train_df['nearby_trains'] > 20) & (train_df['speed'] < 45)).sum()
    if 'delay' in train_df and 'nearby_trains' in train_df:
        delayed_with_high_proximity = ((train_df['delay'] > 3) & (train_df['nearby_trains'] > 15)).sum()
    
    speed_delay_correlation = 0
    if 'speed' in train_df and 'delay' in train_df and len(train_df) > 1:
        speed_delay_correlation = train_df[['speed', 'delay']].corr().iloc[0, 1]
        if np.isnan(speed_delay_correlation):
            speed_delay_correlation = 0
    
    # Spatial features
    location_spread = 0
    if 'lat' in train_df and 'lng' in train_df and len(train_df) > 1:
        location_spread = np.sqrt(train_df['lat'].var() + train_df['lng'].var())
    
    # Temporal trends (use zeros if not available)
    avg_speed_trend = avg_speed
    avg_delay_trend = avg_delay
    anomaly_ratio_trend = anomaly_ratio
    delayed_ratio_trend = delayed_ratio
    
    return {
        'train_count': train_count,
        'avg_speed': avg_speed,
        'std_speed': std_speed,
        'min_speed': min_speed,
        'speed_variance': speed_variance,
        'slow_train_ratio': slow_train_ratio,
        'fast_train_ratio': fast_train_ratio,
        'avg_delay': avg_delay,
        'max_delay': max_delay,
        'std_delay': std_delay,
        'delayed_train_count': delayed_train_count,
        'delayed_ratio': delayed_ratio,
        'severe_delay_count': severe_delay_count,
        'delayed_status_count': delayed_status_count,
        'status_delay_mismatch': status_delay_mismatch,
        'anomaly_count': anomaly_count,
        'anomaly_ratio': anomaly_ratio,
        'avg_nearest_distance': avg_nearest_distance,
        'min_nearest_distance': min_nearest_distance,
        'crowded_locations': crowded_locations,
        'avg_nearby_trains': avg_nearby_trains,
        'high_density_slow_speed': high_density_slow_speed,
        'delayed_with_high_proximity': delayed_with_high_proximity,
        'speed_delay_correlation': speed_delay_correlation,
        'location_spread': location_spread,
        'avg_speed_trend': avg_speed_trend,
        'avg_delay_trend': avg_delay_trend,
        'anomaly_ratio_trend': anomaly_ratio_trend,
        'delayed_ratio_trend': delayed_ratio_trend
    }


def generate_alert_info(prediction_result, network_features):
    """Generate alert information based on prediction"""
    probability = prediction_result['conflict_probability']
    risk_level = prediction_result['risk_level']
    
    # Determine severity
    if probability >= 0.8:
        severity = 'critical'
        action = 'IMMEDIATE ACTION REQUIRED'
    elif probability >= 0.6:
        severity = 'high'
        action = 'Monitor closely and prepare intervention'
    elif probability >= 0.4:
        severity = 'medium'
        action = 'Increased monitoring recommended'
    else:
        severity = 'low'
        action = 'Normal operations'
    
    # Identify contributing factors
    factors = []
    if network_features.get('anomaly_ratio', 0) > 0.3:
        factors.append(f"High anomaly rate ({network_features['anomaly_ratio']:.1%})")
    if network_features.get('delayed_ratio', 0) > 0.2:
        factors.append(f"Significant delays ({network_features['delayed_ratio']:.1%} of trains)")
    if network_features.get('avg_speed', 0) < 45:
        factors.append(f"Below-normal speeds (avg {network_features['avg_speed']:.1f} km/h)")
    if network_features.get('train_count', 0) > 100:
        factors.append(f"High network density ({network_features['train_count']} trains)")
    
    return {
        'should_alert': probability > 0.4,
        'severity': severity,
        'risk_level': risk_level,
        'recommended_action': action,
        'contributing_factors': factors,
        'alert_message': f"{risk_level.upper()} risk of network conflict detected"
    }


@app.route('/api/ml/model-info', methods=['GET'])
def model_info():
    """Get model information and metadata"""
    if not predictor:
        return jsonify({'error': 'Model not loaded'}), 500
    
    return jsonify({
        'success': True,
        'model': {
            'type': predictor.metrics.get('model_type', 'Unknown'),
            'features': predictor.feature_names,
            'feature_count': len(predictor.feature_names),
            'training_date': predictor.metrics.get('training_date', 'Unknown'),
            'performance': {
                'test_accuracy': predictor.metrics.get('test_accuracy', 0),
                'test_f1': predictor.metrics.get('test_f1', 0),
                'test_precision': predictor.metrics.get('test_precision', 0),
                'test_recall': predictor.metrics.get('test_recall', 0)
            }
        }
    })


if __name__ == '__main__':
    print("\n" + "="*60)
    print("NETWORK CONFLICT PREDICTION API")
    print("="*60)
    print("\nEndpoints:")
    print("  GET  /api/ml/health                  - Health check")
    print("  GET  /api/ml/model-info              - Model metadata")
    print("  POST /api/ml/predict-network-conflict - Single prediction")
    print("  POST /api/ml/analyze-network         - Analyze live network")
    print("  POST /api/ml/predict-batch           - Batch predictions")
    print("\n" + "="*60)
    
    app.run(host='0.0.0.0', port=5003, debug=True)
