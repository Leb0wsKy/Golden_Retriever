"""
Model Evaluation and Analysis
Comprehensive evaluation tools for the conflict prediction model
"""

import pandas as pd
import numpy as np
import joblib
import json
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    confusion_matrix, 
    classification_report,
    roc_curve, 
    auc, 
    precision_recall_curve,
    average_precision_score
)
from predict import ConflictPredictor
import warnings
warnings.filterwarnings('ignore')

# Set style
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (12, 8)


class ModelEvaluator:
    """Comprehensive model evaluation tools"""
    
    def __init__(self, predictor, test_data_path):
        """
        Initialize evaluator
        
        Args:
            predictor: ConflictPredictor instance
            test_data_path: path to test dataset with ground truth
        """
        self.predictor = predictor
        self.test_data_path = test_data_path
        self.test_df = None
        self.predictions = None
        self.y_true = None
        self.y_pred = None
        self.y_proba = None
        
    def load_test_data(self):
        """Load test dataset"""
        print(f"Loading test data from '{self.test_data_path}'...")
        self.test_df = pd.read_csv(self.test_data_path)
        print(f"  Loaded {len(self.test_df)} test samples")
        return self
    
    def make_predictions(self):
        """Make predictions on test data"""
        print("\nMaking predictions on test set...")
        
        results = self.predictor.predict(self.test_df)
        
        if isinstance(results, list):
            self.y_proba = np.array([r['conflict_probability'] for r in results])
            self.y_pred = np.array([r['prediction'] for r in results])
        else:
            self.y_proba = np.array([results['conflict_probability']])
            self.y_pred = np.array([results['prediction']])
        
        self.y_true = self.test_df['is_network_conflict'].values
        
        print("  Predictions complete")
        return self
    
    def print_metrics(self):
        """Print detailed metrics"""
        print("\n" + "="*60)
        print("DETAILED EVALUATION METRICS")
        print("="*60)
        
        # Classification report
        print("\nClassification Report:")
        print(classification_report(
            self.y_true, self.y_pred,
            target_names=['No Conflict', 'Conflict'],
            digits=4
        ))
        
        # Confusion matrix
        cm = confusion_matrix(self.y_true, self.y_pred)
        print("\nConfusion Matrix:")
        print(f"                    Predicted")
        print(f"                 No    |  Yes")
        print(f"Actual  No    {cm[0,0]:6d} | {cm[0,1]:6d}")
        print(f"        Yes   {cm[1,0]:6d} | {cm[1,1]:6d}")
        
        # Additional metrics
        tn, fp, fn, tp = cm.ravel()
        
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        
        print(f"\nAdditional Metrics:")
        print(f"  True Positives:  {tp}")
        print(f"  True Negatives:  {tn}")
        print(f"  False Positives: {fp}")
        print(f"  False Negatives: {fn}")
        print(f"  Sensitivity (Recall): {sensitivity:.4f}")
        print(f"  Specificity: {specificity:.4f}")
        
        # ROC-AUC
        roc_auc = auc(*roc_curve(self.y_true, self.y_proba)[:2][::-1])
        print(f"  ROC-AUC Score: {roc_auc:.4f}")
        
        # Average Precision
        avg_precision = average_precision_score(self.y_true, self.y_proba)
        print(f"  Average Precision: {avg_precision:.4f}")
        
        return self
    
    def plot_confusion_matrix(self, save_path='conflict_prediction_model/confusion_matrix.png'):
        """Plot confusion matrix heatmap"""
        cm = confusion_matrix(self.y_true, self.y_pred)
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(
            cm, 
            annot=True, 
            fmt='d', 
            cmap='Blues',
            xticklabels=['No Conflict', 'Conflict'],
            yticklabels=['No Conflict', 'Conflict']
        )
        plt.title('Confusion Matrix', fontsize=16, fontweight='bold')
        plt.ylabel('Actual', fontsize=12)
        plt.xlabel('Predicted', fontsize=12)
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\nConfusion matrix plot saved to '{save_path}'")
        plt.close()
        
        return self
    
    def plot_roc_curve(self, save_path='conflict_prediction_model/roc_curve.png'):
        """Plot ROC curve"""
        fpr, tpr, thresholds = roc_curve(self.y_true, self.y_proba)
        roc_auc = auc(fpr, tpr)
        
        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, color='darkorange', lw=2, 
                label=f'ROC curve (AUC = {roc_auc:.4f})')
        plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', 
                label='Random Classifier')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate', fontsize=12)
        plt.ylabel('True Positive Rate', fontsize=12)
        plt.title('Receiver Operating Characteristic (ROC) Curve', 
                 fontsize=16, fontweight='bold')
        plt.legend(loc="lower right", fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"ROC curve plot saved to '{save_path}'")
        plt.close()
        
        return self
    
    def plot_precision_recall_curve(self, save_path='conflict_prediction_model/precision_recall_curve.png'):
        """Plot Precision-Recall curve"""
        precision, recall, thresholds = precision_recall_curve(self.y_true, self.y_proba)
        avg_precision = average_precision_score(self.y_true, self.y_proba)
        
        plt.figure(figsize=(8, 6))
        plt.plot(recall, precision, color='blue', lw=2,
                label=f'PR curve (AP = {avg_precision:.4f})')
        plt.xlabel('Recall', fontsize=12)
        plt.ylabel('Precision', fontsize=12)
        plt.title('Precision-Recall Curve', fontsize=16, fontweight='bold')
        plt.legend(loc="lower left", fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Precision-Recall curve plot saved to '{save_path}'")
        plt.close()
        
        return self
    
    def plot_feature_importance(self, top_n=15, save_path='conflict_prediction_model/feature_importance.png'):
        """Plot feature importance"""
        if not hasattr(self.predictor.model, 'feature_importances_'):
            print("Model does not support feature importance visualization")
            return self
        
        # Get feature importances
        importance_df = pd.DataFrame({
            'feature': self.predictor.feature_names,
            'importance': self.predictor.model.feature_importances_
        }).sort_values('importance', ascending=False).head(top_n)
        
        # Plot
        plt.figure(figsize=(10, 8))
        plt.barh(range(len(importance_df)), importance_df['importance'], color='steelblue')
        plt.yticks(range(len(importance_df)), importance_df['feature'])
        plt.xlabel('Importance', fontsize=12)
        plt.ylabel('Feature', fontsize=12)
        plt.title(f'Top {top_n} Most Important Features', fontsize=16, fontweight='bold')
        plt.gca().invert_yaxis()
        plt.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Feature importance plot saved to '{save_path}'")
        plt.close()
        
        return self
    
    def plot_probability_distribution(self, save_path='conflict_prediction_model/probability_distribution.png'):
        """Plot distribution of predicted probabilities"""
        plt.figure(figsize=(10, 6))
        
        # Separate by actual class
        conflict_probs = self.y_proba[self.y_true == 1]
        no_conflict_probs = self.y_proba[self.y_true == 0]
        
        plt.hist(no_conflict_probs, bins=50, alpha=0.6, label='No Conflict (Actual)', 
                color='green', edgecolor='black')
        plt.hist(conflict_probs, bins=50, alpha=0.6, label='Conflict (Actual)', 
                color='red', edgecolor='black')
        
        plt.xlabel('Predicted Conflict Probability', fontsize=12)
        plt.ylabel('Frequency', fontsize=12)
        plt.title('Distribution of Predicted Probabilities', fontsize=16, fontweight='bold')
        plt.legend(loc='upper center', fontsize=10)
        plt.grid(axis='y', alpha=0.3)
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Probability distribution plot saved to '{save_path}'")
        plt.close()
        
        return self
    
    def analyze_errors(self):
        """Analyze prediction errors"""
        print("\n" + "="*60)
        print("ERROR ANALYSIS")
        print("="*60)
        
        # False positives
        fp_indices = np.where((self.y_pred == 1) & (self.y_true == 0))[0]
        print(f"\nFalse Positives: {len(fp_indices)}")
        
        if len(fp_indices) > 0:
            fp_data = self.test_df.iloc[fp_indices]
            print("\nFalse Positive Statistics:")
            print(f"  Avg Train Count: {fp_data['train_count'].mean():.2f}")
            print(f"  Avg Conflict Count: {fp_data['conflict_count'].mean():.2f}")
            print(f"  Avg Anomaly Ratio: {fp_data['anomaly_ratio'].mean():.4f}")
            print(f"  Avg Conflict Probability: {self.y_proba[fp_indices].mean():.4f}")
        
        # False negatives
        fn_indices = np.where((self.y_pred == 0) & (self.y_true == 1))[0]
        print(f"\nFalse Negatives: {len(fn_indices)}")
        
        if len(fn_indices) > 0:
            fn_data = self.test_df.iloc[fn_indices]
            print("\nFalse Negative Statistics:")
            print(f"  Avg Train Count: {fn_data['train_count'].mean():.2f}")
            print(f"  Avg Conflict Count: {fn_data['conflict_count'].mean():.2f}")
            print(f"  Avg Anomaly Ratio: {fn_data['anomaly_ratio'].mean():.4f}")
            print(f"  Avg Conflict Probability: {self.y_proba[fn_indices].mean():.4f}")
        
        return self
    
    def generate_full_report(self):
        """Generate complete evaluation report"""
        print("\n" + "="*60)
        print("GENERATING COMPLETE EVALUATION REPORT")
        print("="*60)
        
        self.load_test_data()
        self.make_predictions()
        self.print_metrics()
        self.plot_confusion_matrix()
        self.plot_roc_curve()
        self.plot_precision_recall_curve()
        self.plot_feature_importance()
        self.plot_probability_distribution()
        self.analyze_errors()
        
        print("\n" + "="*60)
        print("EVALUATION COMPLETE!")
        print("="*60)
        print("\nGenerated artifacts:")
        print("  - confusion_matrix.png")
        print("  - roc_curve.png")
        print("  - precision_recall_curve.png")
        print("  - feature_importance.png")
        print("  - probability_distribution.png")
        
        return self


def main():
    """Run complete evaluation"""
    print("="*60)
    print("MODEL EVALUATION")
    print("="*60)
    
    # Load predictor
    predictor = ConflictPredictor()
    
    # Initialize evaluator
    test_data_path = '../dataset/processed/network_conflicts_minute.csv'
    evaluator = ModelEvaluator(predictor, test_data_path)
    
    # Generate full report
    evaluator.generate_full_report()


if __name__ == "__main__":
    main()
