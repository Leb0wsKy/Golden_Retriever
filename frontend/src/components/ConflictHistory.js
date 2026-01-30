import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  CircularProgress,
  TextField,
  InputAdornment,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Tooltip,
} from '@mui/material';
import {
  History as HistoryIcon,
  Search as SearchIcon,
  Train as TrainIcon,
  LocationOn as LocationIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import axios from 'axios';

function ConflictHistory() {
  const [conflicts, setConflicts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');

  useEffect(() => {
    fetchConflicts();
  }, []);

  const fetchConflicts = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/digital-twin/conflicts', {
        params: { limit: 100 }
      });
      setConflicts(response.data.conflicts || response.data || []);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching conflicts:', error);
      setConflicts([]);
      setLoading(false);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'error';
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  const getStatusColor = (resolved) => {
    return resolved ? 'success' : 'warning';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const filteredConflicts = conflicts.filter(conflict => {
    const matchesSearch = searchTerm === '' || 
      conflict.station?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      conflict.conflict_type?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesSeverity = severityFilter === 'all' || 
      conflict.severity?.toLowerCase() === severityFilter;
    
    const matchesType = typeFilter === 'all' || 
      conflict.conflict_type === typeFilter;

    return matchesSearch && matchesSeverity && matchesType;
  });

  const uniqueTypes = [...new Set(conflicts.map(c => c.conflict_type))].filter(Boolean);

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <HistoryIcon sx={{ mr: 1.5, fontSize: 40, color: '#0891b2' }} />
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 800, color: '#1e40af' }}>
              Conflict History
            </Typography>
            <Typography variant="caption" sx={{ color: '#64748b' }}>
              {filteredConflicts.length} conflicts • Last 30 days
            </Typography>
          </Box>
        </Box>
        <IconButton
          onClick={fetchConflicts}
          disabled={loading}
          sx={{ color: '#0891b2' }}
        >
          <RefreshIcon />
        </IconButton>
      </Box>

      {/* Filters */}
      <Paper elevation={0} sx={{ p: 2, mb: 3, borderRadius: 2 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <TextField
            placeholder="Search by station or type..."
            variant="outlined"
            size="small"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            sx={{ flexGrow: 1, minWidth: 250 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ color: '#64748b' }} />
                </InputAdornment>
              ),
            }}
          />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Severity</InputLabel>
            <Select
              value={severityFilter}
              label="Severity"
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <MenuItem value="all">All Severities</MenuItem>
              <MenuItem value="critical">Critical</MenuItem>
              <MenuItem value="high">High</MenuItem>
              <MenuItem value="medium">Medium</MenuItem>
              <MenuItem value="low">Low</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Type</InputLabel>
            <Select
              value={typeFilter}
              label="Type"
              onChange={(e) => setTypeFilter(e.target.value)}
            >
              <MenuItem value="all">All Types</MenuItem>
              {uniqueTypes.map(type => (
                <MenuItem key={type} value={type}>
                  {type?.replace(/_/g, ' ').toUpperCase()}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </Paper>

      {/* History Table */}
      <TableContainer component={Paper} elevation={0} sx={{ borderRadius: 2 }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Table>
            <TableHead>
              <TableRow sx={{ bgcolor: '#f1f5f9' }}>
                <TableCell sx={{ fontWeight: 700 }}>Timestamp</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Station</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Trains</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Conflict Type</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Severity</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Status</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>Description</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredConflicts.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 8 }}>
                    <Typography color="textSecondary">
                      No conflicts found
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filteredConflicts.map((conflict, index) => (
                  <TableRow 
                    key={conflict.id || index}
                    sx={{ 
                      '&:hover': { bgcolor: '#f8fafc' },
                      transition: 'background-color 0.2s'
                    }}
                  >
                    <TableCell sx={{ fontSize: '0.85rem' }}>
                      {formatDate(conflict.timestamp)}
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <LocationIcon sx={{ fontSize: 16, color: '#64748b' }} />
                        <Typography variant="body2" fontWeight={600}>
                          {conflict.station || 'N/A'}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <TrainIcon sx={{ fontSize: 16, color: '#64748b' }} />
                        <Typography variant="body2">
                          {conflict.train_id || conflict.affected_trains?.join(', ') || 'N/A'}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip 
                        label={conflict.conflict_type?.replace(/_/g, ' ') || 'Unknown'}
                        size="small"
                        sx={{ textTransform: 'capitalize' }}
                      />
                    </TableCell>
                    <TableCell>
                      <Chip 
                        label={conflict.severity || 'Medium'}
                        size="small"
                        color={getSeverityColor(conflict.severity)}
                      />
                    </TableCell>
                    <TableCell>
                      <Chip 
                        icon={conflict.resolved ? <CheckIcon /> : <ErrorIcon />}
                        label={conflict.resolved ? 'Resolved' : 'Active'}
                        size="small"
                        color={getStatusColor(conflict.resolved)}
                        variant={conflict.resolved ? 'filled' : 'outlined'}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ maxWidth: 300, fontSize: '0.85rem' }}>
                        {conflict.description || conflict.details || 'No description available'}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </TableContainer>
    </Box>
  );
}

export default ConflictHistory;
