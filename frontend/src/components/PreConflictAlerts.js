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
      const response = await axios.get('http://localhost:8000/api/v1/preventive-alerts/');
      // API returns array directly, not wrapped in {alerts: [...]}
      setAlerts(Array.isArray(response.data) ? response.data : []);
      setLastUpdate(new Date());
      setLoading(false);
      setError(null); // Clear any previous errors
    } catch (error) {
      console.error('Error fetching preventive alerts:', error);
      setError('Failed to fetch alerts. Please check if the API is running.');
      setLoading(false);
    }
  };

  const fetchScannerStatus = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/v1/preventive-alerts/health');
      setScannerStatus(response.data);
    } catch (error) {
      console.error('Error fetching scanner status:', error);
      // Don't show error for status check - it's not critical
    }
  };

  const handleManualScan = async () => {
    try {
      setLoading(true);
      await axios.post('http://localhost:8000/api/v1/preventive-alerts/scan', {
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

  const getSeverityColor = (confidence) => {
    if (confidence >= 0.65) return 'error';    // High confidence (65%+)
    if (confidence >= 0.45) return 'warning';  // Medium confidence (45-65%)
    return 'info';                              // Lower confidence (30-45%)
  };

  const getSeverityIcon = (confidence) => {
    if (confidence >= 0.65) return <ErrorIcon />;    // High confidence
    if (confidence >= 0.45) return <WarningIcon />;  // Medium confidence
    return <TrendingUpIcon />;                        // Lower confidence
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
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white'
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningIcon sx={{ fontSize: 28 }} />
          <Typography variant="h6" fontWeight="bold">
            Pre-Conflict Alerts
          </Typography>
        </Box>
        <Tooltip title="Trigger manual scan">
          <IconButton 
            onClick={handleManualScan} 
            disabled={loading}
            sx={{ color: 'white' }}
          >
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Scanner Status */}
      {scannerStatus && (
        <Box sx={{ mb: 2, p: 1.5, bgcolor: 'rgba(255,255,255,0.1)', borderRadius: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="body2">
              Scanner Status: <strong>{scannerStatus.status}</strong>
            </Typography>
            {scannerStatus.status === 'healthy' && (
              <CheckCircleIcon sx={{ color: '#4caf50' }} />
            )}
          </Box>
          <Typography variant="caption" sx={{ opacity: 0.8 }}>
            Threshold: {(scannerStatus.similarity_threshold * 100).toFixed(0)}% similarity
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
                bgcolor: 'rgba(255,255,255,0.1)', 
                borderRadius: 1, 
                mb: 1.5,
                flexDirection: 'column',
                alignItems: 'flex-start'
              }}
            >
              <Box sx={{ width: '100%', display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  {getSeverityIcon(alert.confidence)}
                  <Typography variant="subtitle2" fontWeight="bold">
                    {alert.predicted_conflict_type?.replace(/_/g, ' ').toUpperCase()}
                  </Typography>
                </Box>
                <Chip 
                  label={`${(alert.confidence * 100).toFixed(0)}% confidence`}
                  size="small"
                  sx={{ 
                    bgcolor: 'rgba(255,255,255,0.2)',
                    color: 'white',
                    fontWeight: 'bold'
                  }}
                />
              </Box>

              <Typography variant="body2" sx={{ mb: 1, opacity: 0.9 }}>
                {alert.explanation}
              </Typography>

              <Box sx={{ width: '100%', display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Chip 
                  icon={<ScheduleIcon sx={{ color: 'white !important' }} />}
                  label={formatTimeToConflict(alert.time_to_conflict_minutes)}
                  size="small"
                  sx={{ bgcolor: 'rgba(255,255,255,0.15)', color: 'white' }}
                />
                <Chip 
                  label={alert.predicted_location}
                  size="small"
                  sx={{ bgcolor: 'rgba(255,255,255,0.15)', color: 'white' }}
                />
                <Chip 
                  label={alert.predicted_severity}
                  size="small"
                  color={getSeverityColor(alert.confidence)}
                />
              </Box>

              {alert.recommended_actions && alert.recommended_actions.length > 0 && (
                <Box sx={{ mt: 1.5, width: '100%' }}>
                  <Typography variant="caption" sx={{ opacity: 0.7, display: 'block', mb: 0.5 }}>
                    Recommended Actions:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                    {alert.recommended_actions.map((action, i) => (
                      <Chip 
                        key={i}
                        label={action.replace(/_/g, ' ')}
                        size="small"
                        sx={{ 
                          bgcolor: 'rgba(76, 175, 80, 0.2)',
                          color: 'white',
                          fontSize: '0.7rem'
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
