import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  Grid,
  Alert,
  Divider,
} from '@mui/material';
import { Save as SaveIcon } from '@mui/icons-material';
import axios from 'axios';

function Settings() {
  const [settings, setSettings] = useState({
    qdrant_url: 'http://localhost:6333',
    qdrant_api_key: '',
    collection_name: 'default_collection',
    vector_dimension: 384,
    max_connections: 10,
    timeout: 30,
  });
  const [saveStatus, setSaveStatus] = useState(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await axios.get('/api/settings');
      setSettings(response.data);
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  };

  const handleSave = async () => {
    try {
      await axios.post('/api/settings', settings);
      setSaveStatus({ type: 'success', message: 'Settings saved successfully!' });
      setTimeout(() => setSaveStatus(null), 3000);
    } catch (error) {
      setSaveStatus({ type: 'error', message: 'Failed to save settings' });
      console.error('Error saving settings:', error);
    }
  };

  const handleChange = (field, value) => {
    setSettings({ ...settings, [field]: value });
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Settings
      </Typography>

      {saveStatus && (
        <Alert severity={saveStatus.type} sx={{ mb: 3 }}>
          {saveStatus.message}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Qdrant Configuration
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Qdrant URL"
              value={settings.qdrant_url}
              onChange={(e) => handleChange('qdrant_url', e.target.value)}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Qdrant API Key"
              type="password"
              value={settings.qdrant_api_key}
              onChange={(e) => handleChange('qdrant_api_key', e.target.value)}
              helperText="Enter your Qdrant API key for authentication"
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Default Collection Name"
              value={settings.collection_name}
              onChange={(e) => handleChange('collection_name', e.target.value)}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Vector Dimension"
              type="number"
              value={settings.vector_dimension}
              onChange={(e) => handleChange('vector_dimension', parseInt(e.target.value))}
            />
          </Grid>
        </Grid>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h6" gutterBottom>
          Connection Settings
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Max Connections"
              type="number"
              value={settings.max_connections}
              onChange={(e) => handleChange('max_connections', parseInt(e.target.value))}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Timeout (seconds)"
              type="number"
              value={settings.timeout}
              onChange={(e) => handleChange('timeout', parseInt(e.target.value))}
            />
          </Grid>
        </Grid>

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            size="large"
          >
            Save Settings
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}

export default Settings;
