import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  Typography,
  Alert,
  RadioGroup,
  FormControlLabel,
  Radio,
  Slider,
  Chip,
} from '@mui/material';
import {
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import axios from 'axios';

function FeedbackModal({ open, onClose, conflictId, strategyApplied }) {
  const [formData, setFormData] = useState({
    conflict_id: conflictId || '',
    strategy_applied: strategyApplied || '',
    outcome: 'success',
    actual_delay_after: 0,
    operator_notes: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    try {
      setSubmitting(true);
      setError('');
      
      await axios.post('http://localhost:8000/api/v1/recommendations/feedback', formData);
      
      setSuccess(true);
      setTimeout(() => {
        onClose();
        setSuccess(false);
        // Reset form
        setFormData({
          conflict_id: '',
          strategy_applied: '',
          outcome: 'success',
          actual_delay_after: 0,
          operator_notes: '',
        });
      }, 2000);
    } catch (err) {
      console.error('Error submitting feedback:', err);
      setError(err.response?.data?.detail || 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData({ ...formData, [field]: value });
  };

  React.useEffect(() => {
    if (conflictId) setFormData(prev => ({ ...prev, conflict_id: conflictId }));
    if (strategyApplied) setFormData(prev => ({ ...prev, strategy_applied: strategyApplied }));
  }, [conflictId, strategyApplied]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ bgcolor: '#0b0499', color: 'white', fontWeight: 'bold' }}>
        📋 Submit Resolution Feedback
      </DialogTitle>
      <DialogContent sx={{ mt: 3 }}>
        {success ? (
          <Alert severity="success" icon={<CheckCircleIcon />} sx={{ mb: 2 }}>
            <strong>Feedback submitted successfully!</strong> The system will learn from this outcome.
          </Alert>
        ) : (
          <>
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <TextField
              fullWidth
              label="Conflict ID"
              value={formData.conflict_id}
              onChange={(e) => handleChange('conflict_id', e.target.value)}
              sx={{ mb: 2 }}
              required
              helperText="The ID of the conflict that was resolved"
            />

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Strategy Applied</InputLabel>
              <Select
                value={formData.strategy_applied}
                onChange={(e) => handleChange('strategy_applied', e.target.value)}
                label="Strategy Applied"
                required
              >
                <MenuItem value="platform_change">Platform Change</MenuItem>
                <MenuItem value="route_modification">Route Modification</MenuItem>
                <MenuItem value="schedule_adjustment">Schedule Adjustment</MenuItem>
                <MenuItem value="speed_regulation">Speed Regulation</MenuItem>
                <MenuItem value="hold_and_proceed">Hold and Proceed</MenuItem>
                <MenuItem value="emergency_stop">Emergency Stop</MenuItem>
                <MenuItem value="service_cancellation">Service Cancellation</MenuItem>
                <MenuItem value="train_coupling">Train Coupling</MenuItem>
                <MenuItem value="crew_reassignment">Crew Reassignment</MenuItem>
                <MenuItem value="platform_extension">Platform Extension</MenuItem>
              </Select>
            </FormControl>

            <Typography gutterBottom sx={{ fontWeight: 'bold', color: '#0b0499' }}>
              Outcome
            </Typography>
            <RadioGroup
              value={formData.outcome}
              onChange={(e) => handleChange('outcome', e.target.value)}
              sx={{ mb: 2 }}
            >
              <FormControlLabel 
                value="success" 
                control={<Radio />} 
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ThumbUpIcon sx={{ color: '#10b981' }} />
                    <span>Success - Resolution worked as expected</span>
                  </Box>
                }
              />
              <FormControlLabel 
                value="partial_success" 
                control={<Radio />} 
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <span>⚡</span>
                    <span>Partial Success - Resolution helped but wasn't perfect</span>
                  </Box>
                }
              />
              <FormControlLabel 
                value="failed" 
                control={<Radio />} 
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <ThumbDownIcon sx={{ color: '#ef4444' }} />
                    <span>Failed - Resolution did not improve the situation</span>
                  </Box>
                }
              />
            </RadioGroup>

            <Typography gutterBottom sx={{ fontWeight: 'bold', color: '#0b0499', mb: 1 }}>
              Actual Delay After Resolution: {formData.actual_delay_after} minutes
            </Typography>
            <Slider
              value={formData.actual_delay_after}
              onChange={(e, value) => handleChange('actual_delay_after', value)}
              min={0}
              max={60}
              step={1}
              marks={[
                { value: 0, label: '0m' },
                { value: 15, label: '15m' },
                { value: 30, label: '30m' },
                { value: 45, label: '45m' },
                { value: 60, label: '60m' },
              ]}
              valueLabelDisplay="auto"
              sx={{ mb: 3 }}
            />

            <TextField
              fullWidth
              label="Operator Notes (Optional)"
              value={formData.operator_notes}
              onChange={(e) => handleChange('operator_notes', e.target.value)}
              multiline
              rows={3}
              placeholder="Any additional observations or context about the resolution..."
              helperText="Your notes help the AI learn and improve future recommendations"
            />
          </>
        )}
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose} disabled={submitting}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={submitting || success || !formData.conflict_id || !formData.strategy_applied}
          sx={{
            bgcolor: '#0b0499',
            '&:hover': { bgcolor: '#1a0db3' },
          }}
        >
          {submitting ? 'Submitting...' : success ? 'Submitted!' : 'Submit Feedback'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default FeedbackModal;
