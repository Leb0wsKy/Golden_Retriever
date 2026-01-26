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
} from '@mui/material';
import {
  Warning as WarningIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  CheckCircle as CheckCircleIcon,
  Close as CloseIcon,
  NotificationsActive as NotificationsIcon,
} from '@mui/icons-material';

function Alerts() {
  const [alerts, setAlerts] = useState([
    {
      id: 1,
      type: 'error',
      title: 'Critical System Alert',
      message: 'Train #2547 exceeded speed limit at sector B-12',
      timestamp: new Date().toISOString(),
      visible: true,
    },
    {
      id: 2,
      type: 'warning',
      title: 'Maintenance Required',
      message: 'Track maintenance scheduled for tomorrow at 03:00 AM',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      visible: true,
    },
    {
      id: 3,
      type: 'info',
      title: 'System Update',
      message: 'AI model training completed successfully',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      visible: true,
    },
    {
      id: 4,
      type: 'success',
      title: 'All Systems Operational',
      message: 'Network monitoring is running smoothly',
      timestamp: new Date(Date.now() - 10800000).toISOString(),
      visible: true,
    },
  ]);

  const [stats, setStats] = useState({
    critical: 1,
    warnings: 1,
    info: 2,
  });

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
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 3, fontWeight: 600, color: '#2c3e50' }}>
        System Alerts & Notifications
      </Typography>

      {/* Alert Statistics */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              background: 'linear-gradient(135deg, #fee2e2 0%, #fecaca 100%)',
              borderRadius: 2,
              border: '1px solid #fca5a5',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box>
                <Typography variant="h3" sx={{ fontWeight: 700, color: '#dc2626' }}>
                  {stats.critical}
                </Typography>
                <Typography variant="body2" sx={{ color: '#991b1b', mt: 1 }}>
                  Critical Alerts
                </Typography>
              </Box>
              <ErrorIcon sx={{ fontSize: 48, color: '#dc2626', opacity: 0.7 }} />
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
              borderRadius: 2,
              border: '1px solid #fcd34d',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box>
                <Typography variant="h3" sx={{ fontWeight: 700, color: '#d97706' }}>
                  {stats.warnings}
                </Typography>
                <Typography variant="body2" sx={{ color: '#92400e', mt: 1 }}>
                  Warnings
                </Typography>
              </Box>
              <WarningIcon sx={{ fontSize: 48, color: '#d97706', opacity: 0.7 }} />
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <Paper
            elevation={0}
            sx={{
              p: 3,
              background: 'linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%)',
              borderRadius: 2,
              border: '1px solid #93c5fd',
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Box>
                <Typography variant="h3" sx={{ fontWeight: 700, color: '#2563eb' }}>
                  {stats.info}
                </Typography>
                <Typography variant="body2" sx={{ color: '#1e40af', mt: 1 }}>
                  Information
                </Typography>
              </Box>
              <InfoIcon sx={{ fontSize: 48, color: '#2563eb', opacity: 0.7 }} />
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* Recent Alerts */}
      <Paper elevation={0} sx={{ p: 3, borderRadius: 2, border: '1px solid #e5e7eb' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <NotificationsIcon sx={{ mr: 1, color: '#0891b2' }} />
          <Typography variant="h6" sx={{ fontWeight: 600, color: '#2c3e50' }}>
            Recent Alerts
          </Typography>
        </Box>

        <List>
          {alerts.filter(alert => alert.visible).map((alert, index) => (
            <React.Fragment key={alert.id}>
              <Collapse in={alert.visible}>
                <ListItem
                  sx={{
                    borderRadius: 1,
                    mb: 1,
                    '&:hover': { bgcolor: '#f9fafb' },
                  }}
                  secondaryAction={
                    <IconButton
                      edge="end"
                      aria-label="close"
                      onClick={() => handleClose(alert.id)}
                      size="small"
                    >
                      <CloseIcon />
                    </IconButton>
                  }
                >
                  <Alert
                    severity={alert.type}
                    icon={getSeverityIcon(alert.type)}
                    sx={{
                      width: '100%',
                      border: 'none',
                      '& .MuiAlert-message': { width: '100%' },
                    }}
                  >
                    <AlertTitle sx={{ fontWeight: 600 }}>{alert.title}</AlertTitle>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      {alert.message}
                    </Typography>
                    <Chip
                      label={formatTimestamp(alert.timestamp)}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '0.7rem',
                        bgcolor: 'rgba(0,0,0,0.05)',
                      }}
                    />
                  </Alert>
                </ListItem>
              </Collapse>
              {index < alerts.filter(a => a.visible).length - 1 && <Divider sx={{ my: 1 }} />}
            </React.Fragment>
          ))}
        </List>

        {alerts.filter(a => a.visible).length === 0 && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <CheckCircleIcon sx={{ fontSize: 64, color: '#10b981', opacity: 0.5, mb: 2 }} />
            <Typography variant="h6" color="textSecondary">
              No Active Alerts
            </Typography>
            <Typography variant="body2" color="textSecondary">
              All systems are running smoothly
            </Typography>
          </Box>
        )}
      </Paper>
    </Box>
  );
}

export default Alerts;
