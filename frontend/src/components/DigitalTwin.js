import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Chip,
  LinearProgress,
  Divider,
  IconButton,
  Tabs,
  Tab,
  Alert,
} from '@mui/material';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { 
  DeviceHub as DeviceHubIcon,
  CloudSync as SyncIcon,
  Speed as SpeedIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Schedule as ScheduleIcon,
  TrendingUp as TrendingUpIcon,
  Memory as MemoryIcon,
  ViewInAr as ViewInArIcon,
  Insights as InsightsIcon,
  ShowChart as ShowChartIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import axios from 'axios';

function DigitalTwin() {
  const [activeTab, setActiveTab] = useState(0);
  const [syncStatus, setSyncStatus] = useState('synced');
  const [performanceData, setPerformanceData] = useState([]);
  const [predictiveData, setPredictiveData] = useState([]);
  const [twinMetrics, setTwinMetrics] = useState({
    syncAccuracy: 98.5,
    dataLatency: 45,
    prediction_accuracy: 94.2,
    activeModels: 5,
    anomaliesDetected: 2,
    lastSync: new Date().toISOString(),
  });

  // Sample data for charts
  const networkHealthData = [
    { time: '00:00', health: 98, load: 45, incidents: 0 },
    { time: '04:00', health: 97, load: 32, incidents: 1 },
    { time: '08:00', health: 95, load: 78, incidents: 2 },
    { time: '12:00', health: 96, load: 85, incidents: 1 },
    { time: '16:00', health: 94, load: 92, incidents: 3 },
    { time: '20:00', health: 97, load: 68, incidents: 1 },
  ];

  const predictionData = [
    { hour: '1h', actual: 45, predicted: 47 },
    { hour: '2h', actual: 52, predicted: 50 },
    { hour: '3h', actual: 48, predicted: 49 },
    { hour: '4h', actual: null, predicted: 55 },
    { hour: '5h', actual: null, predicted: 58 },
    { hour: '6h', actual: null, predicted: 62 },
  ];

  const systemStatusData = [
    { name: 'Operational', value: 87, color: '#10b981' },
    { name: 'Maintenance', value: 8, color: '#f59e0b' },
    { name: 'Critical', value: 5, color: '#ef4444' },
  ];

  const anomalyData = [
    { id: 1, type: 'Speed Anomaly', train: 'Train #2547', severity: 'high', time: '2m ago' },
    { id: 2, type: 'Route Deviation', train: 'Train #3821', severity: 'medium', time: '15m ago' },
  ];

  useEffect(() => {
    fetchTwinData();
    const interval = setInterval(fetchTwinData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchTwinData = async () => {
    try {
      const response = await axios.get('/api/digital-twin/status');
      // Update with real data when available
      setSyncStatus('synced');
    } catch (error) {
      console.error('Error fetching twin data:', error);
      setSyncStatus('error');
    }
  };

  const getSyncStatusColor = () => {
    switch (syncStatus) {
      case 'synced': return '#10b981';
      case 'syncing': return '#f59e0b';
      case 'error': return '#ef4444';
      default: return '#6b7280';
    }
  };

  const getSyncStatusText = () => {
    switch (syncStatus) {
      case 'synced': return 'Synchronized';
      case 'syncing': return 'Synchronizing...';
      case 'error': return 'Connection Error';
      default: return 'Unknown';
    }
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
          <DeviceHubIcon sx={{ mr: 1.5, fontSize: 40, color: '#0891b2' }} />
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#1e40af' }}>
              Digital Twin
            </Typography>
            <Typography variant="caption" sx={{ color: '#64748b', fontWeight: 500 }}>
              Real-time network replication & predictive analytics
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Chip
            icon={<SyncIcon />}
            label={getSyncStatusText()}
            sx={{
              bgcolor: getSyncStatusColor(),
              color: 'white',
              fontWeight: 600,
              '& .MuiChip-icon': { color: 'white' }
            }}
          />
          <IconButton
            sx={{
              bgcolor: 'white',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              '&:hover': { bgcolor: '#f8f9fa' }
            }}
            onClick={fetchTwinData}
          >
            <RefreshIcon sx={{ color: '#0891b2' }} />
          </IconButton>
        </Box>
      </Box>

      {/* Key Metrics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{
            background: 'linear-gradient(135deg, #1e40af 0%, #0891b2 100%)',
            color: 'white',
            borderRadius: 3,
            boxShadow: '0 8px 32px rgba(30, 64, 175, 0.2)',
          }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.9, mb: 1, fontWeight: 500 }}>
                    Sync Accuracy
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-1px' }}>
                    {twinMetrics.syncAccuracy}%
                  </Typography>
                </Box>
                <CheckCircleIcon sx={{ fontSize: 40, opacity: 0.7 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{
            background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)',
            color: 'white',
            borderRadius: 3,
            boxShadow: '0 8px 32px rgba(16, 185, 129, 0.2)',
          }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.9, mb: 1, fontWeight: 500 }}>
                    Data Latency
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-1px' }}>
                    {twinMetrics.dataLatency}ms
                  </Typography>
                </Box>
                <SpeedIcon sx={{ fontSize: 40, opacity: 0.7 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{
            background: 'linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%)',
            color: 'white',
            borderRadius: 3,
            boxShadow: '0 8px 32px rgba(124, 58, 237, 0.2)',
          }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.9, mb: 1, fontWeight: 500 }}>
                    Prediction Accuracy
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-1px' }}>
                    {twinMetrics.prediction_accuracy}%
                  </Typography>
                </Box>
                <TrendingUpIcon sx={{ fontSize: 40, opacity: 0.7 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{
            background: 'linear-gradient(135deg, #dc2626 0%, #f87171 100%)',
            color: 'white',
            borderRadius: 3,
            boxShadow: '0 8px 32px rgba(220, 38, 38, 0.2)',
          }}>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Box>
                  <Typography variant="body2" sx={{ opacity: 0.9, mb: 1, fontWeight: 500 }}>
                    Anomalies Detected
                  </Typography>
                  <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-1px' }}>
                    {twinMetrics.anomaliesDetected}
                  </Typography>
                </Box>
                <WarningIcon sx={{ fontSize: 40, opacity: 0.7 }} />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Paper sx={{
        bgcolor: 'white',
        borderRadius: 3,
        boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
        border: '1px solid rgba(0,0,0,0.05)',
        mb: 3
      }}>
        <Tabs
          value={activeTab}
          onChange={(e, newValue) => setActiveTab(newValue)}
          sx={{
            borderBottom: 1,
            borderColor: 'divider',
            '& .MuiTab-root': {
              fontWeight: 600,
              textTransform: 'none',
              fontSize: '1rem',
            },
            '& .Mui-selected': {
              color: '#0891b2 !important',
            },
            '& .MuiTabs-indicator': {
              backgroundColor: '#0891b2',
              height: 3,
            }
          }}
        >
          <Tab icon={<ShowChartIcon />} iconPosition="start" label="Real-Time Analytics" />
          <Tab icon={<InsightsIcon />} iconPosition="start" label="Predictive Models" />
          <Tab icon={<ViewInArIcon />} iconPosition="start" label="System Status" />
        </Tabs>
      </Paper>

      {/* Tab Content */}
      {activeTab === 0 && (
        <Grid container spacing={3}>
          <Grid item xs={12} lg={8}>
            <Paper sx={{
              p: 3,
              bgcolor: 'white',
              borderRadius: 3,
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
              border: '1px solid rgba(0,0,0,0.05)',
            }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#1e40af', mb: 3 }}>
                Network Health Over Time
              </Typography>
              <ResponsiveContainer width="100%" height={350}>
                <AreaChart data={networkHealthData}>
                  <defs>
                    <linearGradient id="healthGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0891b2" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#0891b2" stopOpacity={0.1}/>
                    </linearGradient>
                    <linearGradient id="loadGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.1}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="time" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="health" stroke="#0891b2" fillOpacity={1} fill="url(#healthGradient)" name="Health %" />
                  <Area type="monotone" dataKey="load" stroke="#f59e0b" fillOpacity={1} fill="url(#loadGradient)" name="Load %" />
                </AreaChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>

          <Grid item xs={12} lg={4}>
            <Paper sx={{
              p: 3,
              bgcolor: 'white',
              borderRadius: 3,
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
              border: '1px solid rgba(0,0,0,0.05)',
              height: '100%',
            }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#1e40af', mb: 3 }}>
                Detected Anomalies
              </Typography>
              {anomalyData.map((anomaly) => (
                <Alert
                  key={anomaly.id}
                  severity={anomaly.severity === 'high' ? 'error' : 'warning'}
                  sx={{ mb: 2, borderRadius: 2 }}
                >
                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
                    {anomaly.type}
                  </Typography>
                  <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>
                    {anomaly.train} • {anomaly.time}
                  </Typography>
                </Alert>
              ))}
              <Box sx={{ mt: 3, p: 2, bgcolor: '#f0fdf4', borderRadius: 2, border: '1px solid #86efac' }}>
                <Typography variant="body2" sx={{ color: '#166534', fontWeight: 600 }}>
                  ✓ All critical systems operational
                </Typography>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      )}

      {activeTab === 1 && (
        <Grid container spacing={3}>
          <Grid item xs={12} lg={8}>
            <Paper sx={{
              p: 3,
              bgcolor: 'white',
              borderRadius: 3,
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
              border: '1px solid rgba(0,0,0,0.05)',
            }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#1e40af', mb: 3 }}>
                Traffic Prediction (Next 6 Hours)
              </Typography>
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={predictionData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="hour" stroke="#64748b" />
                  <YAxis stroke="#64748b" />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="actual" stroke="#0891b2" strokeWidth={3} name="Actual Traffic" />
                  <Line type="monotone" dataKey="predicted" stroke="#7c3aed" strokeWidth={3} strokeDasharray="5 5" name="Predicted Traffic" />
                </LineChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>

          <Grid item xs={12} lg={4}>
            <Paper sx={{
              p: 3,
              bgcolor: 'white',
              borderRadius: 3,
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
              border: '1px solid rgba(0,0,0,0.05)',
            }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#1e40af', mb: 3 }}>
                Active ML Models
              </Typography>
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>Anomaly Detection</Typography>
                  <Typography variant="body2" sx={{ color: '#10b981', fontWeight: 700 }}>Active</Typography>
                </Box>
                <LinearProgress variant="determinate" value={96} sx={{ height: 8, borderRadius: 4, bgcolor: '#e5e7eb', '& .MuiLinearProgress-bar': { bgcolor: '#10b981' } }} />
                <Typography variant="caption" sx={{ color: '#64748b' }}>96% accuracy</Typography>
              </Box>
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>Traffic Forecasting</Typography>
                  <Typography variant="body2" sx={{ color: '#10b981', fontWeight: 700 }}>Active</Typography>
                </Box>
                <LinearProgress variant="determinate" value={94} sx={{ height: 8, borderRadius: 4, bgcolor: '#e5e7eb', '& .MuiLinearProgress-bar': { bgcolor: '#7c3aed' } }} />
                <Typography variant="caption" sx={{ color: '#64748b' }}>94% accuracy</Typography>
              </Box>
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>Maintenance Prediction</Typography>
                  <Typography variant="body2" sx={{ color: '#10b981', fontWeight: 700 }}>Active</Typography>
                </Box>
                <LinearProgress variant="determinate" value={91} sx={{ height: 8, borderRadius: 4, bgcolor: '#e5e7eb', '& .MuiLinearProgress-bar': { bgcolor: '#0891b2' } }} />
                <Typography variant="caption" sx={{ color: '#64748b' }}>91% accuracy</Typography>
              </Box>
              <Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>Route Optimization</Typography>
                  <Typography variant="body2" sx={{ color: '#10b981', fontWeight: 700 }}>Active</Typography>
                </Box>
                <LinearProgress variant="determinate" value={88} sx={{ height: 8, borderRadius: 4, bgcolor: '#e5e7eb', '& .MuiLinearProgress-bar': { bgcolor: '#f59e0b' } }} />
                <Typography variant="caption" sx={{ color: '#64748b' }}>88% accuracy</Typography>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      )}

      {activeTab === 2 && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper sx={{
              p: 3,
              bgcolor: 'white',
              borderRadius: 3,
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
              border: '1px solid rgba(0,0,0,0.05)',
            }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#1e40af', mb: 3 }}>
                System Distribution
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={systemStatusData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name}: ${value}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {systemStatusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>

          <Grid item xs={12} md={6}>
            <Paper sx={{
              p: 3,
              bgcolor: 'white',
              borderRadius: 3,
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
              border: '1px solid rgba(0,0,0,0.05)',
            }}>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#1e40af', mb: 3 }}>
                Twin Synchronization Status
              </Typography>
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>Physical Network Data</Typography>
                  <Chip label="Synced" size="small" sx={{ bgcolor: '#10b981', color: 'white', fontWeight: 600 }} />
                </Box>
                <LinearProgress variant="determinate" value={100} sx={{ height: 8, borderRadius: 4, bgcolor: '#e5e7eb', '& .MuiLinearProgress-bar': { bgcolor: '#10b981' } }} />
              </Box>
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>Sensor Network</Typography>
                  <Chip label="Synced" size="small" sx={{ bgcolor: '#10b981', color: 'white', fontWeight: 600 }} />
                </Box>
                <LinearProgress variant="determinate" value={100} sx={{ height: 8, borderRadius: 4, bgcolor: '#e5e7eb', '& .MuiLinearProgress-bar': { bgcolor: '#10b981' } }} />
              </Box>
              <Box sx={{ mb: 3 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>Historical Database</Typography>
                  <Chip label="Syncing" size="small" sx={{ bgcolor: '#f59e0b', color: 'white', fontWeight: 600 }} />
                </Box>
                <LinearProgress variant="determinate" value={75} sx={{ height: 8, borderRadius: 4, bgcolor: '#e5e7eb', '& .MuiLinearProgress-bar': { bgcolor: '#f59e0b' } }} />
              </Box>
              <Divider sx={{ my: 2 }} />
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="caption" sx={{ color: '#64748b', display: 'block' }}>Last Sync</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600, color: '#1e40af' }}>
                    {new Date(twinMetrics.lastSync).toLocaleTimeString()}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ color: '#64748b', display: 'block' }}>Active Models</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600, color: '#1e40af' }}>
                    {twinMetrics.activeModels} / 5
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="caption" sx={{ color: '#64748b', display: 'block' }}>Data Points</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600, color: '#1e40af' }}>
                    1.2M+
                  </Typography>
                </Box>
              </Box>
            </Paper>
          </Grid>
        </Grid>
      )}
    </Box>
  );
}

export default DigitalTwin;
