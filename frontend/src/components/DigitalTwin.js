import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Button,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
} from '@mui/material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { PlayArrow, Stop, Refresh } from '@mui/icons-material';
import axios from 'axios';

function DigitalTwin() {
  const [simulationData, setSimulationData] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [parameters, setParameters] = useState({
    dataRate: 50,
    noiseLevel: 0.1,
    scenario: 'normal',
  });
  const [metrics, setMetrics] = useState({
    accuracy: 0,
    latency: 0,
    throughput: 0,
  });

  useEffect(() => {
    if (isRunning) {
      const interval = setInterval(fetchSimulationData, 1000);
      return () => clearInterval(interval);
    }
  }, [isRunning]);

  const fetchSimulationData = async () => {
    try {
      const response = await axios.get('/api/digital-twin/data');
      setSimulationData(prevData => {
        const newData = [...prevData, response.data];
        return newData.slice(-20); // Keep last 20 points
      });
      setMetrics(response.data.metrics);
    } catch (error) {
      console.error('Error fetching simulation data:', error);
    }
  };

  const startSimulation = async () => {
    try {
      await axios.post('/api/digital-twin/start', parameters);
      setIsRunning(true);
    } catch (error) {
      console.error('Error starting simulation:', error);
    }
  };

  const stopSimulation = async () => {
    try {
      await axios.post('/api/digital-twin/stop');
      setIsRunning(false);
    } catch (error) {
      console.error('Error stopping simulation:', error);
    }
  };

  const resetSimulation = async () => {
    try {
      await axios.post('/api/digital-twin/reset');
      setSimulationData([]);
      setMetrics({ accuracy: 0, latency: 0, throughput: 0 });
    } catch (error) {
      console.error('Error resetting simulation:', error);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Digital Twin Simulation
      </Typography>

      <Alert severity="info" sx={{ mb: 3 }}>
        Monitor real-time vector database performance through digital twin simulation
      </Alert>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Simulation Controls
            </Typography>
            
            <Box sx={{ mb: 3 }}>
              <Typography gutterBottom>Data Rate: {parameters.dataRate}/s</Typography>
              <Slider
                value={parameters.dataRate}
                onChange={(e, value) => setParameters({ ...parameters, dataRate: value })}
                min={1}
                max={100}
                disabled={isRunning}
              />
            </Box>

            <Box sx={{ mb: 3 }}>
              <Typography gutterBottom>Noise Level: {parameters.noiseLevel}</Typography>
              <Slider
                value={parameters.noiseLevel}
                onChange={(e, value) => setParameters({ ...parameters, noiseLevel: value })}
                min={0}
                max={1}
                step={0.01}
                disabled={isRunning}
              />
            </Box>

            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Scenario</InputLabel>
              <Select
                value={parameters.scenario}
                onChange={(e) => setParameters({ ...parameters, scenario: e.target.value })}
                disabled={isRunning}
              >
                <MenuItem value="normal">Normal Operation</MenuItem>
                <MenuItem value="high_load">High Load</MenuItem>
                <MenuItem value="stress_test">Stress Test</MenuItem>
                <MenuItem value="failure">Failure Scenario</MenuItem>
              </Select>
            </FormControl>

            <Box sx={{ display: 'flex', gap: 1, flexDirection: 'column' }}>
              {!isRunning ? (
                <Button
                  variant="contained"
                  startIcon={<PlayArrow />}
                  onClick={startSimulation}
                  fullWidth
                >
                  Start Simulation
                </Button>
              ) : (
                <Button
                  variant="contained"
                  color="error"
                  startIcon={<Stop />}
                  onClick={stopSimulation}
                  fullWidth
                >
                  Stop Simulation
                </Button>
              )}
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={resetSimulation}
                fullWidth
              >
                Reset
              </Button>
            </Box>
          </Paper>

          <Paper sx={{ p: 3, mt: 2 }}>
            <Typography variant="h6" gutterBottom>
              Real-time Metrics
            </Typography>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="textSecondary">
                Accuracy
              </Typography>
              <Typography variant="h4">
                {(metrics.accuracy * 100).toFixed(2)}%
              </Typography>
            </Box>
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="textSecondary">
                Latency
              </Typography>
              <Typography variant="h4">
                {metrics.latency.toFixed(2)}ms
              </Typography>
            </Box>
            <Box>
              <Typography variant="body2" color="textSecondary">
                Throughput
              </Typography>
              <Typography variant="h4">
                {metrics.throughput.toFixed(0)} ops/s
              </Typography>
            </Box>
          </Paper>
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Performance Graph
            </Typography>
            <ResponsiveContainer width="100%" height={400}>
              <LineChart data={simulationData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="accuracy" stroke="#2e7d32" />
                <Line type="monotone" dataKey="latency" stroke="#ed6c02" />
                <Line type="monotone" dataKey="throughput" stroke="#1976d2" />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default DigitalTwin;
