import React, { useState, useEffect, useRef } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  Box,
  Chip,
  Alert,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Train as TrainIcon,
  Speed as SpeedIcon,
  Schedule as ScheduleIcon,
  Warning as WarningIcon,
  Public as PublicIcon,
} from '@mui/icons-material';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import axios from 'axios';

// Fix for default marker icons in react-leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// Custom train icon with brand colors
const trainIcon = new L.Icon({
  iconUrl: 'data:image/svg+xml;base64,' + btoa(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32">
      <circle cx="12" cy="12" r="11" fill="#2596be" stroke="#0b0499" stroke-width="2"/>
      <path d="M12 2C8 2 4 4 4 7v11c0 2 2 4 4 4h8c2 0 4-2 4-4V7c0-3-4-5-8-5zm-1 3h2v2h-2V5zm-4 6c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm10 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zM6 18l1.5-2h9l1.5 2H6z" fill="white"/>
    </svg>
  `),
  iconSize: [32, 32],
  iconAnchor: [16, 16],
  popupAnchor: [0, -16],
});

function MapUpdater({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView(center, zoom || map.getZoom(), { animate: true, duration: 1.5 });
    }
  }, [center, zoom, map]);
  return null;
}

function Dashboard({ stats }) {
  const [networks, setNetworks] = useState([]);
  const [selectedNetwork, setSelectedNetwork] = useState('all');
  const [trains, setTrains] = useState([]);
  const [routes, setRoutes] = useState([]);
  const [mapCenter, setMapCenter] = useState([20, 0]); // World view default
  const [mapZoom, setMapZoom] = useState(3); // Default zoom level
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mapRef = useRef();

  useEffect(() => {
    fetchTrainData();
    const interval = setInterval(fetchTrainData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Update displayed trains and routes when network selection changes
    if (selectedNetwork === 'all') {
      // Show all trains from all networks
      const allTrains = networks.flatMap(n => n.trains);
      const allRoutes = networks.flatMap(n => n.routes);
      setTrains(allTrains);
      setRoutes(allRoutes);
      setMapCenter([20, 0]); // World view
      setMapZoom(3); // Zoom out for global view
    } else {
      // Show trains from selected network only
      const network = networks.find(n => n.id === selectedNetwork);
      if (network) {
        setTrains(network.trains);
        setRoutes(network.routes);
        setMapCenter(network.center || [20, 0]);
        setMapZoom(8); // Zoom in to focus on selected network
      }
    }
  }, [selectedNetwork, networks]);

  const fetchTrainData = async () => {
    try {
      // Don't show loading spinner on refresh - only on initial load
      if (networks.length === 0) {
        setLoading(true);
      }
      
      const response = await axios.get('/api/trains/live');
      setNetworks(response.data.networks || []);
      
      // Initially show all trains
      if (response.data.networks && response.data.networks.length > 0) {
        const allTrains = response.data.networks.flatMap(n => n.trains);
        const allRoutes = response.data.networks.flatMap(n => n.routes);
        setTrains(allTrains);
        setRoutes(allRoutes);
      }
      setError(null);
    } catch (error) {
      console.error('Error fetching train data:', error);
      setError('Unable to fetch live train data.');
    } finally {
      setLoading(false);
    }
  };

  const handleNetworkChange = (event) => {
    setSelectedNetwork(event.target.value);
  };

  const selectedNetworkData = networks.find(n => n.id === selectedNetwork);
  const totalTrains = networks.reduce((sum, n) => sum + n.trainCount, 0);
  const totalRoutes = networks.reduce((sum, n) => sum + n.routeCount, 0);

  const statCards = [
    { label: 'Networks', value: networks.length, color: '#0b0499', icon: <PublicIcon /> },
    { label: 'Total Trains', value: totalTrains, color: '#2596be', icon: <TrainIcon /> },
    { label: 'Active Trains', value: trains.length, color: '#0b0499', icon: <TrainIcon /> },
    { label: 'Routes', value: selectedNetwork === 'all' ? totalRoutes : routes.length, color: '#2596be', icon: <WarningIcon /> },
  ];

  const getStatusColor = (status) => {
    switch (status) {
      case 'on-time': return 'success';
      case 'delayed': return 'warning';
      case 'stopped': return 'error';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ 
      bgcolor: '#f8f9fa', 
      minHeight: '100vh', 
      p: { xs: 2, md: 4 },
      background: 'linear-gradient(180deg, #e3f2fd 0%, #f8f9fa 100%)'
    }}>
      <Box sx={{ mb: 4, textAlign: 'center' }}>
        <Typography 
          variant="h3" 
          sx={{ 
            color: '#0b0499', 
            fontWeight: 900,
            mb: 1,
            textShadow: '2px 2px 4px rgba(0,0,0,0.1)',
            letterSpacing: '-0.5px'
          }}
        >
          🚄 Live Train Network Monitor
        </Typography>
        <Typography variant="body1" sx={{ color: '#666', fontWeight: 500 }}>
          Real-time tracking of {totalTrains} trains across {networks.length} networks worldwide
        </Typography>
      </Box>

      {error && (
        <Alert severity="warning" sx={{ mb: 3, borderRadius: 2, boxShadow: 2 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {statCards.map((stat, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card sx={{ 
              background: index % 2 === 0 
                ? 'linear-gradient(135deg, #0b0499 0%, #1a0db3 100%)'
                : 'linear-gradient(135deg, #2596be 0%, #3ba5ce 100%)',
              color: 'white',
              borderRadius: 3,
              boxShadow: index % 2 === 0 
                ? '0 8px 24px rgba(11, 4, 153, 0.3)'
                : '0 8px 24px rgba(37, 150, 190, 0.3)',
              transition: 'all 0.3s ease',
              border: '1px solid rgba(255,255,255,0.1)',
              '&:hover': { 
                transform: 'translateY(-8px) scale(1.02)', 
                boxShadow: index % 2 === 0 
                  ? '0 16px 48px rgba(11, 4, 153, 0.4)'
                  : '0 16px 48px rgba(37, 150, 190, 0.4)'
              }
            }}>
              <CardContent sx={{ p: 3 }}>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 2 }}>
                  <Box sx={{ 
                    bgcolor: 'rgba(255,255,255,0.2)', 
                    p: 1.5, 
                    borderRadius: 2,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    {stat.icon}
                  </Box>
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      bgcolor: 'rgba(255,255,255,0.2)', 
                      px: 1, 
                      py: 0.5, 
                      borderRadius: 1,
                      fontWeight: 600,
                      fontSize: '0.7rem'
                    }}
                  >
                    LIVE
                  </Typography>
                </Box>
                <Typography variant="body2" sx={{ opacity: 0.9, mb: 1, fontWeight: 500 }}>
                  {stat.label}
                </Typography>
                <Typography variant="h3" sx={{ fontWeight: 900, letterSpacing: '-1px' }}>
                  {stat.value}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}

        {/* Map Section */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ 
            p: 3, 
            height: 650, 
            bgcolor: 'white', 
            borderRadius: 3,
            boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
            border: '1px solid rgba(0,0,0,0.05)'
          }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Box>
                <Typography variant="h5" sx={{ color: '#0b0499', fontWeight: 800, mb: 0.5 }}>
                  {selectedNetwork === 'all' ? '🗺️ Global Network' : `🚊 ${selectedNetworkData?.name || 'Network'}`}
                </Typography>
                <Typography variant="caption" color="textSecondary" sx={{ fontWeight: 500 }}>
                  {trains.length} active trains • {routes.length} routes
                </Typography>
              </Box>
              {loading && trains.length > 0 && (
                <Chip 
                  label="● Updating" 
                  size="small" 
                  sx={{ 
                    bgcolor: '#2596be', 
                    color: 'white',
                    fontWeight: 600,
                    animation: 'pulse 2s infinite',
                    '@keyframes pulse': {
                      '0%, 100%': { opacity: 1 },
                      '50%': { opacity: 0.7 }
                    }
                  }}
                />
              )}
            </Box>

            {/* Network Selector */}
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel 
                id="network-select-label" 
                sx={{ 
                  fontWeight: 600,
                }}
              >
                🌍 Select Train Network
              </InputLabel>
              <Select
                labelId="network-select-label"
                id="network-select"
                value={selectedNetwork}
                label="🌍 Select Train Network"
                onChange={handleNetworkChange}
                sx={{
                  fontWeight: 600,
                  bgcolor: '#f8fafc',
                  borderRadius: 2
                }}
              >
                <MenuItem value="all">
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <PublicIcon sx={{ color: '#2596be' }} />
                    <Typography fontWeight={600}>All Networks</Typography>
                    <Chip 
                      label={`${totalTrains} trains`} 
                      size="small" 
                      sx={{ bgcolor: '#2596be', color: 'white', fontWeight: 'bold' }}
                    />
                  </Box>
                </MenuItem>
                {networks.map((network) => (
                  <MenuItem key={network.id} value={network.id}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center' }}>
                      <Box>
                        <Typography fontWeight={600}>{network.name}</Typography>
                        <Typography variant="caption" color="textSecondary">
                          {network.country}
                        </Typography>
                      </Box>
                      <Chip 
                        label={`${network.trainCount} trains`} 
                        size="small" 
                        sx={{ bgcolor: '#0b0499', color: 'white', fontWeight: 'bold' }}
                      />
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Box sx={{ height: 420, position: 'relative', borderRadius: 2, overflow: 'hidden' }}>
              {loading && trains.length === 0 ? (
                <Box sx={{ 
                  display: 'flex', 
                  flexDirection: 'column',
                  justifyContent: 'center', 
                  alignItems: 'center', 
                  height: '100%',
                  gap: 2
                }}>
                  <Box sx={{ 
                    width: 60, 
                    height: 60, 
                    borderRadius: '50%', 
                    border: '4px solid #e0e0e0',
                    borderTopColor: '#2596be',
                    animation: 'spin 1s linear infinite',
                    '@keyframes spin': {
                      '0%': { transform: 'rotate(0deg)' },
                      '100%': { transform: 'rotate(360deg)' }
                    }
                  }} />
                  <Typography sx={{ color: '#666', fontWeight: 500 }}>
                    Loading train data...
                  </Typography>
                </Box>
              ) : (
                <MapContainer
                  center={mapCenter}
                  zoom={selectedNetwork === 'all' ? 3 : 8}
                  style={{ height: '100%', width: '100%', borderRadius: '8px' }}
                  ref={mapRef}
                  key={selectedNetwork}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  
                  <MapUpdater center={mapCenter} zoom={mapZoom} />
                  
                  {/* Draw routes */}
                  {routes.map((route, index) => (
                    <Polyline
                      key={`route-${route.id}-${index}`}
                      positions={route.path}
                      color={route.color || '#2596be'}
                      weight={3}
                      opacity={0.7}
                    />
                  ))}

                  {/* Draw train markers */}
                  {trains.map((train) => (
                    <Marker
                      key={train.id}
                      position={train.position}
                      icon={trainIcon}
                    >
                      <Popup>
                        <Box sx={{ minWidth: 250 }}>
                          <Typography variant="subtitle1" fontWeight="bold">
                            {train.name}
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            Network: {train.network || 'N/A'}
                          </Typography>
                          <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                            Status: {train.status || 'Active'}
                          </Typography>
                        </Box>
                      </Popup>
                    </Marker>
                  ))}
                </MapContainer>
              )}
            </Box>
          </Paper>
        </Grid>

        {/* Train List */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ 
            p: 3, 
            height: 650, 
            overflow: 'hidden',
            bgcolor: 'white',
            borderRadius: 3,
            boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
            border: '1px solid rgba(0,0,0,0.05)',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <Box sx={{ mb: 2 }}>
              <Typography variant="h5" sx={{ color: '#0b0499', fontWeight: 800, mb: 0.5 }}>
                🚄 Active Trains
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                <Chip 
                  label={`${trains.length} trains`} 
                  size="small"
                  sx={{ bgcolor: '#2596be', color: 'white', fontWeight: 700 }}
                />
                {selectedNetwork !== 'all' && (
                  <Typography variant="caption" color="textSecondary" sx={{ fontWeight: 500 }}>
                    in selected network
                  </Typography>
                )}
              </Box>
            </Box>
            <Box sx={{ overflowY: 'auto', flex: 1, pr: 1 }}>
              {trains.slice(0, 50).map((train, idx) => (
                <Card key={train.id} sx={{ 
                  mb: 2,
                  borderLeft: `4px solid ${train.status === 'on-time' ? '#2596be' : '#ff9800'}`,
                  boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                  transition: 'all 0.2s ease',
                  borderRadius: 2,
                  bgcolor: idx % 2 === 0 ? '#fff' : '#fafafa',
                  '&:hover': { 
                    boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                    transform: 'translateX(4px)'
                  }
                }}>
                  <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" fontWeight={700} sx={{ color: '#0b0499', mb: 0.5 }}>
                          {train.name}
                        </Typography>
                        {train.route && (
                          <Typography variant="caption" color="textSecondary" sx={{ display: 'block', mb: 0.5 }}>
                            {train.route.length > 40 ? train.route.substring(0, 40) + '...' : train.route}
                          </Typography>
                        )}
                      </Box>
                      <Chip
                        label={train.status === 'on-time' ? '✓' : '!'}
                        size="small"
                        sx={{
                          bgcolor: train.status === 'on-time' ? '#2596be' : '#ff9800',
                          color: 'white',
                          fontWeight: 900,
                          minWidth: 28,
                          height: 28
                        }}
                      />
                    </Box>
                    <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <SpeedIcon fontSize="small" sx={{ color: '#2596be', fontSize: 16 }} />
                        <Typography variant="caption" fontWeight={600} sx={{ color: '#0b0499' }}>
                          {train.speed} km/h
                        </Typography>
                      </Box>
                      {train.country && (
                        <Typography variant="caption" sx={{ color: '#666' }}>
                          📍 {train.country}
                        </Typography>
                      )}
                      {train.delay > 0 && (
                        <Chip
                          icon={<WarningIcon sx={{ fontSize: 14 }} />}
                          label={`+${train.delay}m`}
                          size="small"
                          sx={{ 
                            height: 20,
                            bgcolor: '#fff3e0', 
                            color: '#ff9800',
                            fontWeight: 700,
                            fontSize: '0.7rem'
                          }}
                        />
                      )}
                    </Box>
                  </CardContent>
                </Card>
              ))}
              {trains.length === 0 && !loading && (
                <Box sx={{ 
                  textAlign: 'center', 
                  py: 8,
                  color: '#999'
                }}>
                  <TrainIcon sx={{ fontSize: 60, mb: 2, opacity: 0.3 }} />
                  <Typography variant="body2" fontWeight={500}>
                    No active trains
                  </Typography>
                </Box>
              )}
            </Box>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
}

export default Dashboard;
