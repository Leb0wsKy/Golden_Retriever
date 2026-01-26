import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Button,
  TextField,
  CircularProgress,
} from '@mui/material';
import { 
  PlayArrow as PlayIcon,
  Psychology as PsychologyIcon,
} from '@mui/icons-material';
import axios from 'axios';

function AIModels() {
  const [models, setModels] = useState([]);
  const [inputText, setInputText] = useState('');
  const [embedding, setEmbedding] = useState(null);
  const [loading, setLoading] = useState(false);
  const [prediction, setPrediction] = useState(null);

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const response = await axios.get('/api/ai/models');
      setModels(response.data);
    } catch (error) {
      console.error('Error fetching models:', error);
    }
  };

  const generateEmbedding = async () => {
    setLoading(true);
    try {
      const response = await axios.post('/api/ai/embed', {
        text: inputText,
      });
      setEmbedding(response.data);
    } catch (error) {
      console.error('Error generating embedding:', error);
    } finally {
      setLoading(false);
    }
  };

  const runPrediction = async (modelId) => {
    setLoading(true);
    try {
      const response = await axios.post('/api/ai/predict', {
        model_id: modelId,
        input: inputText,
      });
      setPrediction(response.data);
    } catch (error) {
      console.error('Error running prediction:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ 
      bgcolor: '#f8f9fa', 
      minHeight: '100vh', 
      p: { xs: 2, md: 4 },
      background: 'linear-gradient(180deg, #e3f2fd 0%, #f8f9fa 100%)'
    }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <PsychologyIcon sx={{ mr: 1.5, fontSize: 40, color: '#0891b2' }} />
        <Typography variant="h4" sx={{ fontWeight: 800, color: '#1e40af' }}>
          AI Models
        </Typography>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ 
            p: 3,
            bgcolor: 'white',
            borderRadius: 3,
            boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
            border: '1px solid rgba(0,0,0,0.05)',
            height: '100%'
          }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 700, color: '#1e40af', mb: 2 }}>
              Text Embedding Generator
            </Typography>
            <TextField
              fullWidth
              multiline
              rows={4}
              label="Enter text to embed"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              sx={{ mb: 2 }}
            />
            <Button
              variant="contained"
              startIcon={loading ? <CircularProgress size={20} /> : <PlayIcon />}
              onClick={generateEmbedding}
              disabled={loading || !inputText}
              fullWidth
              sx={{
                background: 'linear-gradient(135deg, #1e40af 0%, #0891b2 100%)',
                color: 'white',
                fontWeight: 600,
                py: 1.5,
                '&:hover': {
                  background: 'linear-gradient(135deg, #1e3a8a 0%, #0e7490 100%)',
                },
                '&:disabled': {
                  background: '#e0e0e0',
                }
              }}
            >
              Generate Embedding
            </Button>
            {embedding && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2">Embedding Vector:</Typography>
                <Paper sx={{ p: 2, mt: 1, bgcolor: '#f5f5f5' }}>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                    Dimension: {embedding.dimension}
                    <br />
                    Vector: [{embedding.vector.slice(0, 5).join(', ')}...]
                  </Typography>
                </Paper>
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ 
            p: 3,
            bgcolor: 'white',
            borderRadius: 3,
            boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
            border: '1px solid rgba(0,0,0,0.05)',
            height: '100%'
          }}>
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 700, color: '#1e40af', mb: 2 }}>
              Model Predictions
            </Typography>
            {prediction && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#1e40af', mb: 1 }}>Latest Prediction:</Typography>
                <Paper sx={{ 
                  p: 2, 
                  mt: 1, 
                  background: 'linear-gradient(135deg, #e0f2fe 0%, #dbeafe 100%)',
                  border: '1px solid rgba(8, 145, 178, 0.2)',
                  borderRadius: 2
                }}>
                  <Typography variant="body2">
                    Confidence: {(prediction.confidence * 100).toFixed(2)}%
                    <br />
                    Result: {prediction.result}
                  </Typography>
                </Paper>
              </Box>
            )}
          </Paper>
        </Grid>

        {models.map((model) => (
          <Grid item xs={12} sm={6} md={4} key={model.id}>
            <Card sx={{
              borderRadius: 3,
              boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
              border: '1px solid rgba(0,0,0,0.05)',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                transform: 'translateY(-4px)',
                boxShadow: '0 12px 48px rgba(0,0,0,0.12)',
              },
            }}>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 700, color: '#1e40af' }}>
                  {model.name}
                </Typography>
                <Typography variant="body2" color="textSecondary" paragraph>
                  {model.description}
                </Typography>
                <Typography variant="caption" display="block" gutterBottom sx={{ fontWeight: 600 }}>
                  Status: {model.status}
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => runPrediction(model.id)}
                  disabled={loading || !inputText}
                  fullWidth
                  sx={{
                    borderColor: '#0891b2',
                    color: '#0891b2',
                    fontWeight: 600,
                    '&:hover': {
                      borderColor: '#1e40af',
                      bgcolor: 'rgba(30, 64, 175, 0.04)',
                    }
                  }}
                >
                  Run Prediction
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

export default AIModels;
