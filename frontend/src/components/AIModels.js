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
import { PlayArrow as PlayIcon } from '@mui/icons-material';
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
    <Box>
      <Typography variant="h4" gutterBottom>
        AI Models
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
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
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Model Predictions
            </Typography>
            {prediction && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2">Latest Prediction:</Typography>
                <Paper sx={{ p: 2, mt: 1, bgcolor: '#e3f2fd' }}>
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
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {model.name}
                </Typography>
                <Typography variant="body2" color="textSecondary" paragraph>
                  {model.description}
                </Typography>
                <Typography variant="caption" display="block" gutterBottom>
                  Status: {model.status}
                </Typography>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => runPrediction(model.id)}
                  disabled={loading || !inputText}
                  fullWidth
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
