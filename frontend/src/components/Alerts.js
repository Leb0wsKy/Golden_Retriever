import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  Alert,
  AlertTitle,
  Chip,
  IconButton,
  Collapse,
  List,
  ListItem,
  ListItemText,
  Divider,
  CircularProgress,
  Button,
  Tooltip,
} from '@mui/material';
import {
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  Close as CloseIcon,
  NotificationsActive as NotificationsIcon,
  Refresh as RefreshIcon,
  TravelExplore as TravelExploreIcon,
  Train as TrainIcon,
} from '@mui/icons-material';
import axios from 'axios';

function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    severe: 0,
    moderate: 0,
    minor: 0,
  });
  const [trainsAnalyzed, setTrainsAnalyzed] = useState(0);
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    fetchLiveAlerts();
    // Refresh alerts every 30 seconds
    const interval = setInterval(fetchLiveAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchLiveAlerts = async () => {
    try {
      setLoading(true); // Show loading state
      const response = await axios.get('/api/alerts/live', {
        params: {
          severity: 'minor', // Show all severities
          limit: 100,
          maxAge: 7200000 // 2 hours
        }
      });
      
      // Transform backend alerts to frontend format
      const transformedAlerts = response.data.alerts.map(alert => ({
        id: alert.id,
        type: mapSeverityToType(alert.severity),
        severity: alert.severity,
        title: formatAlertTitle(alert),
        message: alert.conflict,
        solution: alert.solution,
        confidence: alert.confidence,
        train: alert.train,
        timestamp: alert.timestamp,
        visible: true,
        conflictType: alert.conflictType,
        usingAI: alert.usingAI,
      }));
      
      setAlerts(transformedAlerts);
      setStats(response.data.stats.bySeverity);
      setTrainsAnalyzed(response.data.trainsAnalyzed);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (error) {
      console.error('Error fetching live alerts:', error);
      setLoading(false);
    }
  };

  const mapSeverityToType = (severity) => {
    switch (severity) {
      case 'severe': return 'error';
      case 'moderate': return 'warning';
      case 'minor': return 'info';
      default: return 'info';
    }
  };

  const formatAlertTitle = (alert) => {
    const typeLabels = {
      'delay': 'Train Delay',
      'cancellation': 'Service Cancellation',
      'weather': 'Weather Alert',
      'incident': 'Incident Report',
      'congestion': 'Congestion Alert',
      'speed_restriction': 'Speed Restriction',
      'track_maintenance': 'Track Maintenance',
    };
    
    const label = typeLabels[alert.conflictType] || 'System Alert';
    return `${label} - ${alert.train?.name || alert.train?.route || 'Unknown'}`;
  };

  const handleClose = (id) => {
    setAlerts(alerts.map(alert => 
      alert.id === id ? { ...alert, visible: false } : alert
    ));
  };

  const getSeverityIcon = (type) => {
    switch (type) {
      case 'error':
        return <ErrorIcon />;
      case 'warning':
        return <WarningIcon />;
      case 'info':
        return <InfoIcon />;
      case 'success':
        return <CheckCircleIcon />;
      default:
        return <InfoIcon />;
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
  };

  return (
    <Box sx={{ 
      bgcolor: '#f8f9fa', 
      minHeight: '100vh', 
      p: { xs: 2, md: 4 },
      background: 'linear-gradient(180deg, #e3f2fd 0%, #f8f9fa 100%)'
    }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <NotificationsIcon sx={{ mr: 1.5, fontSize: 40, color: '#0891b2' }} />
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#1e40af' }}>
              Live Train Alerts
            </Typography>
            <Typography variant="caption" sx={{ color: '#64748b' }}>
              {lastUpdate && `Last updated: ${lastUpdate.toLocaleTimeString()}`}
              {trainsAnalyzed > 0 && ` • ${trainsAnalyzed} trains monitored`}
            </Typography>
          </Box>
        </Box>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={fetchLiveAlerts}
          disabled={loading}
          sx={{ 
            borderColor: '#0891b2', 
            color: '#0891b2',
            '&:hover': { borderColor: '#0e7490', bgcolor: '#e0f2fe' }
          }}
        >
          Refresh
        </Button>
      </Box>

      {/* Alert Statistics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)',
              borderRadius: 3,
              border: '1px solid rgba(252, 165, 165, 0.3)',
              boxShadow: '0 8px 32px rgba(220, 38, 38, 0.1)',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 12px 48px rgba(220, 38, 38, 0.15)',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box>
                <Typography variant="h3" sx={{ fontWeight: 900, color: '#dc2626', letterSpacing: '-1px' }}>
                  {stats.severe || 0}
                </Typography>
                <Typography variant="body2" sx={{ color: '#991b1b', mt: 1, fontWeight: 600 }}>
                  Severe Alerts
                </Typography>
              </Box>
              <ErrorIcon sx={{ fontSize: 56, color: '#dc2626', opacity: 0.6 }} />
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
              borderRadius: 3,
              border: '1px solid rgba(252, 211, 77, 0.3)',
              boxShadow: '0 8px 32px rgba(217, 119, 6, 0.1)',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 12px 48px rgba(217, 119, 6, 0.15)',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box>
                <Typography variant="h3" sx={{ fontWeight: 900, color: '#d97706', letterSpacing: '-1px' }}>
                  {stats.moderate || 0}
                </Typography>
                <Typography variant="body2" sx={{ color: '#92400e', mt: 1, fontWeight: 600 }}>
                  Moderate Alerts
                </Typography>
              </Box>
              <WarningIcon sx={{ fontSize: 56, color: '#d97706', opacity: 0.6 }} />
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              background: 'linear-gradient(135deg, #1e40af 0%, #0891b2 100%)',
              borderRadius: 3,
              border: '1px solid rgba(8, 145, 178, 0.3)',
              boxShadow: '0 8px 32px rgba(30, 64, 175, 0.15)',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: '0 12px 48px rgba(30, 64, 175, 0.25)',
              },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box>
                <Typography variant="h3" sx={{ fontWeight: 900, color: 'white', letterSpacing: '-1px' }}>
                  {stats.minor || 0}
                </Typography>
                <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.9)', mt: 1, fontWeight: 600 }}>
                  Minor Alerts
                </Typography>
              </Box>
              <InfoIcon sx={{ fontSize: 56, color: 'white', opacity: 0.8 }} />
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Loading State */}
      {loading && alerts.length === 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 8 }}>
          <CircularProgress sx={{ color: '#0891b2' }} />
          <Typography sx={{ ml: 2, color: '#64748b' }}>
            Analyzing live train data...
          </Typography>
        </Box>
      )}

      {/* Alerts List */}
      {!loading && alerts.length === 0 && (
        <Paper
          elevation={0}
          sx={{
            p: 4,
            textAlign: 'center',
            background: 'linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%)',
            borderRadius: 3,
            border: '1px solid rgba(34, 197, 94, 0.3)',
          }}
        >
          <CheckCircleIcon sx={{ fontSize: 64, color: '#22c55e', mb: 2 }} />
          <Typography variant="h6" sx={{ fontWeight: 700, color: '#166534', mb: 1 }}>
            All Systems Operating Normally
          </Typography>
          <Typography variant="body2" sx={{ color: '#15803d' }}>
            No alerts detected from current train operations
          </Typography>
        </Paper>
      )}

      {/* Alerts List */}
      <Grid container spacing={2}>
        {alerts.filter(alert => alert.visible).map((alert) => (
          <Grid item xs={12} key={alert.id}>
            <Collapse in={alert.visible}>
              <Paper
                elevation={0}
                sx={{
                  p: 2.5,
                  borderRadius: 2,
                  border: '1px solid rgba(0,0,0,0.08)',
                  bgcolor: 'white',
                  transition: 'all 0.2s',
                  '&:hover': {
                    boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
                    transform: 'translateY(-2px)',
                  },
                }}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <Box sx={{ flex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      {getSeverityIcon(alert.type)}
                      <Typography variant="h6" sx={{ fontWeight: 700, color: '#1e40af' }}>
                        {alert.title}
                      </Typography>
                      <Chip 
                        label={alert.severity.toUpperCase()} 
                        size="small" 
                        color={alert.type}
                        sx={{ fontWeight: 700, fontSize: '0.7rem' }}
                      />
                      {alert.usingAI && alert.confidence > 0.6 && (
                        <Tooltip title={`AI Confidence: ${(alert.confidence * 100).toFixed(0)}%`}>
                          <Chip 
                            icon={<TravelExploreIcon sx={{ fontSize: 14 }} />}
                            label="AI Solution" 
                            size="small" 
                            sx={{ 
                              bgcolor: '#dcfce7', 
                              color: '#166534',
                              fontWeight: 600,
                              fontSize: '0.7rem'
                            }}
                          />
                        </Tooltip>
                      )}
                    </Box>
                    
                    <Typography variant="body1" sx={{ color: '#475569', mb: 2 }}>
                      {alert.message}
                    </Typography>
                    
                    {alert.solution && (
                      <Box sx={{ 
                        bgcolor: '#f0f9ff', 
                        p: 2, 
                        borderRadius: 1, 
                        borderLeft: '4px solid #0891b2',
                        mb: 2
                      }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: '#0e7490', mb: 0.5 }}>
                          Recommended Action:
                        </Typography>
                        <Typography variant="body2" sx={{ color: '#0c4a6e' }}>
                          {alert.solution}
                        </Typography>
                      </Box>
                    )}
                    
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                      {alert.train && (
                        <>
                          {alert.train.name && (
                            <Chip
                              icon={<TrainIcon sx={{ fontSize: 14 }} />}
                              label={alert.train.name}
                              size="small"
                              variant="outlined"
                              sx={{ fontSize: '0.75rem' }}
                            />
                          )}
                          {alert.train.route && (
                            <Chip
                              label={`Route: ${alert.train.route}`}
                              size="small"
                              variant="outlined"
                              sx={{ fontSize: '0.75rem' }}
                            />
                          )}
                          {alert.train.agency && (
                            <Chip
                              label={alert.train.agency}
                              size="small"
                              variant="outlined"
                              sx={{ fontSize: '0.75rem' }}
                            />
                          )}
                        </>
                      )}
                      <Chip
                        label={formatTimestamp(alert.timestamp)}
                        size="small"
                        sx={{
                          fontSize: '0.7rem',
                          bgcolor: 'rgba(0,0,0,0.05)',
                        }}
                      />
                    </Box>
                  </Box>
                  
                  <IconButton
                    size="small"
                    onClick={() => handleClose(alert.id)}
                    sx={{ ml: 1 }}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </Box>
              </Paper>
            </Collapse>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

export default Alerts;
