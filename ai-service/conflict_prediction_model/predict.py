"""
Network Conflict Prediction - Inference Module
Load trained model and make predictions on new data
"""

import pandas as pd
import numpy as np
import joblib
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


class ConflictPredictor:
    """Load model and make predictions on network data"""
    
    def __init__(self, model_dir='conflict_prediction_model'):
        """Initialize predictor by loading saved artifacts"""
        self.model_dir = model_dir
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.metrics = None
        
        self._load_artifacts()
    
    def _load_artifacts(self):
        """Load model, scaler, and metadata"""
        print(f"Loading model from '{self.model_dir}/'...")
        
        try:
            # Load model
            self.model = joblib.load(f'{self.model_dir}/conflict_predictor.pkl')
            print("  ✓ Model loaded")
            
            # Load scaler
            self.scaler = joblib.load(f'{self.model_dir}/scaler.pkl')
            print("  ✓ Scaler loaded")
            
            # Load feature names
            with open(f'{self.model_dir}/feature_names.json', 'r') as f:
                self.feature_names = json.load(f)
            print(f"  ✓ Feature names loaded ({len(self.feature_names)} features)")
            
            # Load metrics
            with open(f'{self.model_dir}/model_metrics.json', 'r') as f:
                self.metrics = json.load(f)
            print(f"  ✓ Model metrics loaded")
            print(f"\nModel Info:")
            print(f"  Type: {self.metrics.get('model_type', 'Unknown')}")
            print(f"  Test Accuracy: {self.metrics.get('test_accuracy', 0):.4f}")
            print(f"  Test F1-Score: {self.metrics.get('test_f1', 0):.4f}")
            print(f"  Training Date: {self.metrics.get('training_date', 'Unknown')}")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load model artifacts: {e}")
    
    def predict(self, data):
        """
        Make predictions on network data
        
        Args:
            data: pandas DataFrame or dict with required features
            
        Returns:
            dict with predictions and probabilities
        """
        # Convert dict to DataFrame if needed
        if isinstance(data, dict):
            data = pd.DataFrame([data])
        
        # Validate features
        missing_features = set(self.feature_names) - set(data.columns)
        if missing_features:
            raise ValueError(f"Missing required features: {missing_features}")
        
        # Extract and order features
        X = data[self.feature_names].copy()
        
        # Handle missing values
        X = X.fillna(0)
        
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        # Make predictions
        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)
        
        # Format results
        results = []
        for i in range(len(predictions)):
            results.append({
                'prediction': bool(predictions[i]),
                'conflict_probability': float(probabilities[i, 1]),
                'no_conflict_probability': float(probabilities[i, 0]),
                'confidence': float(max(probabilities[i])),
                'risk_level': self._get_risk_level(probabilities[i, 1])
            })
        
        return results if len(results) > 1 else results[0]
    
    def predict_from_csv(self, csv_path, output_path=None):
        """
        Make predictions on CSV file
        
        Args:
            csv_path: path to CSV file with network data
            output_path: optional path to save predictions
            
        Returns:
            DataFrame with predictions
        """
        print(f"\nLoading data from '{csv_path}'...")
        df = pd.read_csv(csv_path)
        print(f"  Loaded {len(df)} records")
        
        # Make predictions
        print("Making predictions...")
        results = self.predict(df)
        
        # Add predictions to dataframe
        if isinstance(results, list):
            df['predicted_conflict'] = [r['prediction'] for r in results]
            df['conflict_probability'] = [r['conflict_probability'] for r in results]
            df['confidence'] = [r['confidence'] for r in results]
            df['risk_level'] = [r['risk_level'] for r in results]
        else:
            df['predicted_conflict'] = results['prediction']
            df['conflict_probability'] = results['conflict_probability']
            df['confidence'] = results['confidence']
            df['risk_level'] = results['risk_level']
        
        # Save if output path provided
        if output_path:
            df.to_csv(output_path, index=False)
            print(f"  Predictions saved to '{output_path}'")
        
        # Display summary
        print("\nPrediction Summary:")
        print(f"  Total Records: {len(df)}")
        print(f"  Predicted Conflicts: {df['predicted_conflict'].sum()}")
        print(f"  Conflict Rate: {df['predicted_conflict'].mean():.2%}")
        print(f"\nRisk Level Distribution:")
        print(df['risk_level'].value_counts().to_string())
        
        return df
    
    def predict_single(self, **kwargs):
        """
        Make prediction for a single network snapshot
        
        Example:
            predictor.predict_single(
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
        """
        # Convert boolean strings to integers
        for key in kwargs:
            if isinstance(kwargs[key], bool):
                kwargs[key] = int(kwargs[key])
            elif isinstance(kwargs[key], str) and kwargs[key].lower() in ['true', 'false']:
                kwargs[key] = int(kwargs[key].lower() == 'true')
        
        return self.predict(kwargs)
    
    def _get_risk_level(self, probability):
        """Categorize conflict probability into risk levels"""
        if probability >= 0.8:
            return 'CRITICAL'
        elif probability >= 0.6:
            return 'HIGH'
        elif probability >= 0.4:
            return 'MEDIUM'
        elif probability >= 0.2:
            return 'LOW'
        else:
            return 'MINIMAL'
    
    def explain_prediction(self, data, top_n=5):
        """
        Explain prediction by showing feature contributions
        (Only works for tree-based models)
        """
        if not hasattr(self.model, 'feature_importances_'):
            print("Model does not support feature importance explanations")
            return None
        
        # Convert dict to DataFrame if needed
        if isinstance(data, dict):
            data = pd.DataFrame([data])
        
        # Get feature values
        X = data[self.feature_names].iloc[0]
        
        # Get feature importances
        importances = self.model.feature_importances_
        
        # Create explanation
        explanation = pd.DataFrame({
            'feature': self.feature_names,
            'value': X.values,
            'importance': importances
        }).sort_values('importance', ascending=False).head(top_n)
        
        print(f"\nTop {top_n} Contributing Features:")
        print(explanation.to_string(index=False))
        
        return explanation


def main():
    """Example usage"""
    print("="*60)
    print("NETWORK CONFLICT PREDICTOR - INFERENCE")
    print("="*60)
    
    # Initialize predictor
    predictor = ConflictPredictor()
    
    # Example 1: Predict on single snapshot
    print("\n" + "="*60)
    print("Example 1: Single Prediction")
    print("="*60)
    
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
    
    print("\nPrediction Result:")
    print(f"  Conflict Predicted: {result['prediction']}")
    print(f"  Conflict Probability: {result['conflict_probability']:.4f}")
    print(f"  Confidence: {result['confidence']:.4f}")
    print(f"  Risk Level: {result['risk_level']}")
    
    # Example 2: Predict on CSV file
    print("\n" + "="*60)
    print("Example 2: Batch Prediction from CSV")
    print("="*60)
    
    csv_path = '../dataset/processed/network_conflicts_minute.csv'
    output_path = 'conflict_prediction_model/predictions.csv'
    
    try:
        df_predictions = predictor.predict_from_csv(csv_path, output_path)
        
        # Show sample predictions
        print("\nSample Predictions:")
        print(df_predictions[['network_id', 'train_count', 'predicted_conflict', 
                             'conflict_probability', 'risk_level']].head(10).to_string(index=False))
    except FileNotFoundError:
        print(f"Dataset not found at '{csv_path}'. Skipping batch prediction example.")


if __name__ == "__main__":
    main()
