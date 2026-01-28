import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Chip,
  Alert,
  AlertTitle,
  IconButton,
  Tabs,
  Tab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  Badge,
  Divider,
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
  Tooltip as RechartsTooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import {
  NetworkCheck as NetworkCheckIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  TrendingUp as TrendingUpIcon,
  TrendingDown as TrendingDownIcon,
  Refresh as RefreshIcon,
  Add as AddIcon,
  ThumbUp as ThumbUpIcon,
  ShowChart as ShowChartIcon,
  RateReview as RateReviewIcon,
} from '@mui/icons-material';
import axios from 'axios';
import FeedbackModal from './FeedbackModal';

function NetworkMonitoring() {
  const [loading, setLoading] = useState(true);
  const [networks, setNetworks] = useState([]);
  const [selectedNetwork, setSelectedNetwork] = useState(null);
  const [networkRiskData, setNetworkRiskData] = useState(null);
  const [conflicts, setConflicts] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [openConflictDialog, setOpenConflictDialog] = useState(false);
  const [openFeedbackModal, setOpenFeedbackModal] = useState(false);
  const [feedbackConflict, setFeedbackConflict] = useState({ id: '', strategy: '' });
  const [activeTab, setActiveTab] = useState(0);

  // Form state for creating conflicts
  const [conflictForm, setConflictForm] = useState({
    conflict_type: 'headway_conflict',
    station: '',
    time_of_day: 'evening_peak',
    severity: 'high',
    affected_trains: '',
    description: '',
    delay_before: 10,
    platform: '',
    network_id: '',
  });

  useEffect(() => {
    fetchNetworksSummary();
    fetchConflicts();
    const interval = setInterval(() => {
      fetchNetworksSummary();
      fetchConflicts();
    }, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedNetwork) {
      fetchNetworkRisk(selectedNetwork);
    }
  }, [selectedNetwork]);

  const fetchNetworksSummary = async () => {
    try {
      const response = await axios.get('/api/conflicts/networks-summary');
      setNetworks(response.data.networks || []);
      if (!selectedNetwork && response.data.networks?.length > 0) {
        setSelectedNetwork(response.data.networks[0].network_id);
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching networks:', error);
      setLoading(false);
    }
  };

  const fetchNetworkRisk = async (networkId) => {
    try {
      const response = await axios.post('/api/conflicts/network-risk', {
        network_id: networkId,
        timestamp: new Date().toISOString(),
      });
      setNetworkRiskData(response.data);
    } catch (error) {
      console.error('Error fetching network risk:', error);
    }
  };

  const fetchConflicts = async () => {
    try {
      const response = await axios.get('/api/digital-twin/conflicts?limit=50');
      setConflicts(response.data.conflicts || []);
    } catch (error) {
      console.error('Error fetching conflicts:', error);
    }
  };

  const handleCreateConflict = async () => {
    try {
      const conflictData = {
        ...conflictForm,
        affected_trains: conflictForm.affected_trains.split(',').map(t => t.trim()),
        delay_before: parseInt(conflictForm.delay_before),
        metadata: {
          network_id: conflictForm.network_id,
        },
      };

      await axios.post('/api/digital-twin/conflicts', conflictData);
      
      // Get recommendations immediately
      const recsResponse = await axios.post('/api/digital-twin/recommendations', conflictData);
      setRecommendations(recsResponse.data.recommendations || []);
      
      fetchConflicts();
      setOpenConflictDialog(false);
      
      // Reset form
      setConflictForm({
        conflict_type: 'headway_conflict',
        station: '',
        time_of_day: 'evening_peak',
        severity: 'high',
        affected_trains: '',
        description: '',
        delay_before: 10,
        platform: '',
        network_id: selectedNetwork || '',
      });
    } catch (error) {
      console.error('Error creating conflict:', error);
      alert('Error creating conflict: ' + (error.response?.data?.detail || error.message));
    }
  };

  const getRiskLevelColor = (level) => {
    const colors = {
      critical: '#ef4444',
      high: '#f59e0b',
      elevated: '#eab308',
      medium: '#3b82f6',
      normal: '#10b981',
      low: '#6b7280',
      unknown: '#9ca3af',
    };
    return colors[level] || colors.unknown;
  };

  const getRiskLevelLabel = (level) => {
    const labels = {
      critical: 'CRITICAL',
      high: 'HIGH',
      elevated: 'ELEVATED',
      medium: 'MEDIUM',
      normal: 'NORMAL',
      low: 'LOW',
    };
    return labels[level] || level?.toUpperCase() || 'UNKNOWN';
  };

  const formatHour = (hour) => {
    return `${hour.toString().padStart(2, '0')}:00`;
  };

  const prepareRiskChartData = () => {
    if (!networkRiskData?.high_risk_windows) return [];
    
    return networkRiskData.high_risk_windows.map(window => ({
      hour: formatHour(window.hour),
      risk: (window.conflict_probability * 100).toFixed(1),
      samples: window.sample_count,
      level: window.risk_level,
    }));
  };

  const prepareConflictTypesData = () => {
    if (!networkRiskData?.conflict_types) return [];
    
    return Object.entries(networkRiskData.conflict_types).map(([type, value]) => ({
      name: type.replace(/_/g, ' ').toUpperCase(),
      value: (value * 100).toFixed(1),
      count: Math.round(value * networkRiskData.sample_size),
    }));
  };

  const selectedNetworkData = networks.find(n => n.network_id === selectedNetwork);

  return (
    <Box sx={{ 
      bgcolor: '#f8f9fa', 
      minHeight: '100vh', 
      p: { xs: 2, md: 4 },
      background: 'linear-gradient(180deg, #fef3c7 0%, #f8f9fa 100%)'
    }}>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <NetworkCheckIcon sx={{ mr: 1.5, fontSize: 40, color: '#f59e0b' }} />
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#92400e' }}>
              Network Monitoring
            </Typography>
            <Typography variant="caption" sx={{ color: '#78350f', fontWeight: 500 }}>
              Real-time network risk assessment & conflict patterns (Phase 3)
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 2 }}>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setOpenConflictDialog(true)}
            sx={{
              bgcolor: '#f59e0b',
              '&:hover': { bgcolor: '#d97706' },
              fontWeight: 600,
            }}
          >
            Create Conflict
          </Button>
          <IconButton
            sx={{
              bgcolor: 'white',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              '&:hover': { bgcolor: '#fef3c7' }
            }}
            onClick={() => {
              fetchNetworksSummary();
              if (selectedNetwork) fetchNetworkRisk(selectedNetwork);
            }}
          >
            <RefreshIcon sx={{ color: '#f59e0b' }} />
          </IconButton>
        </Box>
      </Box>

      {/* Network Selector */}
      <Paper sx={{ p: 2, mb: 3, borderRadius: 2 }}>
        <FormControl fullWidth>
          <InputLabel>Select Network</InputLabel>
          <Select
            value={selectedNetwork || ''}
            onChange={(e) => setSelectedNetwork(e.target.value)}
            label="Select Network"
          >
            {networks.map((network) => (
              <MenuItem key={network.network_id} value={network.network_id}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                  <span>{network.network_id} - {network.conflict_count} conflicts</span>
                  <Chip
                    label={getRiskLevelLabel(network.risk_level)}
                    size="small"
                    sx={{
                      bgcolor: getRiskLevelColor(network.risk_level),
                      color: 'white',
                      fontWeight: 600,
                      fontSize: '0.7rem',
                    }}
                  />
                </Box>
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Paper>

      {/* Key Metrics */}
      {selectedNetworkData && networkRiskData && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Card sx={{
              background: `linear-gradient(135deg, ${getRiskLevelColor(networkRiskData.risk_level)} 0%, ${getRiskLevelColor(networkRiskData.risk_level)}dd 100%)`,
              color: 'white',
              borderRadius: 3,
            }}>
              <CardContent>
                <Typography variant="body2" sx={{ opacity: 0.9, mb: 1 }}>
                  Risk Level
                </Typography>
                <Typography variant="h3" sx={{ fontWeight: 900 }}>
                  {getRiskLevelLabel(networkRiskData.risk_level)}
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.8 }}>
                  Current Hour: {(networkRiskData.current_hour_risk * 100).toFixed(0)}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card sx={{ borderRadius: 3 }}>
              <CardContent>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Conflict Rate
                </Typography>
                <Typography variant="h3" sx={{ fontWeight: 900, color: '#ef4444' }}>
                  {(networkRiskData.overall_conflict_rate * 100).toFixed(0)}%
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {networkRiskData.sample_size} samples analyzed
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card sx={{ borderRadius: 3 }}>
              <CardContent>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  High-Risk Windows
                </Typography>
                <Typography variant="h3" sx={{ fontWeight: 900, color: '#f59e0b' }}>
                  {networkRiskData.high_risk_windows?.length || 0}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Hours with elevated risk
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={3}>
            <Card sx={{ borderRadius: 3 }}>
              <CardContent>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Confidence Boost
                </Typography>
                <Typography variant="h3" sx={{ fontWeight: 900, color: '#10b981' }}>
                  +{networkRiskData.risk_level === 'critical' ? '20' : networkRiskData.risk_level === 'high' ? '15' : '10'}%
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Recommendation confidence
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Charts */}
      {networkRiskData && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          {/* Hourly Risk Pattern */}
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3, borderRadius: 3 }}>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
                Hourly Risk Pattern
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={prepareRiskChartData()}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="hour" />
                  <YAxis label={{ value: 'Risk %', angle: -90, position: 'insideLeft' }} />
                  <RechartsTooltip 
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        return (
                          <Paper sx={{ p: 1.5 }}>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {payload[0].payload.hour}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Risk: {payload[0].value}%
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Samples: {payload[0].payload.samples}
                            </Typography>
                            <Chip
                              label={getRiskLevelLabel(payload[0].payload.level)}
                              size="small"
                              sx={{
                                mt: 0.5,
                                bgcolor: getRiskLevelColor(payload[0].payload.level),
                                color: 'white',
                              }}
                            />
                          </Paper>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar 
                    dataKey="risk" 
                    fill="#f59e0b"
                    radius={[8, 8, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>

          {/* Conflict Types Distribution */}
          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3, borderRadius: 3 }}>
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
                Conflict Types
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={prepareConflictTypesData()}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, value }) => `${name.split(' ')[0]}: ${value}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {prepareConflictTypesData().map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={['#ef4444', '#f59e0b', '#10b981', '#3b82f6'][index % 4]} />
                    ))}
                  </Pie>
                  <RechartsTooltip />
                </PieChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* Recent Conflicts */}
      <Paper sx={{ p: 3, borderRadius: 3, mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
          Recent Conflicts ({conflicts.length})
        </Typography>
        <Grid container spacing={2}>
          {conflicts.slice(0, 6).map((conflict, index) => (
            <Grid item xs={12} md={6} lg={4} key={index}>
              <Card sx={{ borderRadius: 2, borderLeft: '4px solid #f59e0b' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      {conflict.conflict_type?.replace(/_/g, ' ').toUpperCase()}
                    </Typography>
                    <Chip
                      label={conflict.severity}
                      size="small"
                      sx={{
                        bgcolor: conflict.severity === 'high' ? '#ef4444' : conflict.severity === 'medium' ? '#f59e0b' : '#10b981',
                        color: 'white',
                      }}
                    />
                  </Box>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {conflict.description || conflict.station}
                  </Typography>
                  {conflict.metadata?.network_id && (
                    <Chip
                      label={`Network: ${conflict.metadata.network_id}`}
                      size="small"
                      variant="outlined"
                      icon={<NetworkCheckIcon />}
                      sx={{ fontSize: '0.7rem' }}
                    />
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Paper>

      {/* Recommendations Display */}
      {recommendations.length > 0 && (
        <Paper sx={{ p: 3, borderRadius: 3 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 700, color: '#10b981' }}>
            <ThumbUpIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            AI Recommendations (Network-Aware)
          </Typography>
          <Grid container spacing={2}>
            {recommendations.map((rec, index) => (
              <Grid item xs={12} key={index}>
                <Card sx={{ 
                  borderRadius: 2, 
                  borderLeft: `4px solid ${index === 0 ? '#10b981' : index === 1 ? '#3b82f6' : '#f59e0b'}`,
                  bgcolor: index === 0 ? '#f0fdf4' : 'white',
                }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="h6" sx={{ fontWeight: 700 }}>
                        #{rec.rank} {rec.strategy?.replace(/_/g, ' ').toUpperCase()}
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                        <Tooltip title="Confidence boosted by network risk analysis">
                          <Chip
                            label={`${(rec.confidence * 100).toFixed(1)}% confidence`}
                            sx={{
                              bgcolor: '#10b981',
                              color: 'white',
                              fontWeight: 600,
                            }}
                            icon={<TrendingUpIcon sx={{ color: 'white !important' }} />}
                          />
                        </Tooltip>
                        {rec.cascade_risk && rec.cascade_risk.has_cascade_risk && (
                          <Tooltip title={`⚠️ Warning: This strategy may cause ${rec.cascade_risk.cascade_count} secondary conflict(s). Confidence reduced by ${rec.cascade_risk.cascade_penalty} points.`}>
                            <Chip
                              label={`⚠️ Cascade Risk (${rec.cascade_risk.cascade_count})`}
                              sx={{
                                bgcolor: '#ef4444',
                                color: 'white',
                                fontWeight: 600,
                              }}
                              icon={<WarningIcon sx={{ color: 'white !important' }} />}
                            />
                          </Tooltip>
                        )}
                      </Box>
                    </Box>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: rec.cascade_risk && rec.cascade_risk.has_cascade_risk ? 1.5 : 0 }}>
                      {rec.explanation}
                    </Typography>
                    {rec.cascade_risk && rec.cascade_risk.has_cascade_risk && (
                      <Alert severity="warning" sx={{ mt: 1 }}>
                        <strong>Cascade Risk Detected:</strong> This resolution may trigger {rec.cascade_risk.cascade_count} additional conflict(s). 
                        Consider alternative strategies to avoid secondary disruptions.
                      </Alert>
                    )}
                    <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                      <Button
                        startIcon={<RateReviewIcon />}
                        variant="outlined"
                        size="small"
                        onClick={() => {
                          setFeedbackConflict({
                            id: conflicts[0]?.id || '',
                            strategy: rec.strategy
                          });
                          setOpenFeedbackModal(true);
                        }}
                        sx={{
                          color: '#0b0499',
                          borderColor: '#0b0499',
                          '&:hover': {
                            borderColor: '#1a0db3',
                            bgcolor: 'rgba(11, 4, 153, 0.04)',
                          }
                        }}
                      >
                        Submit Feedback
                      </Button>
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

      {/* Create Conflict Dialog */}
      <Dialog 
        open={openConflictDialog} 
        onClose={() => setOpenConflictDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Create Network Conflict</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Conflict Type</InputLabel>
                <Select
                  value={conflictForm.conflict_type}
                  onChange={(e) => setConflictForm({ ...conflictForm, conflict_type: e.target.value })}
                  label="Conflict Type"
                >
                  <MenuItem value="platform_conflict">Platform Conflict</MenuItem>
                  <MenuItem value="headway_conflict">Headway Conflict</MenuItem>
                  <MenuItem value="track_blockage">Track Blockage</MenuItem>
                  <MenuItem value="capacity_overload">Capacity Overload</MenuItem>
                  <MenuItem value="signal_failure">Signal Failure</MenuItem>
                  <MenuItem value="crew_shortage">Crew Shortage</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Network</InputLabel>
                <Select
                  value={conflictForm.network_id}
                  onChange={(e) => setConflictForm({ ...conflictForm, network_id: e.target.value })}
                  label="Network"
                >
                  {networks.map((network) => (
                    <MenuItem key={network.network_id} value={network.network_id}>
                      {network.network_id} ({getRiskLevelLabel(network.risk_level)})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Station"
                value={conflictForm.station}
                onChange={(e) => setConflictForm({ ...conflictForm, station: e.target.value })}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Time of Day</InputLabel>
                <Select
                  value={conflictForm.time_of_day}
                  onChange={(e) => setConflictForm({ ...conflictForm, time_of_day: e.target.value })}
                  label="Time of Day"
                >
                  <MenuItem value="early_morning">Early Morning</MenuItem>
                  <MenuItem value="morning_peak">Morning Peak</MenuItem>
                  <MenuItem value="midday">Midday</MenuItem>
                  <MenuItem value="evening_peak">Evening Peak</MenuItem>
                  <MenuItem value="evening">Evening</MenuItem>
                  <MenuItem value="night">Night</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel>Severity</InputLabel>
                <Select
                  value={conflictForm.severity}
                  onChange={(e) => setConflictForm({ ...conflictForm, severity: e.target.value })}
                  label="Severity"
                >
                  <MenuItem value="low">Low</MenuItem>
                  <MenuItem value="medium">Medium</MenuItem>
                  <MenuItem value="high">High</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Delay Before (minutes)"
                type="number"
                value={conflictForm.delay_before}
                onChange={(e) => setConflictForm({ ...conflictForm, delay_before: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Affected Trains (comma-separated)"
                placeholder="101, 102, 103"
                value={conflictForm.affected_trains}
                onChange={(e) => setConflictForm({ ...conflictForm, affected_trains: e.target.value })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                multiline
                rows={3}
                label="Description"
                value={conflictForm.description}
                onChange={(e) => setConflictForm({ ...conflictForm, description: e.target.value })}
              />
            </Grid>
          </Grid>
          <Alert severity="info" sx={{ mt: 2 }}>
            <Typography variant="body2">
              <strong>Network Risk Integration:</strong> The recommendation engine will automatically analyze the selected network's risk level and adjust confidence scores accordingly. High-risk networks get +15-20% confidence boost.
            </Typography>
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenConflictDialog(false)}>Cancel</Button>
          <Button 
            variant="contained" 
            onClick={handleCreateConflict}
            disabled={!conflictForm.station || !conflictForm.network_id || !conflictForm.affected_trains}
          >
            Create & Get Recommendations
          </Button>
        </DialogActions>
      </Dialog>

      {/* Feedback Modal */}
      <FeedbackModal
        open={openFeedbackModal}
        onClose={() => setOpenFeedbackModal(false)}
        conflictId={feedbackConflict.id}
        strategyApplied={feedbackConflict.strategy}
      />
    </Box>
  );
}

export default NetworkMonitoring;
