import React, { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Avatar,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  Divider,
  Alert,
} from '@mui/material';
import {
  Person as PersonIcon,
  Edit as EditIcon,
  Email as EmailIcon,
  AccountCircle as AccountCircleIcon,
} from '@mui/icons-material';
import axios from 'axios';

function Profile() {
  const [user, setUser] = useState(JSON.parse(localStorage.getItem('user') || '{}'));
  const [openEdit, setOpenEdit] = useState(false);
  const [formData, setFormData] = useState({
    name: user.name || '',
    email: user.email || '',
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });
  const [saveStatus, setSaveStatus] = useState(null);

  const handleOpenEdit = () => {
    setFormData({
      name: user.name || '',
      email: user.email || '',
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    });
    setOpenEdit(true);
    setSaveStatus(null);
  };

  const handleCloseEdit = () => {
    setOpenEdit(false);
    setSaveStatus(null);
  };

  const handleChange = (field, value) => {
    setFormData({ ...formData, [field]: value });
  };

  const handleSave = async () => {
    try {
      // Validate passwords if changing
      if (formData.newPassword) {
        if (formData.newPassword !== formData.confirmPassword) {
          setSaveStatus({ type: 'error', message: 'New passwords do not match' });
          return;
        }
        if (formData.newPassword.length < 8) {
          setSaveStatus({ type: 'error', message: 'Password must be at least 8 characters' });
          return;
        }
      }

      const updateData = {
        name: formData.name,
        email: formData.email,
      };

      if (formData.newPassword) {
        updateData.currentPassword = formData.currentPassword;
        updateData.newPassword = formData.newPassword;
      }

      // In a real app, this would call the API
      // await axios.put('/api/profile', updateData, {
      //   headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      // });

      // Update local storage
      const updatedUser = { ...user, name: formData.name, email: formData.email };
      localStorage.setItem('user', JSON.stringify(updatedUser));
      setUser(updatedUser);

      setSaveStatus({ type: 'success', message: 'Profile updated successfully!' });
      setTimeout(() => {
        handleCloseEdit();
      }, 1500);
    } catch (error) {
      setSaveStatus({ type: 'error', message: 'Failed to update profile' });
      console.error('Error updating profile:', error);
    }
  };

  return (
    <Box sx={{ 
      minHeight: '100vh', 
      p: { xs: 2, md: 4 },
    }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <PersonIcon sx={{ mr: 1.5, fontSize: 40, color: '#0891b2' }} />
        <Typography variant="h4" sx={{ fontWeight: 700, background: 'linear-gradient(135deg, #1e40af 0%, #0891b2 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          Profile
        </Typography>
      </Box>

      <Paper sx={{ 
        p: 4,
        borderRadius: 3,
        boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        border: '1px solid #e5e7eb',
      }}>
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', md: 'row' }, alignItems: 'center', gap: 4 }}>
          <Avatar 
            sx={{ 
              width: 120, 
              height: 120,
              background: 'linear-gradient(135deg, #1e40af 0%, #0891b2 100%)',
              fontSize: 48,
              fontWeight: 700,
            }}
          >
            {(user.name || user.email || 'U')[0].toUpperCase()}
          </Avatar>

          <Box sx={{ flex: 1 }}>
            <Typography variant="h5" sx={{ fontWeight: 700, color: '#1e40af', mb: 1 }}>
              {user.name || 'User'}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <EmailIcon sx={{ fontSize: 20, color: '#64748b', mr: 1 }} />
              <Typography variant="body1" sx={{ color: '#64748b' }}>
                {user.email}
              </Typography>
            </Box>
            <Button
              variant="contained"
              startIcon={<EditIcon />}
              onClick={handleOpenEdit}
              sx={{
                background: 'linear-gradient(135deg, #1e40af 0%, #0891b2 100%)',
                textTransform: 'none',
                fontWeight: 600,
                px: 3,
                py: 1,
                borderRadius: 2,
                boxShadow: 'none',
                '&:hover': {
                  background: 'linear-gradient(135deg, #1e3a8a 0%, #0e7490 100%)',
                  boxShadow: '0 4px 12px rgba(30, 64, 175, 0.3)',
                },
              }}
            >
              Edit Profile
            </Button>
          </Box>
        </Box>

        <Divider sx={{ my: 4 }} />

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, bgcolor: '#f0f9ff', borderRadius: 2, border: '1px solid #e0f2fe' }}>
              <Typography variant="body2" sx={{ color: '#64748b', fontWeight: 600, mb: 1 }}>
                ACCOUNT STATUS
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#0891b2' }}>
                Active
              </Typography>
            </Paper>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, bgcolor: '#f0f9ff', borderRadius: 2, border: '1px solid #e0f2fe' }}>
              <Typography variant="body2" sx={{ color: '#64748b', fontWeight: 600, mb: 1 }}>
                MEMBER SINCE
              </Typography>
              <Typography variant="h6" sx={{ fontWeight: 700, color: '#0891b2' }}>
                {new Date().toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
              </Typography>
            </Paper>
          </Grid>
        </Grid>
      </Paper>

      {/* Edit Profile Dialog */}
      <Dialog 
        open={openEdit} 
        onClose={handleCloseEdit}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            borderRadius: 3,
            boxShadow: '0 8px 32px rgba(0,0,0,0.12)',
          }
        }}
      >
        <DialogTitle sx={{ 
          fontWeight: 700, 
          fontSize: '1.5rem',
          background: 'linear-gradient(135deg, #1e40af 0%, #0891b2 100%)',
          color: 'white',
          display: 'flex',
          alignItems: 'center',
          gap: 1,
        }}>
          <EditIcon />
          Edit Profile
        </DialogTitle>
        <DialogContent sx={{ pt: 3 }}>
          {saveStatus && (
            <Alert severity={saveStatus.type} sx={{ mb: 3, borderRadius: 2 }}>
              {saveStatus.message}
            </Alert>
          )}

          <TextField
            fullWidth
            label="Full Name"
            value={formData.name}
            onChange={(e) => handleChange('name', e.target.value)}
            sx={{ 
              mb: 2.5,
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              }
            }}
          />

          <TextField
            fullWidth
            label="Email"
            type="email"
            value={formData.email}
            onChange={(e) => handleChange('email', e.target.value)}
            sx={{ 
              mb: 3,
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              }
            }}
          />

          <Divider sx={{ my: 3 }}>
            <Typography variant="caption" sx={{ color: '#64748b', fontWeight: 600 }}>
              CHANGE PASSWORD (OPTIONAL)
            </Typography>
          </Divider>

          <TextField
            fullWidth
            label="Current Password"
            type="password"
            value={formData.currentPassword}
            onChange={(e) => handleChange('currentPassword', e.target.value)}
            sx={{ 
              mb: 2.5,
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              }
            }}
          />

          <TextField
            fullWidth
            label="New Password"
            type="password"
            value={formData.newPassword}
            onChange={(e) => handleChange('newPassword', e.target.value)}
            helperText="At least 8 characters"
            sx={{ 
              mb: 2.5,
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              }
            }}
          />

          <TextField
            fullWidth
            label="Confirm New Password"
            type="password"
            value={formData.confirmPassword}
            onChange={(e) => handleChange('confirmPassword', e.target.value)}
            sx={{ 
              '& .MuiOutlinedInput-root': {
                borderRadius: 2,
              }
            }}
          />
        </DialogContent>
        <DialogActions sx={{ p: 3, pt: 2 }}>
          <Button 
            onClick={handleCloseEdit}
            sx={{ 
              textTransform: 'none',
              color: '#64748b',
              fontWeight: 600,
            }}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleSave}
            variant="contained"
            sx={{
              background: 'linear-gradient(135deg, #1e40af 0%, #0891b2 100%)',
              textTransform: 'none',
              fontWeight: 600,
              px: 3,
              boxShadow: 'none',
              '&:hover': {
                background: 'linear-gradient(135deg, #1e3a8a 0%, #0e7490 100%)',
                boxShadow: '0 4px 12px rgba(30, 64, 175, 0.3)',
              },
            }}
          >
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default Profile;
