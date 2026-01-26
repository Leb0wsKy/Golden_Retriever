from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import time
import threading
from datetime import datetime
from collections import deque
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Simulation state
simulation_state = {
    'running': False,
    'parameters': {
        'dataRate': 50,
        'noiseLevel': 0.1,
        'scenario': 'normal'
    },
    'data': deque(maxlen=100),
    'metrics': {
        'accuracy': 0.95,
        'latency': 15.0,
        'throughput': 500.0
    }
}

simulation_thread = None

def generate_simulation_data():
    """Generate simulated data based on parameters"""
    params = simulation_state['parameters']
    scenario = params['scenario']
    
    # Base values
    base_accuracy = 0.95
    base_latency = 15.0
    base_throughput = 500.0
    
    # Scenario adjustments
    if scenario == 'high_load':
        base_latency *= 1.5
        base_accuracy *= 0.95
        base_throughput *= 1.3
    elif scenario == 'stress_test':
        base_latency *= 2.0
        base_accuracy *= 0.85
        base_throughput *= 1.5
    elif scenario == 'failure':
        base_latency *= 3.0
        base_accuracy *= 0.6
        base_throughput *= 0.5
    
    # Add noise
    noise_level = params['noiseLevel']
    accuracy = base_accuracy + np.random.normal(0, noise_level * 0.1)
    latency = base_latency + np.random.normal(0, noise_level * 10)
    throughput = base_throughput + np.random.normal(0, noise_level * 100)
    
    # Clamp values
    accuracy = max(0.0, min(1.0, accuracy))
    latency = max(1.0, latency)
    throughput = max(0.0, throughput)
    
    return {
        'timestamp': datetime.now().isoformat(),
        'accuracy': accuracy,
        'latency': latency,
        'throughput': throughput,
        'metrics': {
            'accuracy': accuracy,
            'latency': latency,
            'throughput': throughput
        }
    }

def simulation_loop():
    """Main simulation loop"""
    while simulation_state['running']:
        data = generate_simulation_data()
        simulation_state['data'].append(data)
        simulation_state['metrics'] = data['metrics']
        
        # Sleep based on data rate
        sleep_time = 1.0 / simulation_state['parameters']['dataRate']
        time.sleep(sleep_time)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'service': 'Digital Twin Simulation',
        'simulation_running': simulation_state['running']
    })

@app.route('/data', methods=['GET'])
def get_data():
    """Get current simulation data"""
    if simulation_state['running'] and len(simulation_state['data']) > 0:
        return jsonify(simulation_state['data'][-1])
    else:
        return jsonify(generate_simulation_data())

@app.route('/history', methods=['GET'])
def get_history():
    """Get simulation history"""
    limit = request.args.get('limit', 50, type=int)
    data_list = list(simulation_state['data'])
    return jsonify({
        'data': data_list[-limit:],
        'count': len(data_list)
    })

@app.route('/start', methods=['POST'])
def start_simulation():
    """Start the simulation"""
    global simulation_thread
    
    try:
        data = request.json or {}
        
        # Update parameters
        if 'dataRate' in data:
            simulation_state['parameters']['dataRate'] = data['dataRate']
        if 'noiseLevel' in data:
            simulation_state['parameters']['noiseLevel'] = data['noiseLevel']
        if 'scenario' in data:
            simulation_state['parameters']['scenario'] = data['scenario']
        
        if not simulation_state['running']:
            simulation_state['running'] = True
            simulation_thread = threading.Thread(target=simulation_loop, daemon=True)
            simulation_thread.start()
            
        return jsonify({
            'success': True,
            'message': 'Simulation started',
            'parameters': simulation_state['parameters']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stop', methods=['POST'])
def stop_simulation():
    """Stop the simulation"""
    try:
        simulation_state['running'] = False
        return jsonify({
            'success': True,
            'message': 'Simulation stopped'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reset', methods=['POST'])
def reset_simulation():
    """Reset the simulation"""
    try:
        simulation_state['running'] = False
        simulation_state['data'].clear()
        simulation_state['parameters'] = {
            'dataRate': 50,
            'noiseLevel': 0.1,
            'scenario': 'normal'
        }
        simulation_state['metrics'] = {
            'accuracy': 0.95,
            'latency': 15.0,
            'throughput': 500.0
        }
        return jsonify({
            'success': True,
            'message': 'Simulation reset'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/parameters', methods=['GET'])
def get_parameters():
    """Get current simulation parameters"""
    return jsonify(simulation_state['parameters'])

@app.route('/parameters', methods=['POST'])
def update_parameters():
    """Update simulation parameters"""
    try:
        data = request.json
        simulation_state['parameters'].update(data)
        return jsonify({
            'success': True,
            'parameters': simulation_state['parameters']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Get current metrics"""
    return jsonify(simulation_state['metrics'])

@app.route('/scenarios', methods=['GET'])
def get_scenarios():
    """Get available simulation scenarios"""
    scenarios = [
        {
            'id': 'normal',
            'name': 'Normal Operation',
            'description': 'Standard operating conditions'
        },
        {
            'id': 'high_load',
            'name': 'High Load',
            'description': 'Increased traffic and workload'
        },
        {
            'id': 'stress_test',
            'name': 'Stress Test',
            'description': 'Maximum capacity testing'
        },
        {
            'id': 'failure',
            'name': 'Failure Scenario',
            'description': 'Simulated system failures'
        }
    ]
    return jsonify(scenarios)

@app.route('/predict', methods=['POST'])
def predict_performance():
    """Predict future performance based on current trends"""
    try:
        data = request.json
        horizon = data.get('horizon', 10)  # Number of future points to predict
        
        # Use recent data to predict
        if len(simulation_state['data']) < 5:
            return jsonify({'error': 'Not enough data for prediction'}), 400
        
        recent_data = list(simulation_state['data'])[-10:]
        
        # Simple linear extrapolation
        accuracies = [d['accuracy'] for d in recent_data]
        latencies = [d['latency'] for d in recent_data]
        throughputs = [d['throughput'] for d in recent_data]
        
        predictions = []
        for i in range(horizon):
            predictions.append({
                'timestamp': f'T+{i+1}',
                'accuracy': np.mean(accuracies) + np.random.normal(0, 0.02),
                'latency': np.mean(latencies) + np.random.normal(0, 2),
                'throughput': np.mean(throughputs) + np.random.normal(0, 50)
            })
        
        return jsonify({
            'predictions': predictions,
            'confidence': 0.75
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('DIGITAL_TWIN_PORT', 5002))
    print(f"Starting Digital Twin Service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
