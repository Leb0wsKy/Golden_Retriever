# Network Conflict Prediction Model

Machine learning model for predicting train network conflicts using historical network data.

## Overview

This model predicts network-level conflicts by analyzing network metrics such as:
- Train counts
- Anomaly counts
- Conflict counts  
- Delay patterns
- Speed metrics
- Network congestion indicators

## Files

### Core Scripts

- **`train_model.py`** - Train the conflict prediction model
  - Loads and preprocesses network_conflicts_minute.csv
  - Trains Random Forest or Gradient Boosting classifier
  - Performs hyperparameter optimization (optional)
  - Evaluates model performance
  - Saves trained model artifacts

- **`predict.py`** - Make predictions using trained model
  - Load saved model and make predictions on new data
  - Support for single predictions, batch CSV predictions
  - Returns conflict probability and risk level
  - Provides feature importance explanations

- **`evaluate.py`** - Comprehensive model evaluation
  - Detailed metrics (accuracy, precision, recall, F1, ROC-AUC)
  - Confusion matrix visualization
  - ROC and Precision-Recall curves
  - Feature importance analysis
  - Error analysis (false positives/negatives)
  - Probability distribution plots

### Model Artifacts (Generated)

- **`conflict_predictor.pkl`** - Trained model
- **`scaler.pkl`** - Feature scaler for normalization
- **`feature_names.json`** - List of feature names
- **`model_metrics.json`** - Model performance metrics
- **`feature_importance.csv`** - Feature importance rankings

### Visualizations (Generated)

- **`confusion_matrix.png`** - Confusion matrix heatmap
- **`roc_curve.png`** - ROC curve with AUC score
- **`precision_recall_curve.png`** - Precision-Recall curve
- **`feature_importance.png`** - Top feature importance bar chart
- **`probability_distribution.png`** - Distribution of predicted probabilities

## Installation

```bash
cd ai-service/conflict_prediction_model
pip install -r requirements.txt
```

## Usage

### 1. Train the Model

```bash
python train_model.py
```

This will:
- Load the dataset from `../dataset/processed/network_conflicts_minute.csv`
- Train a Random Forest classifier
- Evaluate performance on test set
- Save model artifacts

**Configuration Options** (edit in `train_model.py`):
- `MODEL_TYPE`: 'random_forest' or 'gradient_boosting'
- `OPTIMIZE_HYPERPARAMS`: True for hyperparameter tuning (slower but better)

### 2. Make Predictions

#### Single Prediction
```python
from predict import ConflictPredictor

predictor = ConflictPredictor()

result = predictor.predict_single(
    train_count=150,
    anomaly_count=45,
    conflict_count=120,
    delay_high_count=20,
    avg_delay=1.2,
    avg_speed=54.5,
    anomaly_ratio=0.30,
    conflict_ratio=0.80,
    proximity_conflict_count=10,
    congestion_conflict_count=110,
    network_congestion_conflict=True,
    network_proximity_conflict=False,
    network_delay_conflict=True,
    network_anomaly_spike=True
)

print(f"Conflict Predicted: {result['prediction']}")
print(f"Probability: {result['conflict_probability']:.4f}")
print(f"Risk Level: {result['risk_level']}")
```

#### Batch Prediction from CSV
```python
from predict import ConflictPredictor

predictor = ConflictPredictor()
df = predictor.predict_from_csv(
    'data.csv', 
    output_path='predictions.csv'
)
```

#### Command Line
```bash
python predict.py
```

### 3. Evaluate Model

```bash
python evaluate.py
```

This generates:
- Detailed classification metrics
- Confusion matrix
- ROC and Precision-Recall curves
- Feature importance charts
- Error analysis

## Model Features

The model uses 14 input features:

### Numeric Features
1. **train_count** - Number of trains in network
2. **anomaly_count** - Number of anomalous trains
3. **conflict_count** - Number of conflicts detected
4. **delay_high_count** - Number of significantly delayed trains
5. **avg_delay** - Average delay across network (minutes)
6. **avg_speed** - Average speed across network (km/h)
7. **anomaly_ratio** - Ratio of anomalous trains
8. **conflict_ratio** - Ratio of trains in conflict
9. **proximity_conflict_count** - Proximity-based conflicts
10. **congestion_conflict_count** - Congestion-based conflicts

### Boolean Features
11. **network_congestion_conflict** - Network-level congestion detected
12. **network_proximity_conflict** - Network-level proximity issues
13. **network_delay_conflict** - Network-level delay issues
14. **network_anomaly_spike** - Spike in anomalies detected

### Target Variable
- **is_network_conflict** - Whether network conflict occurred (True/False)

## Model Performance

Expected performance metrics (after training):
- **Accuracy**: ~95-98%
- **Precision**: ~92-96%
- **Recall**: ~94-98%
- **F1-Score**: ~93-97%
- **ROC-AUC**: ~0.97-0.99

## Risk Levels

Predictions include risk level categorization:
- **CRITICAL** - Probability ≥ 0.8
- **HIGH** - Probability ≥ 0.6
- **MEDIUM** - Probability ≥ 0.4
- **LOW** - Probability ≥ 0.2
- **MINIMAL** - Probability < 0.2

## API Integration

To integrate with the main application:

```python
from conflict_prediction_model.predict import ConflictPredictor

# Initialize once
predictor = ConflictPredictor()

# Make predictions
def predict_network_conflict(network_data):
    """
    Predict conflict for network snapshot
    
    Args:
        network_data: dict with required features
    
    Returns:
        dict with prediction, probability, and risk level
    """
    return predictor.predict_single(**network_data)
```

## Dataset

- **Source**: `ai-service/dataset/processed/network_conflicts_minute.csv`
- **Size**: ~1,151 network snapshots
- **Temporal**: Minute-level aggregations
- **Conflict Rate**: ~70-80% (imbalanced dataset handled with class weights)

## Model Architecture

### Random Forest (Default)
- **Estimators**: 200 trees
- **Max Depth**: 20
- **Min Samples Split**: 5
- **Min Samples Leaf**: 2
- **Class Weight**: Balanced (handles class imbalance)

### Gradient Boosting (Alternative)
- **Estimators**: 200
- **Learning Rate**: 0.1
- **Max Depth**: 5
- **Subsample**: 0.8

## Feature Engineering

- **Standardization**: StandardScaler for all numeric features
- **Boolean Encoding**: Boolean flags converted to 0/1
- **Missing Values**: Filled with 0 (rare in this dataset)

## Troubleshooting

### Model not found
```
RuntimeError: Failed to load model artifacts
```
**Solution**: Run `train_model.py` first to generate model files

### Missing features error
```
ValueError: Missing required features
```
**Solution**: Ensure input data contains all 14 required features

### Low performance
- Try enabling hyperparameter optimization: `OPTIMIZE_HYPERPARAMS = True`
- Consider using Gradient Boosting: `MODEL_TYPE = 'gradient_boosting'`
- Check dataset for data quality issues

## Future Enhancements

- [ ] Add LSTM/GRU for temporal sequence modeling
- [ ] Implement online learning for model updates
- [ ] Add SHAP values for better explainability
- [ ] Create real-time prediction API endpoint
- [ ] Add cross-validation with time-based splits
- [ ] Implement ensemble of multiple models
- [ ] Add anomaly detection for input validation

## 🚀 Production Integration

The model is integrated into the Golden Retriever platform through:

### 1. ML Prediction API (Port 5003)
```bash
cd .. # Go to ai-service directory
python ml_prediction_api.py
```
Serves the model via REST API with endpoints for:
- Real-time conflict prediction
- Network analysis from live train data
- Batch predictions

### 2. ML Integration Service
```bash
python ml_integration_service.py
```
Monitors networks every 30 seconds and automatically:
- Fetches active trains
- Predicts conflicts using ML model
- Creates pre-conflict alerts in Digital Twin
- Displays warnings in frontend dashboard

### 3. Quick Start Scripts
```bash
# From project root
.\start-ml-api.bat           # Start ML API
.\start-ml-integration.bat   # Start monitoring service
```

### Architecture Flow
```
Backend → ML Integration → ML API → Pre-Conflict Alerts → Frontend
```

See [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) for complete details.

---

## License

Part of the Golden Retriever Rail Network Monitoring Platform
