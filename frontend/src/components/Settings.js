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
import { 
  Save as SaveIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
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
    <Box sx={{ 
      bgcolor: '#f8f9fa', 
      minHeight: '100vh', 
      p: { xs: 2, md: 4 },
      background: 'linear-gradient(180deg, #e3f2fd 0%, #f8f9fa 100%)'
    }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <SettingsIcon sx={{ mr: 1.5, fontSize: 40, color: '#0891b2' }} />
        <Typography variant="h4" sx={{ fontWeight: 800, color: '#1e40af' }}>
          Settings
        </Typography>
      </Box>

      {saveStatus && (
        <Alert severity={saveStatus.type} sx={{ mb: 3, borderRadius: 2, fontWeight: 500 }}>
          {saveStatus.message}
        </Alert>
      )}

      <Paper sx={{ 
        p: 3,
        bgcolor: 'white',
        borderRadius: 3,
        boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
        border: '1px solid rgba(0,0,0,0.05)'
      }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 700, color: '#1e40af', mb: 3 }}>
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

        <Typography variant="h6" gutterBottom sx={{ fontWeight: 700, color: '#1e40af', mb: 3 }}>
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
            sx={{
              background: 'linear-gradient(135deg, #1e40af 0%, #0891b2 100%)',
              fontWeight: 600,
              px: 4,
              py: 1.5,
              '&:hover': {
                background: 'linear-gradient(135deg, #1e3a8a 0%, #0e7490 100%)',
              }
            }}
          >
            Save Settings
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}

export default Settings;
