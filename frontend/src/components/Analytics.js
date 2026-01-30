import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  CircularProgress,
  Card,
  CardContent,
  LinearProgress,
} from '@mui/material';
import {
  Analytics as AnalyticsIcon,
  TrendingUp,
  TrendingDown,
  Warning,
  CheckCircle,
  Speed,
  Schedule,
} from '@mui/icons-material';
import axios from 'axios';

function Analytics() {
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState(null);
  const [conflictStats, setConflictStats] = useState(null);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      setLoading(true);
      const [metricsRes, conflictsRes] = await Promise.all([
        axios.get('/api/digital-twin/recommendations/metrics'),
        axios.get('/api/digital-twin/conflicts', { params: { limit: 500 } })
      ]);
      
      setMetrics(metricsRes.data);
      
      // Calculate conflict statistics
      const conflicts = conflictsRes.data.conflicts || conflictsRes.data || [];
      const stats = {
        total: conflicts.length,
        resolved: conflicts.filter(c => c.resolved).length,
        active: conflicts.filter(c => !c.resolved).length,
        bySeverity: {
          critical: conflicts.filter(c => c.severity === 'critical').length,
          high: conflicts.filter(c => c.severity === 'high').length,
          medium: conflicts.filter(c => c.severity === 'medium').length,
          low: conflicts.filter(c => c.severity === 'low').length,
        },
        byType: conflicts.reduce((acc, c) => {
          acc[c.conflict_type] = (acc[c.conflict_type] || 0) + 1;
          return acc;
        }, {}),
        resolutionRate: conflicts.length > 0 
          ? ((conflicts.filter(c => c.resolved).length / conflicts.length) * 100).toFixed(1)
          : 0
      };
      
      setConflictStats(stats);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching analytics:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <AnalyticsIcon sx={{ mr: 1.5, fontSize: 40, color: '#0891b2' }} />
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 800, color: '#1e40af' }}>
            System Analytics
          </Typography>
          <Typography variant="caption" sx={{ color: '#64748b' }}>
            Performance metrics and conflict insights
          </Typography>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Recommendation Metrics */}
        {metrics && (
          <>
            <Grid item xs={12} md={3}>
              <Card elevation={0} sx={{ height: '100%', borderRadius: 2, border: '1px solid #e2e8f0' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography color="textSecondary" variant="body2" fontWeight={600}>
                      Total Recommendations
                    </Typography>
                    <TrendingUp sx={{ color: '#10b981' }} />
                  </Box>
                  <Typography variant="h3" fontWeight={700} color="#0891b2">
                    {metrics.total_recommendations || 0}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={3}>
              <Card elevation={0} sx={{ height: '100%', borderRadius: 2, border: '1px solid #e2e8f0' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography color="textSecondary" variant="body2" fontWeight={600}>
                      Avg Confidence
                    </Typography>
                    <Speed sx={{ color: '#6366f1' }} />
                  </Box>
                  <Typography variant="h3" fontWeight={700} color="#0891b2">
                    {metrics.average_confidence ? (metrics.average_confidence * 100).toFixed(0) : 0}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={3}>
              <Card elevation={0} sx={{ height: '100%', borderRadius: 2, border: '1px solid #e2e8f0' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography color="textSecondary" variant="body2" fontWeight={600}>
                      Avg Delay Reduction
                    </Typography>
                    <Schedule sx={{ color: '#f59e0b' }} />
                  </Box>
                  <Typography variant="h3" fontWeight={700} color="#0891b2">
                    {metrics.average_delay_reduction ? metrics.average_delay_reduction.toFixed(1) : 0}m
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid item xs={12} md={3}>
              <Card elevation={0} sx={{ height: '100%', borderRadius: 2, border: '1px solid #e2e8f0' }}>
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                    <Typography color="textSecondary" variant="body2" fontWeight={600}>
                      Success Rate
                    </Typography>
                    <CheckCircle sx={{ color: '#10b981' }} />
                  </Box>
                  <Typography variant="h3" fontWeight={700} color="#0891b2">
                    {metrics.success_rate ? (metrics.success_rate * 100).toFixed(0) : 0}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </>
        )}

        {/* Conflict Statistics */}
        {conflictStats && (
          <>
            <Grid item xs={12} md={6}>
              <Paper elevation={0} sx={{ p: 3, borderRadius: 2, border: '1px solid #e2e8f0' }}>
                <Typography variant="h6" fontWeight={700} gutterBottom>
                  Conflict Overview
                </Typography>
                <Box sx={{ mt: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="textSecondary">Total Conflicts</Typography>
                    <Typography variant="body2" fontWeight={600}>{conflictStats.total}</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="body2" color="textSecondary">Resolved</Typography>
                    <Typography variant="body2" fontWeight={600} color="success.main">
                      {conflictStats.resolved}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="body2" color="textSecondary">Active</Typography>
                    <Typography variant="body2" fontWeight={600} color="warning.main">
                      {conflictStats.active}
                    </Typography>
                  </Box>
                  <Box sx={{ mb: 1 }}>
                    <Typography variant="body2" color="textSecondary" gutterBottom>
                      Resolution Rate
                    </Typography>
                    <LinearProgress 
                      variant="determinate" 
                      value={parseFloat(conflictStats.resolutionRate)} 
                      sx={{ height: 8, borderRadius: 4 }}
                    />
                    <Typography variant="caption" color="textSecondary">
                      {conflictStats.resolutionRate}%
                    </Typography>
                  </Box>
                </Box>
              </Paper>
            </Grid>

            <Grid item xs={12} md={6}>
              <Paper elevation={0} sx={{ p: 3, borderRadius: 2, border: '1px solid #e2e8f0' }}>
                <Typography variant="h6" fontWeight={700} gutterBottom>
                  Severity Distribution
                </Typography>
                <Box sx={{ mt: 2 }}>
                  {Object.entries(conflictStats.bySeverity).map(([severity, count]) => (
                    <Box key={severity} sx={{ mb: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                          {severity}
                        </Typography>
                        <Typography variant="body2" fontWeight={600}>
                          {count}
                        </Typography>
                      </Box>
                      <LinearProgress 
                        variant="determinate" 
                        value={(count / conflictStats.total) * 100} 
                        sx={{ 
                          height: 6, 
                          borderRadius: 3,
                          bgcolor: '#e2e8f0',
                          '& .MuiLinearProgress-bar': {
                            bgcolor: severity === 'critical' ? '#ef4444' :
                                     severity === 'high' ? '#f59e0b' :
                                     severity === 'medium' ? '#eab308' : '#10b981'
                          }
                        }}
                      />
                    </Box>
                  ))}
                </Box>
              </Paper>
            </Grid>

            <Grid item xs={12}>
              <Paper elevation={0} sx={{ p: 3, borderRadius: 2, border: '1px solid #e2e8f0' }}>
                <Typography variant="h6" fontWeight={700} gutterBottom>
                  Conflict Types
                </Typography>
                <Grid container spacing={2} sx={{ mt: 1 }}>
                  {Object.entries(conflictStats.byType).map(([type, count]) => (
                    <Grid item xs={12} sm={6} md={4} key={type}>
                      <Box sx={{ 
                        p: 2, 
                        bgcolor: '#f8fafc', 
                        borderRadius: 2,
                        border: '1px solid #e2e8f0'
                      }}>
                        <Typography variant="body2" color="textSecondary" gutterBottom>
                          {type?.replace(/_/g, ' ').toUpperCase() || 'Unknown'}
                        </Typography>
                        <Typography variant="h5" fontWeight={700} color="#0891b2">
                          {count}
                        </Typography>
                      </Box>
                    </Grid>
                  ))}
                </Grid>
              </Paper>
            </Grid>
          </>
        )}
      </Grid>
    </Box>
  );
}

export default Analytics;
