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
  IconButton,
  Avatar,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  AccountCircle as AccountCircleIcon,
  Person as PersonIcon,
  Logout as LogoutIcon,
  Analytics as AnalyticsIcon,
  History as HistoryIcon,
} from '@mui/icons-material';
import Dashboard from './components/Dashboard';
import Alerts from './components/Alerts';
import ConflictHistory from './components/ConflictHistory';
import Analytics from './components/Analytics';
import './App.css';

function App() {
  const [stats, setStats] = useState({
    vectors: 0,
    collections: 0,
    aiModels: 0,
    uptime: '0h 0m',
  });
  const [anchorEl, setAnchorEl] = useState(null);

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleProfileClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleProfileClose = () => {
    setAnchorEl(null);
  };

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
    { text: 'Live Alerts', icon: <NotificationsIcon />, path: '/alerts' },
    { text: 'Conflict History', icon: <HistoryIcon />, path: '/history' },
    { text: 'Analytics', icon: <AnalyticsIcon />, path: '/analytics' },
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
            <Box sx={{ position: 'absolute', right: 24 }}>
              <IconButton
                onClick={handleProfileClick}
                sx={{
                  color: 'white',
                  '&:hover': {
                    bgcolor: 'rgba(255, 255, 255, 0.1)',
                  },
                }}
              >
                <Avatar 
                  sx={{ 
                    width: 40, 
                    height: 40,
                    bgcolor: 'rgba(255, 255, 255, 0.2)',
                    border: '2px solid white',
                  }}
                >
                  <AccountCircleIcon sx={{ fontSize: 28 }} />
                </Avatar>
              </IconButton>
              <Menu
                anchorEl={anchorEl}
                open={Boolean(anchorEl)}
                onClose={handleProfileClose}
                anchorOrigin={{
                  vertical: 'bottom',
                  horizontal: 'right',
                }}
                transformOrigin={{
                  vertical: 'top',
                  horizontal: 'right',
                }}
                PaperProps={{
                  sx: {
                    mt: 1,
                    minWidth: 200,
                    borderRadius: 2,
                    boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
                  },
                }}
              >
                <MenuItem onClick={handleProfileClose}>
                  <PersonIcon sx={{ mr: 1.5, fontSize: 20, color: '#0891b2' }} />
                  Profile
                </MenuItem>
                <MenuItem onClick={handleProfileClose}>
                  <SettingsIcon sx={{ mr: 1.5, fontSize: 20, color: '#0891b2' }} />
                  Settings
                </MenuItem>
                <MenuItem onClick={handleProfileClose}>
                  <LogoutIcon sx={{ mr: 1.5, fontSize: 20, color: '#0891b2' }} />
                  Logout
                </MenuItem>
              </Menu>
            </Box>
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
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/history" element={<ConflictHistory />} />
              <Route path="/analytics" element={<Analytics />} />
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
