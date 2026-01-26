import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  CssBaseline,
  Button,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Psychology as PsychologyIcon,
  Settings as SettingsIcon,
  DeviceHub as DeviceHubIcon,
  Notifications as NotificationsIcon,
} from '@mui/icons-material';
import Dashboard from './components/Dashboard';
import AIModels from './components/AIModels';
import DigitalTwin from './components/DigitalTwin';
import Settings from './components/Settings';
import Alerts from './components/Alerts';
import './App.css';

function App() {
  const [stats, setStats] = useState({
    vectors: 0,
    collections: 0,
    aiModels: 0,
    uptime: '0h 0m',
  });

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/stats');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/' },
    { text: 'AI Models', icon: <PsychologyIcon />, path: '/ai' },
    { text: 'Digital Twin', icon: <DeviceHubIcon />, path: '/digital-twin' },
    { text: 'Alerts', icon: <NotificationsIcon />, path: '/alerts' },
    { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
  ];

  return (
    <Router>
      <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <CssBaseline />
        <AppBar 
          position="fixed" 
          elevation={0}
          sx={{ 
            background: 'linear-gradient(135deg, #1e40af 0%, #0891b2 100%)',
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <Toolbar sx={{ justifyContent: 'center', position: 'relative' }}>
            <Typography 
              variant="h6" 
              component="div"
              sx={{ 
                position: 'absolute',
                left: 24,
                fontWeight: 700,
                letterSpacing: 0.5,
                display: 'flex',
                alignItems: 'center',
                gap: 1,
              }}
            >
              <img 
                src="/golden-retriever-logo.png" 
                alt="Golden Retriever" 
                style={{ 
                  height: '45px', 
                  width: 'auto',
                  filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))'
                }} 
              />
              Golden Retriever
            </Typography>
            <NavigationTabs menuItems={menuItems} />
          </Toolbar>
        </AppBar>
        <Box 
          component="main" 
          sx={{ 
            flexGrow: 1, 
            pt: 10, 
            px: 4, 
            pb: 4,
            background: 'linear-gradient(to bottom, #f0f9ff 0%, #e0f2fe 100%)',
            minHeight: '100vh',
          }}
        >
          <Container maxWidth="xl">
            <Routes>
              <Route path="/" element={<Dashboard stats={stats} />} />
              <Route path="/ai" element={<AIModels />} />
              <Route path="/digital-twin" element={<DigitalTwin />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Container>
        </Box>
      </Box>
    </Router>
  );
}

function NavigationTabs({ menuItems }) {
  const location = useLocation();
  const currentPath = location.pathname;

  return (
    <Box sx={{ display: 'flex', gap: 1 }}>
      {menuItems.map((item) => (
        <Button
          key={item.text}
          component={Link}
          to={item.path}
          startIcon={item.icon}
          sx={{
            color: 'white',
            textTransform: 'none',
            px: 2,
            py: 1,
            borderRadius: 2,
            fontWeight: currentPath === item.path ? 700 : 400,
            backgroundColor: currentPath === item.path ? 'rgba(255,255,255,0.2)' : 'transparent',
            '&:hover': {
              backgroundColor: 'rgba(255,255,255,0.15)',
            },
          }}
        >
          {item.text}
        </Button>
      ))}
    </Box>
  );
}

export default App;
