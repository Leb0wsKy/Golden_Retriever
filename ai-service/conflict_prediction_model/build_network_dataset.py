"""
Build Network-Level Dataset with Realistic Noise
Creates a network conflict prediction dataset from train-level data
with complex labeling logic and realistic noise patterns
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)


class NetworkDatasetBuilder:
    """Build realistic network-level dataset from train data"""
    
    def __init__(self, train_data_path):
        self.train_data_path = train_data_path
        self.df = None
        self.network_df = None
        
    def load_data(self):
        """Load train-level dataset"""
        print("Loading train-level data...")
        self.df = pd.read_csv(self.train_data_path)
        print(f"  Loaded {len(self.df):,} train records")
        print(f"  Networks: {self.df['network_id'].nunique()}")
        print(f"  Timestamps: {self.df['snapshot_ts'].nunique()}")
        print(f"  Trains: {self.df['train_id'].nunique()}")
        return self
    
    def aggregate_to_network_level(self):
        """Aggregate train data to network level with complex features"""
        print("\nAggregating to network level...")
        
        # Group by network and timestamp
        grouped = self.df.groupby(['snapshot_ts', 'network_id'])
        
        # Calculate aggregated features
        agg_data = []
        
        for (timestamp, network_id), group in grouped:
            # Basic counts
            train_count = len(group)
            
            # Speed metrics (continuous features with noise)
            avg_speed = group['speed'].mean()
            std_speed = group['speed'].std()
            min_speed = group['speed'].min()
            speed_variance = group['speed'].var()
            
            # Speed distribution features
            slow_train_ratio = (group['speed'] < 40).sum() / train_count
            fast_train_ratio = (group['speed'] > 70).sum() / train_count
            
            # Delay patterns (with measurement noise)
            avg_delay = group['delay'].mean()
            max_delay = group['delay'].max()
            std_delay = group['delay'].std()
            delayed_train_count = (group['delay'] > 0).sum()
            delayed_ratio = delayed_train_count / train_count
            severe_delay_count = (group['delay'] > 5).sum()
            
            # Status patterns
            delayed_status_count = (group['status'] == 'delayed').sum()
            status_delay_mismatch = abs(delayed_status_count - delayed_train_count)
            
            # Anomaly patterns
            anomaly_count = group['is_anomaly'].sum()
            anomaly_ratio = anomaly_count / train_count
            
            # Conflict patterns
            conflict_count = group['has_conflict'].sum()
            conflict_ratio = conflict_count / train_count
            
            # Proximity features
            avg_nearest_distance = group['nearest_train_km'].mean()
            min_nearest_distance = group['nearest_train_km'].min()
            crowded_locations = (group['nearby_trains'] > 20).sum()
            avg_nearby_trains = group['nearby_trains'].mean()
            
            # Interaction features (compound indicators)
            high_density_slow_speed = ((group['nearby_trains'] > 20) & (group['speed'] < 45)).sum()
            delayed_with_high_proximity = ((group['delay'] > 3) & (group['nearby_trains'] > 15)).sum()
            speed_delay_correlation = group[['speed', 'delay']].corr().iloc[0, 1] if len(group) > 1 else 0
            
            # Spatial features
            location_spread = np.sqrt(group['lat'].var() + group['lng'].var()) if len(group) > 1 else 0
            
            # Add realistic measurement noise
            noise_factor = np.random.normal(1.0, 0.02)  # 2% noise
            avg_speed *= noise_factor
            avg_delay *= max(0, np.random.normal(1.0, 0.05))  # 5% noise, non-negative
            
            agg_data.append({
                'snapshot_ts': timestamp,
                'network_id': network_id,
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
                'conflict_count': conflict_count,
                'conflict_ratio': conflict_ratio,
                'avg_nearest_distance': avg_nearest_distance,
                'min_nearest_distance': min_nearest_distance,
                'crowded_locations': crowded_locations,
                'avg_nearby_trains': avg_nearby_trains,
                'high_density_slow_speed': high_density_slow_speed,
                'delayed_with_high_proximity': delayed_with_high_proximity,
                'speed_delay_correlation': speed_delay_correlation,
                'location_spread': location_spread
            })
        
        self.network_df = pd.DataFrame(agg_data)
        print(f"  Created {len(self.network_df):,} network snapshots")
        print(f"  Features: {len(self.network_df.columns) - 2}")  # Exclude timestamp and network_id
        
        return self
    
    def label_network_conflicts(self):
        """
        Label network conflicts using COMPLEX multi-factor logic
        Not simple thresholds - uses combinations and weighted scoring
        """
        print("\nLabeling network conflicts with complex logic...")
        
        # Initialize conflict scores (0-100 scale)
        conflict_scores = np.zeros(len(self.network_df))
        
        # Factor 1: Network Congestion Score (0-30 points)
        # High train count + low average speed + high proximity
        congestion_component = (
            (self.network_df['train_count'] / self.network_df['train_count'].max()) * 10 +
            ((100 - self.network_df['avg_speed']) / 100) * 10 +
            (self.network_df['avg_nearby_trains'] / self.network_df['avg_nearby_trains'].max()) * 10
        )
        conflict_scores += congestion_component
        
        # Factor 2: Delay Propagation Score (0-25 points)
        # Multiple delays + variance in delays + delay-proximity interaction
        delay_component = (
            (self.network_df['delayed_ratio']) * 10 +
            (self.network_df['std_delay'] / (self.network_df['std_delay'].max() + 0.01)) * 8 +
            (self.network_df['delayed_with_high_proximity'] / (self.network_df['train_count'] + 1)) * 7
        )
        conflict_scores += delay_component
        
        # Factor 3: Anomaly & Unpredictability Score (0-20 points)
        # Anomalies + speed variance + status mismatches
        anomaly_component = (
            (self.network_df['anomaly_ratio']) * 8 +
            (self.network_df['speed_variance'] / (self.network_df['speed_variance'].max() + 0.01)) * 6 +
            (self.network_df['status_delay_mismatch'] / (self.network_df['train_count'] + 1)) * 6
        )
        conflict_scores += anomaly_component
        
        # Factor 4: Critical Density Score (0-15 points)
        # Crowded locations + slow trains in high density + min proximity
        density_component = (
            (self.network_df['crowded_locations'] / (self.network_df['train_count'] + 1)) * 6 +
            (self.network_df['high_density_slow_speed'] / (self.network_df['train_count'] + 1)) * 5 +
            (1 / (self.network_df['min_nearest_distance'] + 1)) * 4
        )
        conflict_scores += density_component
        
        # Factor 5: Systemic Stress Score (0-10 points)
        # Combination of multiple moderate issues
        stress_component = (
            (self.network_df['slow_train_ratio'] * self.network_df['delayed_ratio']) * 5 +
            (self.network_df['severe_delay_count'] / (self.network_df['train_count'] + 1)) * 5
        )
        conflict_scores += stress_component
        
        # Add realistic noise to scores (±5 points)
        noise = np.random.normal(0, 5, len(conflict_scores))
        conflict_scores += noise
        
        # Clip to 0-100 range
        conflict_scores = np.clip(conflict_scores, 0, 100)
        
        # Convert to probabilities using sigmoid-like function
        # Add probabilistic element - same score doesn't always produce same label
        base_probabilities = 1 / (1 + np.exp(-(conflict_scores - 50) / 10))
        
        # Add sampling noise - introduce label noise
        label_noise = np.random.uniform(0, 1, len(base_probabilities))
        
        # Generate labels with uncertainty
        self.network_df['conflict_score'] = conflict_scores
        self.network_df['conflict_probability'] = base_probabilities
        self.network_df['is_network_conflict'] = (base_probabilities > label_noise).astype(int)
        
        # Add label noise: flip 3% of labels randomly
        flip_mask = np.random.random(len(self.network_df)) < 0.03
        self.network_df.loc[flip_mask, 'is_network_conflict'] = 1 - self.network_df.loc[flip_mask, 'is_network_conflict']
        
        conflict_rate = self.network_df['is_network_conflict'].mean()
        print(f"  Conflict rate: {conflict_rate:.2%}")
        print(f"  Conflict score range: {conflict_scores.min():.1f} - {conflict_scores.max():.1f}")
        print(f"  Average conflict score: {conflict_scores.mean():.1f}")
        
        return self
    
    def add_temporal_features(self):
        """Add temporal context features"""
        print("\nAdding temporal features...")
        
        # Parse timestamp
        self.network_df['timestamp'] = pd.to_datetime(self.network_df['snapshot_ts'])
        
        # Extract time features
        self.network_df['hour'] = self.network_df['timestamp'].dt.hour
        self.network_df['minute'] = self.network_df['timestamp'].dt.minute
        
        # Sort by network and time
        self.network_df = self.network_df.sort_values(['network_id', 'timestamp'])
        
        # Calculate rolling statistics (previous 3 snapshots)
        for col in ['avg_speed', 'avg_delay', 'anomaly_ratio', 'delayed_ratio']:
            self.network_df[f'{col}_trend'] = (
                self.network_df.groupby('network_id')[col]
                .rolling(window=3, min_periods=1)
                .mean()
                .reset_index(0, drop=True)
            )
        
        # Drop temporary columns
        self.network_df = self.network_df.drop(['timestamp'], axis=1)
        
        print(f"  Added {4} temporal trend features")
        
        return self
    
    def save_dataset(self, output_path):
        """Save the processed dataset"""
        print(f"\nSaving dataset to '{output_path}'...")
        
        self.network_df.to_csv(output_path, index=False)
        print(f"  Saved {len(self.network_df):,} records")
        print(f"  Total features: {len(self.network_df.columns) - 3}")  # Exclude metadata
        
        return self
    
    def print_summary(self):
        """Print dataset summary"""
        print("\n" + "="*60)
        print("DATASET SUMMARY")
        print("="*60)
        
        print(f"\nRows: {len(self.network_df):,}")
        print(f"Features: {len(self.network_df.columns) - 3}")
        
        print(f"\nTarget Distribution:")
        print(self.network_df['is_network_conflict'].value_counts())
        print(f"Conflict Rate: {self.network_df['is_network_conflict'].mean():.2%}")
        
        print(f"\nConflict Score Statistics:")
        print(f"  Mean: {self.network_df['conflict_score'].mean():.2f}")
        print(f"  Std:  {self.network_df['conflict_score'].std():.2f}")
        print(f"  Min:  {self.network_df['conflict_score'].min():.2f}")
        print(f"  Max:  {self.network_df['conflict_score'].max():.2f}")
        
        print(f"\nKey Features:")
        for col in ['train_count', 'avg_speed', 'avg_delay', 'anomaly_ratio', 'delayed_ratio']:
            print(f"  {col:20s}: mean={self.network_df[col].mean():.2f}, std={self.network_df[col].std():.2f}")
        
        print(f"\nFeature List:")
        feature_cols = [c for c in self.network_df.columns if c not in ['snapshot_ts', 'network_id', 'hour', 'minute', 'is_network_conflict', 'conflict_score', 'conflict_probability']]
        for i, col in enumerate(feature_cols, 1):
            print(f"  {i:2d}. {col}")


def main():
    """Build network dataset"""
    print("="*60)
    print("NETWORK CONFLICT DATASET BUILDER")
    print("="*60)
    
    # Paths
    TRAIN_DATA_PATH = '../dataset/processed/dataset.csv'
    OUTPUT_PATH = 'network_conflicts_realistic.csv'
    
    # Build dataset
    builder = NetworkDatasetBuilder(TRAIN_DATA_PATH)
    
    builder.load_data()
    builder.aggregate_to_network_level()
    builder.label_network_conflicts()
    builder.add_temporal_features()
    builder.save_dataset(OUTPUT_PATH)
    builder.print_summary()
    
    print("\n" + "="*60)
    print("DATASET CREATION COMPLETE!")
    print("="*60)
    print(f"\nOutput: {OUTPUT_PATH}")
    print("\nThis dataset includes:")
    print("  ✓ Complex multi-factor conflict labeling")
    print("  ✓ Realistic measurement noise")
    print("  ✓ Label noise (3% random flips)")
    print("  ✓ Probabilistic labeling (not deterministic)")
    print("  ✓ Temporal trend features")
    print("  ✓ Interaction features (compound indicators)")


if __name__ == "__main__":
    main()
