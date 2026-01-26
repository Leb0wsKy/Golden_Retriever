import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Box,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  CssBaseline,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Storage as StorageIcon,
  Psychology as PsychologyIcon,
  Settings as SettingsIcon,
  DeviceHub as DeviceHubIcon,
} from '@mui/icons-material';
import Dashboard from './components/Dashboard';
import VectorDatabase from './components/VectorDatabase';
import AIModels from './components/AIModels';
import DigitalTwin from './components/DigitalTwin';
import Settings from './components/Settings';
import './App.css';

const drawerWidth = 240;

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
    { text: 'Vector Database', icon: <StorageIcon />, path: '/vectors' },
    { text: 'AI Models', icon: <PsychologyIcon />, path: '/ai' },
    { text: 'Digital Twin', icon: <DeviceHubIcon />, path: '/digital-twin' },
    { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
  ];

  return (
    <Router>
      <Box sx={{ display: 'flex' }}>
        <CssBaseline />
        <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
          <Toolbar>
            <Typography variant="h6" noWrap component="div">
              Train Network Monitoring Platform
            </Typography>
          </Toolbar>
        </AppBar>
        <Drawer
          variant="permanent"
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
          }}
        >
          <Toolbar />
          <Box sx={{ overflow: 'auto' }}>
            <List>
              {menuItems.map((item) => (
                <ListItem button key={item.text} component={Link} to={item.path}>
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItem>
              ))}
            </List>
          </Box>
        </Drawer>
        <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
          <Toolbar />
          <Container maxWidth="xl">
            <Routes>
              <Route path="/" element={<Dashboard stats={stats} />} />
              <Route path="/vectors" element={<VectorDatabase />} />
              <Route path="/ai" element={<AIModels />} />
              <Route path="/digital-twin" element={<DigitalTwin />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </Container>
        </Box>
      </Box>
    </Router>
  );
}

export default App;
