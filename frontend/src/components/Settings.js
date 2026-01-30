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
  Card,
  CardContent,
  CardActions,
  Chip,
} from '@mui/material';
import { 
  Save as SaveIcon,
  Settings as SettingsIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  Star as StarIcon,
  Workspaces as WorkspaceIcon,
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
  const [currentPlan, setCurrentPlan] = useState('free'); // free, premium, premium_plus

  const pricingPlans = [
    {
      id: 'free',
      name: 'Free',
      price: 0,
      features: [
        { text: 'Basic conflict detection', included: true },
        { text: 'Up to 100 alerts/month', included: true },
        { text: 'Email notifications', included: true },
        { text: 'Historical data (7 days)', included: true },
        { text: 'Advanced analytics', included: false },
        { text: 'Priority support', included: false },
        { text: 'API access', included: false },
      ],
      color: '#64748b',
    },
    {
      id: 'premium',
      name: 'Premium',
      price: 49,
      features: [
        { text: 'Advanced conflict detection', included: true },
        { text: 'Unlimited alerts', included: true },
        { text: 'Email & SMS notifications', included: true },
        { text: 'Historical data (90 days)', included: true },
        { text: 'Advanced analytics', included: true },
        { text: 'Priority support', included: false },
        { text: 'API access', included: false },
      ],
      color: '#0891b2',
      popular: true,
    },
    {
      id: 'premium_plus',
      name: 'Premium Plus',
      price: 99,
      features: [
        { text: 'AI-powered predictions', included: true },
        { text: 'Unlimited everything', included: true },
        { text: 'Multi-channel notifications', included: true },
        { text: 'Unlimited historical data', included: true },
        { text: 'Advanced analytics & reports', included: true },
        { text: '24/7 Priority support', included: true },
        { text: 'Full API access', included: true },
      ],
      color: '#1e40af',
    },
  ];

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
      minHeight: '100vh', 
      p: { xs: 2, md: 4 },
    }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <SettingsIcon sx={{ mr: 1.5, fontSize: 40, color: '#0891b2' }} />
        <Typography variant="h4" sx={{ fontWeight: 700, background: 'linear-gradient(135deg, #1e40af 0%, #0891b2 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Settings
        </Typography>
      </Box>

      {saveStatus && (
        <Alert severity={saveStatus.type} sx={{ mb: 3, borderRadius: 2, fontWeight: 500 }}>
          {saveStatus.message}
        </Alert>
      )}

      {/* Subscription Plans Section */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" sx={{ fontWeight: 700, color: '#1e40af', mb: 3, display: 'flex', alignItems: 'center', gap: 1 }}>
          <WorkspaceIcon sx={{ fontSize: 28 }} />
          Subscription Plans
        </Typography>

        <Grid container spacing={3}>
          {pricingPlans.map((plan) => (
            <Grid item xs={12} md={4} key={plan.id}>
              <Card 
                sx={{ 
                  height: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  borderRadius: 3,
                  border: currentPlan === plan.id ? `3px solid ${plan.color}` : '1px solid #e5e7eb',
                  boxShadow: plan.popular ? '0 8px 32px rgba(8, 145, 178, 0.2)' : '0 1px 3px rgba(0,0,0,0.08)',
                  position: 'relative',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: `0 12px 40px ${plan.color}33`,
                  }
                }}
              >
                {plan.popular && (
                  <Chip 
                    label="POPULAR" 
                    icon={<StarIcon />}
                    sx={{ 
                      position: 'absolute',
                      top: 16,
                      right: 16,
                      background: 'linear-gradient(135deg, #1e40af 0%, #0891b2 100%)',
                      color: 'white',
                      fontWeight: 700,
                      fontSize: '0.7rem',
                    }}
                  />
                )}
                <CardContent sx={{ flexGrow: 1, p: 3 }}>
                  <Typography variant="h5" sx={{ fontWeight: 700, color: plan.color, mb: 1 }}>
                    {plan.name}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'baseline', mb: 3 }}>
                    <Typography variant="h3" sx={{ fontWeight: 800, color: '#1e40af' }}>
                      {plan.price}
                    </Typography>
                    <Typography variant="h6" sx={{ color: '#64748b', ml: 1 }}>
                      TND/month
                    </Typography>
                  </Box>

                  <Divider sx={{ mb: 2 }} />

                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                    {plan.features.map((feature, index) => (
                      <Box key={index} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        {feature.included ? (
                          <CheckIcon sx={{ fontSize: 20, color: '#10b981' }} />
                        ) : (
                          <CloseIcon sx={{ fontSize: 20, color: '#e5e7eb' }} />
                        )}
                        <Typography 
                          variant="body2" 
                          sx={{ 
                            color: feature.included ? '#1e293b' : '#94a3b8',
                            fontWeight: feature.included ? 500 : 400,
                          }}
                        >
                          {feature.text}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </CardContent>
                <CardActions sx={{ p: 3, pt: 0 }}>
                  {currentPlan === plan.id ? (
                    <Button 
                      fullWidth
                      variant="outlined"
                      disabled
                      sx={{
                        py: 1.5,
                        borderRadius: 2,
                        textTransform: 'none',
                        fontWeight: 600,
                        fontSize: '1rem',
                        borderColor: plan.color,
                        color: plan.color,
                      }}
                    >
                      Current Plan
                    </Button>
                  ) : (
                    <Button 
                      fullWidth
                      variant="contained"
                      onClick={() => setCurrentPlan(plan.id)}
                      sx={{
                        py: 1.5,
                        borderRadius: 2,
                        textTransform: 'none',
                        fontWeight: 600,
                        fontSize: '1rem',
                        background: plan.popular 
                          ? 'linear-gradient(135deg, #1e40af 0%, #0891b2 100%)'
                          : plan.color,
                        boxShadow: 'none',
                        '&:hover': {
                          background: plan.popular
                            ? 'linear-gradient(135deg, #1e3a8a 0%, #0e7490 100%)'
                            : plan.color,
                          boxShadow: `0 4px 12px ${plan.color}66`,
                        },
                      }}
                    >
                      {plan.price === 0 ? 'Select Plan' : 'Upgrade'}
                    </Button>
                  )}
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Box>
  );
}

export default Settings;
