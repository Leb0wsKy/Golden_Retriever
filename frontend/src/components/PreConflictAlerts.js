import React, { useState, useEffect } from 'react';
import {
  Paper,
  Typography,
  Box,
  Alert,
  AlertTitle,
  Chip,
  CircularProgress,
  IconButton,
  Tooltip,
  Divider,
  List,
  ListItem,
  ListItemText,
  Button,
  Snackbar,
} from '@mui/material';
import {
  Warning as WarningIcon,
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import axios from 'axios';

function PreConflictAlerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scannerStatus, setScannerStatus] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  useEffect(() => {
    fetchAlerts();
    fetchScannerStatus();
    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchAlerts();
      fetchScannerStatus();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchAlerts = async () => {
    try {
      // Fetch both preventive alerts AND ML predictions
      const [preventiveResponse, mlResponse] = await Promise.all([
        axios.get('http://localhost:5000/api/digital-twin/preventive-alerts/').catch(() => ({ data: [] })),
        axios.get('http://localhost:5000/api/digital-twin/ml/predictions?limit=20&min_probability=0.4').catch(() => ({ data: [] }))
      ]);
      
      const preventiveAlerts = Array.isArray(preventiveResponse.data) ? preventiveResponse.data : [];
      const mlPredictions = Array.isArray(mlResponse.data) ? mlResponse.data : [];
      
      // Combine both types of alerts
      const combinedAlerts = [
        ...mlPredictions.map(pred => ({
          alert_id: pred.id,
          detected_at: pred.detected_at,
          similarity_score: pred.confidence,
          predicted_conflict_type: 'ml_prediction',
          predicted_severity: pred.severity,
          predicted_location: pred.network_id,
          time_to_conflict_minutes: 15, // Default for ML predictions
          recommended_actions: pred.contributing_factors || [],
          explanation: pred.alert_message,
          confidence: pred.confidence,
          source: 'ml_model',
          risk_level: pred.risk_level,
          probability: pred.probability
        })),
        ...preventiveAlerts.map(alert => ({
          ...alert,
          source: 'pattern_matching'
        }))
      ];
      
      setAlerts(combinedAlerts);
      setLastUpdate(new Date());
      setLoading(false);
      setError(null);
    } catch (error) {
      console.error('Error fetching alerts:', error);
      setError('Failed to fetch alerts. Please check if services are running.');
      setLoading(false);
    }
  };

  const fetchScannerStatus = async () => {
    try {
      const response = await axios.get('http://localhost:5000/api/digital-twin/preventive-alerts/health');
      setScannerStatus(response.data);
    } catch (error) {
      console.error('Error fetching scanner status:', error);
      // Don't show error for status check - it's not critical
    }
  };

  const handleManualScan = async () => {
    try {
      setLoading(true);
      await axios.post('http://localhost:5000/api/digital-twin/preventive-alerts/scan', {
        similarity_threshold: 0.35,
        alert_confidence_threshold: 0.3
      });
      setSuccessMessage('Manual scan completed successfully!');
      // Refresh alerts after scan
      setTimeout(fetchAlerts, 2000);
    } catch (error) {
      console.error('Error triggering manual scan:', error);
      setError('Failed to trigger manual scan. Please try again.');
      setLoading(false);
    }
  };

  const getSeverityColor = (severity) => {
    const severityLower = severity?.toLowerCase() || '';
    if (severityLower === 'high' || severityLower === 'critical' || severityLower === 'severe') {
      return '#ef5350'; // Red for critical
    }
    if (severityLower === 'medium' || severityLower === 'moderate') {
      return '#ff9800'; // Orange for medium
    }
    return '#fdd835'; // Yellow for low
  };

  const getSeverityIcon = (severity) => {
    const severityLower = severity?.toLowerCase() || '';
    if (severityLower === 'high' || severityLower === 'critical' || severityLower === 'severe') {
      return <ErrorIcon />;
    }
    if (severityLower === 'medium' || severityLower === 'moderate') {
      return <WarningIcon />;
    }
    return <TrendingUpIcon />;
  };

  const getConfidenceBadgeColor = (confidence) => {
    if (confidence >= 0.7) return '#ef5350';
    if (confidence >= 0.5) return '#ff9800';
    return '#66bb6a';
  };

  const formatTimeToConflict = (minutes) => {
    if (!minutes) return 'Unknown';
    if (minutes < 60) return `${minutes} minutes`;
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hours}h ${mins}m`;
  };

  return (
    <Paper 
      elevation={3} 
      sx={{ 
        p: 3, 
        height: '100%',
        background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #7e22ce 100%)',
        color: 'white',
        borderRadius: 3,
        boxShadow: '0 8px 32px rgba(0,0,0,0.12)'
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Box sx={{ 
            bgcolor: 'rgba(255,255,255,0.15)', 
            p: 1, 
            borderRadius: 2,
            display: 'flex',
            alignItems: 'center'
          }}>
            <WarningIcon sx={{ fontSize: 28 }} />
          </Box>
          <Box>
            <Typography variant="h6" fontWeight="bold">
              ⚡ Pre-Conflict Alerts
            </Typography>
            <Typography variant="caption" sx={{ opacity: 0.8 }}>
              Predictive Pattern Detection
            </Typography>
          </Box>
        </Box>
        <Tooltip title="Trigger manual scan">
          <IconButton 
            onClick={handleManualScan} 
            disabled={loading}
            sx={{ 
              color: 'white',
              bgcolor: 'rgba(255,255,255,0.15)',
              '&:hover': { bgcolor: 'rgba(255,255,255,0.25)' }
            }}
          >
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Scanner Status */}
      {scannerStatus && (
        <Box sx={{ 
          mb: 2, 
          p: 1.5, 
          bgcolor: 'rgba(255,255,255,0.12)', 
          borderRadius: 2,
          border: '1px solid rgba(255,255,255,0.2)'
        }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="body2" fontWeight={600}>
              Scanner: <Chip 
                label={scannerStatus.status} 
                size="small" 
                sx={{ 
                  bgcolor: scannerStatus.status === 'healthy' ? 'rgba(76, 175, 80, 0.3)' : 'rgba(244, 67, 54, 0.3)',
                  color: 'white',
                  fontWeight: 'bold',
                  ml: 1
                }}
              />
            </Typography>
            {scannerStatus.status === 'healthy' && (
              <CheckCircleIcon sx={{ color: '#66bb6a' }} />
            )}
          </Box>
          <Typography variant="caption" sx={{ opacity: 0.7, mt: 0.5, display: 'block' }}>
            🎯 Threshold: {(scannerStatus.similarity_threshold * 100).toFixed(0)}% similarity
          </Typography>
        </Box>
      )}

      <Divider sx={{ my: 2, borderColor: 'rgba(255,255,255,0.2)' }} />

      {/* Alerts List */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress sx={{ color: 'white' }} />
        </Box>
      ) : alerts.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <CheckCircleIcon sx={{ fontSize: 64, opacity: 0.3, mb: 2 }} />
          <Typography variant="body1" sx={{ opacity: 0.7 }}>
            No emerging conflicts detected
          </Typography>
          <Typography variant="caption" sx={{ opacity: 0.5 }}>
            System is monitoring network patterns continuously
          </Typography>
        </Box>
      ) : (
        <List sx={{ maxHeight: 400, overflow: 'auto' }}>
          {alerts.map((alert, index) => (
            <ListItem 
              key={index}
              sx={{ 
                bgcolor: 'rgba(255,255,255,0.12)', 
                borderRadius: 2, 
                mb: 1.5,
                flexDirection: 'column',
                alignItems: 'flex-start',
                border: '1px solid rgba(255,255,255,0.2)',
                borderLeftWidth: 4,
                borderLeftColor: getSeverityColor(alert.predicted_severity),
                transition: 'all 0.2s ease',
                '&:hover': {
                  bgcolor: 'rgba(255,255,255,0.18)',
                  transform: 'translateX(4px)',
                  boxShadow: '0 4px 16px rgba(0,0,0,0.2)'
                }
              }}
            >
              <Box sx={{ width: '100%', display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  <Box sx={{ 
                    bgcolor: getSeverityColor(alert.predicted_severity),
                    p: 0.5,
                    borderRadius: 1,
                    display: 'flex',
                    alignItems: 'center',
                    color: 'white'
                  }}>
                    {getSeverityIcon(alert.predicted_severity)}
                  </Box>
                  <Typography variant="subtitle2" fontWeight="bold">
                    {alert.predicted_conflict_type?.replace(/_/g, ' ').toUpperCase()}
                  </Typography>
                </Box>
                <Chip 
                  label={`${(alert.confidence * 100).toFixed(0)}%`}
                  size="small"
                  sx={{ 
                    bgcolor: getConfidenceBadgeColor(alert.confidence),
                    color: 'white',
                    fontWeight: 'bold'
                  }}
                />
              </Box>

              <Typography variant="body2" sx={{ mb: 1, opacity: 0.9 }}>
                {alert.explanation}
              </Typography>

              <Box sx={{ width: '100%', display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                <Chip 
                  icon={<ScheduleIcon sx={{ color: 'white !important', fontSize: 16 }} />}
                  label={formatTimeToConflict(alert.time_to_conflict_minutes)}
                  size="small"
                  sx={{ 
                    bgcolor: 'rgba(255,255,255,0.2)', 
                    color: 'white',
                    fontWeight: 600,
                    fontSize: '0.75rem'
                  }}
                />
                <Chip 
                  label={`📍 ${alert.predicted_location}`}
                  size="small"
                  sx={{ 
                    bgcolor: 'rgba(255,255,255,0.2)', 
                    color: 'white',
                    fontWeight: 600,
                    fontSize: '0.75rem'
                  }}
                />
                <Chip 
                  label={alert.predicted_severity?.toUpperCase()}
                  size="small"
                  sx={{
                    bgcolor: getSeverityColor(alert.predicted_severity),
                    color: 'white',
                    fontWeight: 'bold',
                    fontSize: '0.75rem'
                  }}
                />
              </Box>

              {alert.recommended_actions && alert.recommended_actions.length > 0 && (
                <Box sx={{ mt: 1.5, width: '100%' }}>
                  <Typography variant="caption" sx={{ opacity: 0.8, display: 'block', mb: 0.5, fontWeight: 600 }}>
                    💡 Recommended Actions:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {alert.recommended_actions.map((action, i) => (
                      <Chip 
                        key={i}
                        label={action.replace(/_/g, ' ')}
                        size="small"
                        sx={{ 
                          bgcolor: 'rgba(102, 187, 106, 0.3)',
                          color: 'white',
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          border: '1px solid rgba(102, 187, 106, 0.4)'
                        }}
                      />
                    ))}
                  </Box>
                </Box>
              )}

              <Typography variant="caption" sx={{ mt: 1, opacity: 0.5 }}>
                Match: {(alert.similarity_score * 100).toFixed(1)}% similar to pattern {alert.matching_pattern_id?.substring(0, 8)}...
              </Typography>
            </ListItem>
          ))}
        </List>
      )}

      {/* Last Update */}
      {lastUpdate && (
        <Typography variant="caption" sx={{ display: 'block', mt: 2, opacity: 0.6, textAlign: 'center' }}>
          Last updated: {lastUpdate.toLocaleTimeString()}
        </Typography>
      )}

      {/* Error Notification */}
      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setError(null)} severity="error" sx={{ width: '100%' }}>
          {error}
        </Alert>
      </Snackbar>

      {/* Success Notification */}
      <Snackbar
        open={!!successMessage}
        autoHideDuration={3000}
        onClose={() => setSuccessMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={() => setSuccessMessage(null)} severity="success" sx={{ width: '100%' }}>
          {successMessage}
        </Alert>
      </Snackbar>
    </Paper>
  );
}

export default PreConflictAlerts;
