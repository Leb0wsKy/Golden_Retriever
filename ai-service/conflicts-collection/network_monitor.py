"""
Network Conflict Monitor

Analyzes network-level conflict patterns to provide risk assessment
for recommendation confidence adjustment.

Usage:
    from network_monitor import NetworkConflictMonitor
    
    monitor = NetworkConflictMonitor('dataset/processed/network_conflicts.csv')
    risk = monitor.get_network_risk('FS', datetime.now())
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)


class NetworkConflictMonitor:
    """
    Monitors network-level conflict patterns from historical data.
    
    Provides risk assessment based on:
    - Time of day patterns
    - Network-specific conflict rates
    - Historical anomaly trends
    """
    
    def __init__(self, csv_path: str):
        """
        Initialize monitor with network conflicts dataset.
        
        Args:
            csv_path: Path to network_conflicts.csv
        """
        self.csv_path = Path(csv_path)
        
        if not self.csv_path.exists():
            logger.warning(f"Network conflicts dataset not found: {csv_path}")
            self.df = pd.DataFrame()
            return
        
        try:
            self.df = pd.read_csv(csv_path)
            self.df['snapshot_ts'] = pd.to_datetime(self.df['snapshot_ts'])
            self.df['hour'] = self.df['snapshot_ts'].dt.hour
            self.df['day_of_week'] = self.df['snapshot_ts'].dt.dayofweek
            
            logger.info(f"Loaded {len(self.df):,} network conflict records")
            logger.info(f"Networks: {self.df['network_id'].nunique()}")
            logger.info(f"Time range: {self.df['snapshot_ts'].min()} to {self.df['snapshot_ts'].max()}")
        
        except Exception as e:
            logger.error(f"Failed to load network conflicts: {e}")
            self.df = pd.DataFrame()
    
    def get_high_risk_windows(self, network_id: str, threshold: float = 0.3) -> List[Dict]:
        """
        Get time windows with elevated conflict probability.
        
        Args:
            network_id: Network identifier (e.g., 'FS', 'AW')
            threshold: Minimum conflict rate to be considered high-risk (0-1)
        
        Returns:
            List of high-risk windows with hour and probability
        """
        if self.df.empty:
            return []
        
        network_data = self.df[self.df['network_id'] == network_id]
        
        if network_data.empty:
            logger.warning(f"No data found for network: {network_id}")
            return []
        
        # Group by hour and calculate conflict rate
        hourly_stats = network_data.groupby('hour').agg({
            'is_network_conflict': ['mean', 'count']
        }).reset_index()
        
        hourly_stats.columns = ['hour', 'conflict_probability', 'sample_count']
        
        # Filter for high-risk hours
        high_risk = hourly_stats[hourly_stats['conflict_probability'] >= threshold]
        
        return [
            {
                "hour": int(row['hour']),
                "conflict_probability": float(row['conflict_probability']),
                "sample_count": int(row['sample_count']),
                "risk_level": self._classify_risk(row['conflict_probability'])
            }
            for _, row in high_risk.iterrows()
        ]
    
    def get_conflict_rate(self, network_id: str) -> float:
        """
        Get overall conflict rate for a network.
        
        Args:
            network_id: Network identifier
        
        Returns:
            Conflict rate (0-1), or 0 if no data
        """
        if self.df.empty:
            return 0.0
        
        network_data = self.df[self.df['network_id'] == network_id]
        
        if network_data.empty:
            return 0.0
        
        return float(network_data['is_network_conflict'].mean())
    
    def get_network_risk(self, network_id: str, current_time: datetime) -> Dict:
        """
        Get comprehensive risk assessment for a network at a specific time.
        
        Args:
            network_id: Network identifier
            current_time: Current timestamp
        
        Returns:
            Risk assessment with multiple metrics
        """
        if self.df.empty:
            return {
                "network_id": network_id,
                "overall_conflict_rate": 0.0,
                "current_hour_risk": 0.0,
                "risk_level": "unknown",
                "high_risk_windows": [],
                "available": False
            }
        
        network_data = self.df[self.df['network_id'] == network_id]
        
        if network_data.empty:
            return {
                "network_id": network_id,
                "overall_conflict_rate": 0.0,
                "current_hour_risk": 0.0,
                "risk_level": "unknown",
                "high_risk_windows": [],
                "available": False
            }
        
        # Overall conflict rate
        overall_rate = float(network_data['is_network_conflict'].mean())
        
        # Current hour risk
        current_hour = current_time.hour
        hour_data = network_data[network_data['hour'] == current_hour]
        current_hour_risk = float(hour_data['is_network_conflict'].mean()) if not hour_data.empty else overall_rate
        
        # High risk windows
        high_risk_windows = self.get_high_risk_windows(network_id)
        
        # Conflict type breakdown
        conflict_types = self._get_conflict_type_distribution(network_data)
        
        return {
            "network_id": network_id,
            "overall_conflict_rate": overall_rate,
            "current_hour_risk": current_hour_risk,
            "risk_level": self._classify_risk(current_hour_risk),
            "high_risk_windows": high_risk_windows,
            "conflict_types": conflict_types,
            "available": True,
            "sample_size": len(network_data)
        }
    
    def get_all_networks_summary(self) -> List[Dict]:
        """
        Get summary statistics for all networks.
        
        Returns:
            List of network summaries
        """
        if self.df.empty:
            return []
        
        summary = []
        
        for network_id in self.df['network_id'].unique():
            network_data = self.df[self.df['network_id'] == network_id]
            
            summary.append({
                "network_id": str(network_id),
                "conflict_rate": float(network_data['is_network_conflict'].mean()),
                "total_snapshots": len(network_data),
                "avg_train_count": float(network_data['train_count'].mean()),
                "avg_anomaly_ratio": float(network_data['anomaly_ratio'].mean()),
                "congestion_conflicts": int(network_data['network_congestion_conflict'].sum()),
                "proximity_conflicts": int(network_data['network_proximity_conflict'].sum())
            })
        
        # Sort by conflict rate descending
        summary.sort(key=lambda x: x['conflict_rate'], reverse=True)
        
        return summary
    
    def _classify_risk(self, conflict_probability: float) -> str:
        """Classify risk level based on probability."""
        if conflict_probability >= 0.7:
            return "critical"
        elif conflict_probability >= 0.5:
            return "high"
        elif conflict_probability >= 0.3:
            return "medium"
        elif conflict_probability >= 0.1:
            return "low"
        else:
            return "minimal"
    
    def _get_conflict_type_distribution(self, network_data: pd.DataFrame) -> Dict[str, float]:
        """Get distribution of conflict types."""
        conflict_data = network_data[network_data['is_network_conflict'] == True]
        
        if conflict_data.empty:
            return {}
        
        total = len(conflict_data)
        
        return {
            "congestion": float(conflict_data['network_congestion_conflict'].sum() / total),
            "proximity": float(conflict_data['network_proximity_conflict'].sum() / total),
            "delay": float(conflict_data['network_delay_conflict'].sum() / total),
            "anomaly_spike": float(conflict_data['network_anomaly_spike'].sum() / total)
        }


# Singleton instance for reuse
_monitor_instance: Optional[NetworkConflictMonitor] = None


def get_network_monitor(csv_path: Optional[str] = None) -> NetworkConflictMonitor:
    """
    Get or create NetworkConflictMonitor instance.
    
    Args:
        csv_path: Path to network_conflicts.csv (optional, uses default if None)
    
    Returns:
        NetworkConflictMonitor instance
    """
    global _monitor_instance
    
    if _monitor_instance is None:
        if csv_path is None:
            # Default path
            csv_path = str(Path(__file__).parent / 'dataset' / 'processed' / 'network_conflicts.csv')
        
        _monitor_instance = NetworkConflictMonitor(csv_path)
    
    return _monitor_instance
