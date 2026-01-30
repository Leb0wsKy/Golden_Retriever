"""
Train Network Conflict Prediction Model
Predicts train network conflicts using historical network data
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    classification_report, 
    confusion_matrix, 
    roc_auc_score, 
    accuracy_score,
    precision_recall_fscore_support
)
import joblib
import json
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')


class NetworkConflictPredictor:
    """Train and evaluate network conflict prediction model"""
    
    def __init__(self, dataset_path):
        self.dataset_path = dataset_path
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = None
        self.metrics = {}
        
    def load_data(self):
        """Load and prepare the dataset"""
        print("Loading dataset...")
        self.df = pd.read_csv(self.dataset_path)
        print(f"Dataset loaded: {self.df.shape[0]} rows, {self.df.shape[1]} columns")
        
        # Display basic info
        print("\nDataset Info:")
        print(f"Columns: {list(self.df.columns)}")
        print(f"\nClass Distribution:")
        print(self.df['is_network_conflict'].value_counts())
        print(f"\nConflict Rate: {self.df['is_network_conflict'].mean():.2%}")
        
        return self
    
    def prepare_features(self):
        """Prepare features for training"""
        print("\nPreparing features...")
        
        # Define feature columns
        # Exclude features that leak target information:
        #   - conflict_count, conflict_ratio (directly derived from conflicts)
        #   - conflict_score, conflict_probability (used to generate labels)
        
        # Core network metrics (safe to use)
        network_features = [
            'train_count',
            'avg_speed',
            'std_speed',
            'min_speed',
            'speed_variance',
            'slow_train_ratio',
            'fast_train_ratio'
        ]
        
        # Delay features (observable before conflict determination)
        delay_features = [
            'avg_delay',
            'max_delay',
            'std_delay',
            'delayed_train_count',
            'delayed_ratio',
            'severe_delay_count',
            'delayed_status_count',
            'status_delay_mismatch'
        ]
        
        # Anomaly features
        anomaly_features = [
            'anomaly_count',
            'anomaly_ratio'
        ]
        
        # Proximity/density features
        proximity_features = [
            'avg_nearest_distance',
            'min_nearest_distance',
            'crowded_locations',
            'avg_nearby_trains'
        ]
        
        # Interaction features (compound indicators)
        interaction_features = [
            'high_density_slow_speed',
            'delayed_with_high_proximity',
            'speed_delay_correlation',
            'location_spread'
        ]
        
        # Temporal trend features
        temporal_features = [
            'avg_speed_trend',
            'avg_delay_trend',
            'anomaly_ratio_trend',
            'delayed_ratio_trend'
        ]
        
        # Combine all legitimate predictive features
        self.feature_names = (
            network_features + 
            delay_features + 
            anomaly_features + 
            proximity_features + 
            interaction_features +
            temporal_features
        )
        
        # Extract features and target
        X = self.df[self.feature_names].copy()
        
        # Handle any missing values
        X = X.fillna(0)
        
        y = self.df['is_network_conflict'].astype(int)
        
        print(f"Features prepared: {len(self.feature_names)} features")
        print(f"Feature names: {self.feature_names}")
        
        return X, y
    
    def split_data(self, X, y, test_size=0.2, random_state=42):
        """Split data into train and test sets"""
        print(f"\nSplitting data (test_size={test_size})...")
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=test_size, 
            random_state=random_state,
            stratify=y  # Maintain class distribution
        )
        
        print(f"Train set: {X_train.shape[0]} samples")
        print(f"Test set: {X_test.shape[0]} samples")
        print(f"Train conflict rate: {y_train.mean():.2%}")
        print(f"Test conflict rate: {y_test.mean():.2%}")
        
        return X_train, X_test, y_train, y_test
    
    def scale_features(self, X_train, X_test):
        """Scale features using StandardScaler"""
        print("\nScaling features...")
        
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        return X_train_scaled, X_test_scaled
    
    def train_random_forest(self, X_train, y_train, optimize=True):
        """Train Random Forest model with optional hyperparameter tuning"""
        print("\n" + "="*60)
        print("Training Random Forest Classifier")
        print("="*60)
        
        if optimize:
            print("Performing hyperparameter optimization...")
            
            param_grid = {
                'n_estimators': [200, 300, 500],
                'max_depth': [10, 15, 20, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4],
                'max_features': ['sqrt', 'log2'],
                'class_weight': ['balanced', 'balanced_subsample']
            }
            
            rf = RandomForestClassifier(random_state=42)
            
            grid_search = GridSearchCV(
                rf, param_grid, 
                cv=5, 
                scoring='f1',
                n_jobs=-1,
                verbose=1
            )
            
            grid_search.fit(X_train, y_train)
            
            self.model = grid_search.best_estimator_
            print(f"\nBest parameters: {grid_search.best_params_}")
            print(f"Best CV F1 score: {grid_search.best_score_:.4f}")
        else:
            # Train with parameters optimized for imbalanced data
            self.model = RandomForestClassifier(
                n_estimators=300,
                max_depth=15,
                min_samples_split=5,
                min_samples_leaf=2,
                max_features='sqrt',
                random_state=42,
                class_weight='balanced_subsample',  # Better for imbalanced data
                max_samples=0.8,  # Bootstrap with subsampling
                n_jobs=-1,
                verbose=0
            )
            
            self.model.fit(X_train, y_train)
            print("Model trained successfully!")
        
        return self
    
    def train_gradient_boosting(self, X_train, y_train):
        """Train Gradient Boosting model as alternative"""
        print("\n" + "="*60)
        print("Training Gradient Boosting Classifier")
        print("="*60)
        
        self.model = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=5,
            min_samples_split=5,
            min_samples_leaf=2,
            subsample=0.8,
            random_state=42
        )
        
        self.model.fit(X_train, y_train)
        print("Gradient Boosting model trained successfully!")
        
        return self
    
    def evaluate_model(self, X_train, X_test, y_train, y_test):
        """Comprehensive model evaluation"""
        print("\n" + "="*60)
        print("Model Evaluation")
        print("="*60)
        
        # Predictions
        y_train_pred = self.model.predict(X_train)
        y_test_pred = self.model.predict(X_test)
        
        # Prediction probabilities
        y_train_proba = self.model.predict_proba(X_train)[:, 1]
        y_test_proba = self.model.predict_proba(X_test)[:, 1]
        
        # Calculate metrics
        train_accuracy = accuracy_score(y_train, y_train_pred)
        test_accuracy = accuracy_score(y_test, y_test_pred)
        
        train_auc = roc_auc_score(y_train, y_train_proba)
        test_auc = roc_auc_score(y_test, y_test_proba)
        
        # Precision, recall, f1
        train_precision, train_recall, train_f1, _ = precision_recall_fscore_support(
            y_train, y_train_pred, average='binary'
        )
        test_precision, test_recall, test_f1, _ = precision_recall_fscore_support(
            y_test, y_test_pred, average='binary'
        )
        
        # Store metrics
        self.metrics = {
            'train_accuracy': train_accuracy,
            'test_accuracy': test_accuracy,
            'train_auc': train_auc,
            'test_auc': test_auc,
            'train_precision': train_precision,
            'train_recall': train_recall,
            'train_f1': train_f1,
            'test_precision': test_precision,
            'test_recall': test_recall,
            'test_f1': test_f1,
            'model_type': type(self.model).__name__
        }
        
        # Print results
        print("\nTrain Set Performance:")
        print(f"  Accuracy:  {train_accuracy:.4f}")
        print(f"  Precision: {train_precision:.4f}")
        print(f"  Recall:    {train_recall:.4f}")
        print(f"  F1-Score:  {train_f1:.4f}")
        print(f"  ROC-AUC:   {train_auc:.4f}")
        
        print("\nTest Set Performance:")
        print(f"  Accuracy:  {test_accuracy:.4f}")
        print(f"  Precision: {test_precision:.4f}")
        print(f"  Recall:    {test_recall:.4f}")
        print(f"  F1-Score:  {test_f1:.4f}")
        print(f"  ROC-AUC:   {test_auc:.4f}")
        
        print("\nTest Set Classification Report:")
        print(classification_report(y_test, y_test_pred, 
                                   target_names=['No Conflict', 'Conflict']))
        
        print("\nTest Set Confusion Matrix:")
        cm = confusion_matrix(y_test, y_test_pred)
        print(cm)
        print(f"\nTrue Negatives:  {cm[0,0]}")
        print(f"False Positives: {cm[0,1]}")
        print(f"False Negatives: {cm[1,0]}")
        print(f"True Positives:  {cm[1,1]}")
        
        return self
    
    def feature_importance(self):
        """Display feature importance"""
        if hasattr(self.model, 'feature_importances_'):
            print("\n" + "="*60)
            print("Feature Importance")
            print("="*60)
            
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            print(importance_df.to_string(index=False))
            
            # Save to CSV
            importance_df.to_csv(
                'feature_importance.csv',
                index=False
            )
            print("\nFeature importance saved to 'feature_importance.csv'")
            
            return importance_df
        else:
            print("\nModel does not support feature importance.")
            return None
    
    def save_model(self, model_dir='.'):
        """Save trained model and artifacts"""
        print(f"\nSaving model artifacts...")
        
        # Save model
        joblib.dump(self.model, f'{model_dir}/conflict_predictor.pkl')
        print(f"  ✓ Model saved: conflict_predictor.pkl")
        
        # Save scaler
        joblib.dump(self.scaler, f'{model_dir}/scaler.pkl')
        print(f"  ✓ Scaler saved: scaler.pkl")
        
        # Save feature names
        with open(f'{model_dir}/feature_names.json', 'w') as f:
            json.dump(self.feature_names, f, indent=2)
        print(f"  ✓ Feature names saved: feature_names.json")
        
        # Save metrics
        metrics_with_timestamp = {
            **self.metrics,
            'training_date': datetime.now().isoformat(),
            'dataset_path': self.dataset_path,
            'total_samples': len(self.df),
            'feature_count': len(self.feature_names)
        }
        
        with open(f'{model_dir}/model_metrics.json', 'w') as f:
            json.dump(metrics_with_timestamp, f, indent=2)
        print(f"  ✓ Metrics saved: model_metrics.json")
        
        print("\nModel artifacts saved successfully!")
        
        return self


def main():
    """Main training pipeline"""
    print("="*60)
    print("NETWORK CONFLICT PREDICTION MODEL TRAINING")
    print("="*60)
    
    # Configuration
    DATASET_PATH = 'network_conflicts_realistic.csv'  # New realistic dataset
    MODEL_TYPE = 'random_forest'  # Options: 'random_forest', 'gradient_boosting'
    OPTIMIZE_HYPERPARAMS = False  # Set to True for hyperparameter tuning (slower)
    
    # Initialize predictor
    predictor = NetworkConflictPredictor(DATASET_PATH)
    
    # Load and prepare data
    predictor.load_data()
    X, y = predictor.prepare_features()
    
    # Split data
    X_train, X_test, y_train, y_test = predictor.split_data(X, y)
    
    # Scale features
    X_train_scaled, X_test_scaled = predictor.scale_features(X_train, X_test)
    
    # Train model
    if MODEL_TYPE == 'random_forest':
        predictor.train_random_forest(X_train_scaled, y_train, optimize=OPTIMIZE_HYPERPARAMS)
    elif MODEL_TYPE == 'gradient_boosting':
        predictor.train_gradient_boosting(X_train_scaled, y_train)
    else:
        raise ValueError(f"Unknown model type: {MODEL_TYPE}")
    
    # Evaluate model
    predictor.evaluate_model(X_train_scaled, X_test_scaled, y_train, y_test)
    
    # Feature importance
    predictor.feature_importance()
    
    # Save model
    predictor.save_model()
    
    print("\n" + "="*60)
    print("TRAINING COMPLETE!")
    print("="*60)
    print("\nModel artifacts saved:")
    print("  - conflict_predictor.pkl (trained model)")
    print("  - scaler.pkl (feature scaler)")
    print("  - feature_names.json (feature list)")
    print("  - model_metrics.json (performance metrics)")
    print("  - feature_importance.csv (feature rankings)")


if __name__ == "__main__":
    main()
